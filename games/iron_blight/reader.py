"""Iron Blight (Steam build 25439780, Unity 6000.3 IL2CPP, offline single-player) -> GameState. Read-only: no hooks.

Everything is read by class and field name from the game's own metadata (dualsense/il2cpp.py), so an update that
keeps the names keeps working:
    Player.instance           health, baseHealth, IsDead, isKicking (+ canKickLand, currentKicks for --watch)
    MainMenu.instance         isPaused
    GunHandler.instance       currentGun, isReloading, isCheckingAmmo, isMeleeAttacking (+ canMeleeAttackLand)
    currentGun (Gun)          ammoCount, gunType, isJammed, isMelee
A shot = the selected gun's ammoCount dropping while it is not being reloaded or checked (one round per shot,
shotguns too; verified with the pistol). A kick / melee swing = isKicking / isMeleeAttacking turning True
(not yet seen in the running game)."""
import time
from pathlib import Path

from dualsense.effects import GameState
from dualsense.hook import GameNotReady
from dualsense.il2cpp import Il2Cpp, Metadata
from dualsense.memory import Process

WEAPONS = ["pistol", "shotgun", "smg", "rifle", "revolver", "melee", "assaultRifle"]   # enum Type, Gun.gunType
REQUIRED = ["Player", "MainMenu"]
OPTIONAL = ["GunHandler", "Gun"]          # may not exist before the player's first gun


class IronBlightReader:
    RETRY_SECONDS = 2.0       # game starting / closing: wait this long before attaching again
    RESCAN_SECONDS = 10.0     # a class not set up yet: look again this often (a full memory scan)

    def __init__(self, process_names, clock):
        self.process_names = process_names
        self.clock = clock
        self.proc = self.il = None
        self.cls = {}
        self.rescan_at = 0.0
        self.gun = self.ammo = None
        self.prev = {}            # previous snapshot, for False -> True edges
        self.retry_at = 0.0
        self.last_error = None

    def read(self):
        """GameState; never raises for a game that is starting, closing or not running (retries later)."""
        now = self.clock()
        if now < self.retry_at:
            return GameState()
        try:
            return self._read(now)
        except (GameNotReady, OSError) as e:
            self.close()
            self.retry_at = now + self.RETRY_SECONDS
            if str(e) != self.last_error:
                print(f"[{time.strftime('%H:%M:%S')}] game not ready ({e}); retrying")
                self.last_error = str(e)
            return GameState()

    def _attach(self, now):
        if self.proc and not self.proc.alive():
            self.close()
        if self.proc is None:
            self.proc = Process.find(self.process_names)
            if self.proc is None:
                return False
            exe = Path(self.proc.path)
            meta = exe.with_name(f"{exe.stem}_Data") / "il2cpp_data" / "Metadata" / "global-metadata.dat"
            self.il, self.cls, self.rescan_at = Il2Cpp(self.proc, Metadata(meta.read_bytes())), {}, 0.0
            self.last_error = None
        missing = [c for c in REQUIRED + OPTIONAL if c not in self.cls]
        if missing and now >= self.rescan_at:
            self.cls |= self.il.classes(missing)
            self.rescan_at = now + self.RESCAN_SECONDS
        if any(c not in self.cls for c in REQUIRED):
            raise GameNotReady(f"classes not set up yet: {', '.join(c for c in REQUIRED if c not in self.cls)}")
        return True

    def snapshot(self, now):
        """Raw game values (dict), None while the game is not running / no player is loaded."""
        if not self._attach(now):
            return None
        il, c = self.il, self.cls
        player = il.static(c["Player"], "instance")
        if not il.is_a(player, c["Player"]):
            return None                                       # main menu, loading
        menu = il.static(c["MainMenu"], "<instance>k__BackingField")
        s = {"health": il.get(player, c["Player"], "health"),
             "base_health": il.get(player, c["Player"], "baseHealth"),
             "dead": il.get(player, c["Player"], "<IsDead>k__BackingField"),
             "paused": il.get(menu, c["MainMenu"], "isPaused") if il.is_a(menu, c["MainMenu"]) else False,
             "kicking": il.get(player, c["Player"], "isKicking"),
             "kick_land": il.get(player, c["Player"], "canKickLand"),
             "kicks_left": il.get(player, c["Player"], "currentKicks"),
             "gun": None}
        gh_cls, gun_cls = c.get("GunHandler"), c.get("Gun")
        gh = il.static(gh_cls, "instance") if gh_cls else None
        if gun_cls and il.is_a(gh, gh_cls):
            gun = il.get(gh, gh_cls, "currentGun")
            s |= {"selected": il.get(gh, gh_cls, "isSelected"),
                  "reloading": il.get(gh, gh_cls, "isReloading"), "checking": il.get(gh, gh_cls, "isCheckingAmmo"),
                  "shot_count": il.get(gh, gh_cls, "shotCount"),
                  "melee_attacking": il.get(gh, gh_cls, "isMeleeAttacking"),
                  "melee_land": il.get(gh, gh_cls, "canMeleeAttackLand")}
            if il.is_a(gun, gun_cls):
                t = il.get(gun, gun_cls, "gunType")
                s |= {"gun": gun, "ammo": il.get(gun, gun_cls, "ammoCount"),
                      "weapon": WEAPONS[t] if t is not None and 0 <= t < len(WEAPONS) else None,
                      "jammed": il.get(gun, gun_cls, "isJammed"), "melee": il.get(gun, gun_cls, "isMelee")}
        return s

    def _read(self, now):
        return self.replay(self.snapshot(now))

    def replay(self, s):
        """GameState from one snapshot (dict from snapshot(), or None); keeps what it needs from the previous
        one. Also used to simulate every state (states.py) without the game."""
        if s is None:
            self.gun = self.ammo = None
            self.prev = {}
            return GameState(attached=self.proc is not None)
        playing = not s["paused"] and not s["dead"]
        hull = None
        if s["health"] is not None and s["base_health"]:
            hull = max(0.0, min(1.0, s["health"] / s["base_health"]))
        shots, gun = 0, s["gun"]
        if gun:
            # a magazine out is not a shot; melee weapons also have an ammoCount (durability?), never a shot
            busy = s["reloading"] or s["checking"] or s["melee"]
            if gun == self.gun and self.ammo is not None and s["ammo"] is not None and not busy:
                shots = max(0, self.ammo - s["ammo"])
            self.gun, self.ammo = gun, s["ammo"]
        else:
            self.gun = self.ammo = None
        # slack = plain trigger: no gun in hand (holstered: GunHandler.instance is null; while holstering:
        # isSelected False), or a gun that can't fire (empty, jammed); melee has its own profile
        slack = not gun or s.get("selected") is False or (not s["melee"] and (s["ammo"] == 0 or bool(s["jammed"])))
        # body events on the moment an action starts (False -> True); the hit itself may come later (to measure)
        bumps = tuple(name for name, key in (("kick", "kicking"), ("melee", "melee_attacking"))
                      if s.get(key) and not self.prev.get(key))
        self.prev = s
        return GameState(attached=True, in_flight=playing, hull=hull, shots=shots if playing else 0,
                         weapon=s.get("weapon") if gun else None, slack=slack, bumps=bumps if playing else ())

    def close(self):
        """Nothing in the game to restore: this reader never writes."""
        if self.proc:
            self.proc.close()
        self.proc, self.il, self.cls = None, None, {}
