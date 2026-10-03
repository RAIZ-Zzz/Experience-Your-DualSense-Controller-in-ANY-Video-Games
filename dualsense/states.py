"""Every game state the controller can meet, and what it does in each: enumerate, simulate, store as JSON.

A game lists its state dimensions (hand, weapon, ammo, event, ...), the combinations that cannot happen, and
how a state turns into the snapshots its reader sees. Every remaining combination is run through the game's
reader and the shared Effects; the outputs are stored in games/<name>/states.json, so any change in behaviour
shows up as a diff, and checked against the game's design rules (invariants). Bugs found in play so far
(no gun but resistance, holstering, melee durability counted as shots) were all states nobody listed."""
import itertools
import json

from .effects import Effects

DT = 0.005                      # one 200 Hz bridge frame


def expand(dims, impossible):
    """All combinations of dims ({name: [values]}) for which no rule in `impossible` (state -> bool) holds."""
    names = list(dims)
    out = []
    for values in itertools.product(*(dims[n] for n in names)):
        state = dict(zip(names, values))
        if not any(rule(state) for rule in impossible):
            out.append(state)
    return out


def simulate(reader, cfg, frames, now=10.0):
    """Feed the reader's snapshots (one per frame) through it and Effects; controller output at the last frame."""
    fx = Effects(cfg)
    for i, snap in enumerate(frames):
        state = reader.replay(snap)
        t = now + i * DT
        rt = fx.update(state, t)
        rumble = fx.rumble(state, t)
        rgb = fx.lightbar(state, t)
    return {"rt": f"{rt.mode.name} {','.join(map(str, rt.params))}".strip(),
            "rumble": [round(v, 3) for v in rumble],
            "lightbar": list(rgb) if rgb is not None else None,
            "shots": state.shots, "bumps": list(state.bumps)}


def label(state):
    return " ".join(f"{k}={v}" for k, v in state.items())


def table(states, run):
    """[{"state": ..., "out": ...}] for every state; run(state) -> output dict."""
    return [{"state": s, "out": run(s)} for s in states]


def violations(rows, invariants):
    """[(state label, rule text)] for every row breaking a design rule; invariants: [(text, (state, out) -> bool)]."""
    return [(label(r["state"]), text) for r in rows for text, ok in invariants if not ok(r["state"], r["out"])]


def summary(rows, examples=4):
    """Rows grouped by identical controller output, for a human to review."""
    groups = {}
    for r in rows:
        groups.setdefault(json.dumps(r["out"], sort_keys=True), []).append(r["state"])
    lines = [f"{len(rows)} states, {len(groups)} different controller outputs"]
    for out, states in sorted(groups.items(), key=lambda g: -len(g[1])):
        lines.append(f"\n{len(states):4} x {out}")
        lines += [f"       {label(s)}" for s in states[:examples]]
        if len(states) > examples:
            lines.append(f"       ... {len(states) - examples} more")
    return "\n".join(lines)


def save(path, rows):
    path.write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
