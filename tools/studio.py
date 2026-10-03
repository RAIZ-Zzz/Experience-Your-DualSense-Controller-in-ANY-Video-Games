"""Studio: one folder per branch (git worktrees) and a dashboard of every game's progress.

    studio/
      core/                     main            shared framework, tools, skill, template
      tracks/online/            online          games with anti-cheat (offline modes only) + rules
      tracks/single-player/     single-player   games without anti-cheat

    python core/tools/studio.py                     status of every worktree -> prints it and writes STUDIO.md
    python core/tools/studio.py new <name> --track online|single-player
                                                    games/<module>/ in that track, template copied in
    python core/tools/studio.py sync                merge main -> tracks; stops at the first conflict

Each game is a folder games/<module>/ on its track and keeps its progress in TASKS.md there:
"Status:" and "Next:" lines plus a checklist.
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


def tasks(wt):
    """[(module, status, next, open, done)] from every games/*/TASKS.md except the template."""
    out = []
    for f in sorted(wt.glob("games/*/TASKS.md")):
        if f.parent.name.startswith("_"):
            continue
        t = f.read_text(encoding="utf-8")
        field = lambda k: (re.search(rf"^{k}:\s*(.+)$", t, re.M) or [None, "-"])[1].strip()
        out.append((f.parent.name, field("Status"), field("Next"), t.count("- [ ]"), t.count("- [x]")))
    return out


def status(write=True):
    core = worktrees()[0][0]
    rows = []
    for wt, br in worktrees():
        dirty = len(git(wt, "status", "--porcelain").splitlines())
        up = git(wt, "rev-list", "--left-right", "--count", f"{br}...origin/{br}", check=False)
        ahead, behind = up.split() if up else ("?", "?")
        stale = git(core, "rev-list", "--count", f"{br}..main", check=False) if br in TRACKS else ""
        last = git(wt, "log", "-1", "--format=%cs %s")
        rows.append((wt.relative_to(wt.parent.parent) if wt != core else Path("core"), br, dirty, ahead, behind, stale, last, tasks(wt)))

    lines = [f"# Studio ({time.strftime('%Y-%m-%d %H:%M')})", "",
             "| Folder | Branch | Uncommitted | Unpushed | Behind its base | Last commit |", "|---|---|---|---|---|---|"]
    for folder, br, dirty, ahead, behind, stale, last, _ in rows:
        push = "not on GitHub" if ahead == "?" else (ahead if ahead != "0" else "")
        lines.append(f"| `{folder.as_posix()}` | `{br}` | {dirty or ''} | {push} | {stale if stale not in ('', '0') else ''} | {last} |")
    lines += ["", "## Games", "", "| Game | Track | Status | Next | Open / done tasks |", "|---|---|---|---|---|"]
    for _, br, *_, games in rows:
        for module, st, nx, op, dn in games:
            lines.append(f"| `{module}` | `{br}` | {st} | {nx} | {op} / {dn} |")
    text = "\n".join(lines) + "\n"
    print(text)
    if write:
        (studio_root() / "STUDIO.md").write_text(text, encoding="utf-8")
        bat = studio_root() / "studio.bat"
        if not bat.exists():
            bat.write_text('@echo off\ncd /d "%~dp0"\npython core\\tools\\studio.py %*\n', encoding="utf-8")


def new(name, track):
    by_branch = {br: wt for wt, br in worktrees()}
    if track not in by_branch:
        raise SystemExit(f"no worktree for {track}")
    target, module = by_branch[track], name.replace("-", "_")
    game_dir = target / "games" / module
    if game_dir.exists():
        raise SystemExit(f"{game_dir} already exists")
    shutil.copytree(target / "games" / "_template", game_dir)
    (game_dir / "TASKS.md").write_text(
        f"# Tasks: {name}\n\nStatus: started\nNext: Phase 0 of the skill (audit, research, proposal)\n\n"
        "## Todo\n- [ ] Evidence: build version + exe SHA-256 (tools/evidence.py)\n- [ ] active hook\n"
        "- [ ] health hook\n- [ ] shot hook\n- [ ] feel tuned with the player\n\n## Done\n", encoding="utf-8")
    git(target, "add", "--", f"games/{module}")
    git(target, "commit", "-m", f"Start {name} from the template", "--", f"games/{module}")
    print(f"{game_dir} on {track}; edit it there.")


def sync():
    by_branch = {br: wt for wt, br in worktrees()}
    for br, base in [(t, "main") for t in TRACKS if t in by_branch]:
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
