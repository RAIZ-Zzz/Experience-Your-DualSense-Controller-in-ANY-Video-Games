# Rules for games with an anti-cheat

Games on this branch have online modes protected by an anti-cheat (EasyAntiCheat, BattlEye, ...).
They are supported **only in their offline modes, with the anti-cheat switched off**. A controller mod
must never be mistaken for a cheat, and it must never be one.

## Always

1. **Offline modes only.** Story, practice, offline vs AI. With the anti-cheat off the online modes stop
   working anyway; never try to make them work.
2. **The anti-cheat is off only while you play offline.** Restore it (the game's README says how, e.g.
   the store's "Repair") before any online session. A game update usually restores it by itself.
3. **The bridge refuses while an anti-cheat runs.** `dualsense/memory.py` will not attach if one of the
   known anti-cheat processes is running. Never remove or weaken that guard; add new anti-cheats to it.
4. **Every game README documents** how the anti-cheat is switched off for offline play and how it is
   restored (sections *Anti-cheat off (offline only)* and *Restore the anti-cheat*). `tests/test_rules.py`
   fails without them.

## Never

- Hook, read or patch a game while it is in an online mode or while its anti-cheat runs.
- Hide from, spoof, block or patch the anti-cheat itself, or run online without it.
- Ship anything that changes gameplay (infinite energy, god mode, ...): effects only *read* the game.
  The hooks copy a pointer and run the original instruction unchanged.
- Use the hooks in multiplayer, even in private or "co-op vs AI" lobbies that go through the game's
  servers.

## Before adding a game

- Does it have offline modes that run without the anti-cheat? If everything worth playing is online,
  the game is not supported.
- Is switching the anti-cheat off for offline play a documented, reversible method (e.g. on
  PCGamingWiki)? If it needs patching the anti-cheat or the game's network code, stop.
