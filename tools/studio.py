"""Studio: one folder per branch (git worktrees) and a dashboard of every game's progress.

    studio/
      core/                     main            shared framework, tools, skill, template
      tracks/online/            online          games with anti-cheat (offline modes only) + rules
      tracks/single-player/     single-player   games without anti-cheat
      games/<name>/             game/<name>     one game, branched from its track

    python core/tools/studio.py                     status of every worktree -> prints it and writes STUDIO.md
    python core/tools/studio.py new <name> --track online|single-player
                                                    new game branch + worktree, template copied in
    python core/tools/studio.py sync                merge main -> tracks -> games; stops at the first conflict

Each game keeps its progress in games/<module>/TASKS.md: "Status:" and "Next:" lines plus a checklist.
"""
import argparse
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

TRACKS = ("online", "single-player")


def git(cwd, *args, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode:
        raise SystemExit(f"git {' '.join(args)} failed in {cwd}:\n{r.stderr.strip()}")
    return r.stdout.strip()


def worktrees():
    """[(path, branch)], core (the main worktree) first."""
    out, path = [], None
    for line in git(Path(__file__).parent, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = Path(line[9:])
        elif line.startswith("branch "):
            out.append((path, line[7:].removeprefix("refs/heads/")))
    return out


def studio_root():
    return worktrees()[0][0].parent


def track_of(core, branch):
    return git(core, "config", f"branch.{branch}.studio-track", check=False) or None


def tasks(wt):
    """(status, next, open, done) from the first games/*/TASKS.md that isn't the template."""
    for f in sorted(wt.glob("games/*/TASKS.md")):
        if f.parent.name.startswith("_"):
            continue
        t = f.read_text(encoding="utf-8")
        field = lambda k: (re.search(rf"^{k}:\s*(.+)$", t, re.M) or [None, "-"])[1].strip()
        return field("Status"), field("Next"), t.count("- [ ]"), t.count("- [x]")
    return None


def status(write=True):
    core = worktrees()[0][0]
    rows = []
    for wt, br in worktrees():
        dirty = len(git(wt, "status", "--porcelain").splitlines())
        up = git(wt, "rev-list", "--left-right", "--count", f"{br}...origin/{br}", check=False)
        ahead, behind = up.split() if up else ("?", "?")
        base = "main" if br in TRACKS else track_of(core, br)
        stale = git(core, "rev-list", "--count", f"{br}..{base}", check=False) if base else ""
        last = git(wt, "log", "-1", "--format=%cs %s")
        rows.append((wt.relative_to(wt.parent.parent) if wt != core else Path("core"), br, dirty, ahead, behind, stale, last, tasks(wt)))

    lines = [f"# Studio ({time.strftime('%Y-%m-%d %H:%M')})", "",
             "| Folder | Branch | Uncommitted | Unpushed | Behind its base | Last commit |", "|---|---|---|---|---|---|"]
    for folder, br, dirty, ahead, behind, stale, last, _ in rows:
        push = "not on GitHub" if ahead == "?" else (ahead if ahead != "0" else "")
        lines.append(f"| `{folder.as_posix()}` | `{br}` | {dirty or ''} | {push} | {stale if stale not in ('', '0') else ''} | {last} |")
    games = [(folder, br, t) for folder, br, *_, t in rows if br.startswith("game/")]
    lines += ["", "## Games", "", "| Game | Status | Next | Open / done tasks |", "|---|---|---|---|"]
    for folder, br, t in games:
        st, nx, op, dn = t or ("no TASKS.md", "-", 0, 0)
        lines.append(f"| `{br.removeprefix('game/')}` | {st} | {nx} | {op} / {dn} |")
    text = "\n".join(lines) + "\n"
    print(text)
    if write:
        (studio_root() / "STUDIO.md").write_text(text, encoding="utf-8")
        bat = studio_root() / "studio.bat"
        if not bat.exists():
            bat.write_text('@echo off\ncd /d "%~dp0"\npython core\\tools\\studio.py %*\n', encoding="utf-8")


def new(name, track):
    core, root = worktrees()[0][0], studio_root()
    branch, module = f"game/{name}", name.replace("-", "_")
    target = root / "games" / name
    git(core, "worktree", "add", "-b", branch, str(target), track)
    git(core, "config", f"branch.{branch}.studio-track", track)
    game_dir = target / "games" / module
    shutil.copytree(core / "games" / "_template", game_dir)
    (game_dir / "TASKS.md").write_text(
        f"# Tasks: {name}\n\nStatus: started\nNext: Phase 0 of the skill (scope, anti-cheat, route)\n\n"
        "## Todo\n- [ ] Evidence: build version + exe SHA-256 (tools/evidence.py)\n- [ ] active hook\n"
        "- [ ] health hook\n- [ ] shot hook\n- [ ] feel tuned with the player\n\n## Done\n", encoding="utf-8")
    git(target, "add", "-A")
    git(target, "commit", "-m", f"Start {name} from the template")
    print(f"{branch} at {target} (track {track}); edit games/{module}/ there.")


def sync():
    core = worktrees()[0][0]
    by_branch = {br: wt for wt, br in worktrees()}
    order = [(t, "main") for t in TRACKS if t in by_branch]
    order += [(br, track_of(core, br)) for br in by_branch if br.startswith("game/") and track_of(core, br)]
    for br, base in order:
        wt = by_branch[br]
        if git(wt, "status", "--porcelain"):
            raise SystemExit(f"{br}: uncommitted changes in {wt}, commit them first")
        r = subprocess.run(["git", "merge", "--no-edit", base], cwd=wt, capture_output=True, text=True, encoding="utf-8")
        if r.returncode:
            conflicts = git(wt, "diff", "--name-only", "--diff-filter=U", check=False)
            subprocess.run(["git", "merge", "--abort"], cwd=wt)
            raise SystemExit(f"{br}: merging {base} conflicts in: {conflicts or r.stderr.strip()}\n"
                             f"Merge was undone. Resolve by hand in {wt}: git merge {base}")
        print(f"{br} <- {base}: {r.stdout.strip().splitlines()[0] if r.stdout.strip() else 'ok'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    n = sub.add_parser("new")
    n.add_argument("name", help="game name, lowercase with dashes, e.g. ace-combat-7")
    n.add_argument("--track", required=True, choices=TRACKS)
    sub.add_parser("sync")
    sub.add_parser("status")
    args = ap.parse_args()
    if args.cmd == "new":
        new(args.name, args.track)
    elif args.cmd == "sync":
        sync()
    else:
        status()


if __name__ == "__main__":
    sys.exit(main())
