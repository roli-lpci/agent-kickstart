from __future__ import annotations

import argparse
import filecmp
import json
import re
import shlex
import shutil
import subprocess
import sys
from importlib.resources import as_file, files
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import List, Optional, Tuple

from . import __version__
from . import evidence

TOOL = "agent-kickstart"
REPOSITORY = "https://github.com/hermes-labs-ai/agent-kickstart"
STARTER_PATHS = ("python", "javascript")


def asset_root():
    return files("agent_kickstart").joinpath("assets")


def asset_files(root: Path):
    return sorted(path for path in root.rglob("*") if path.is_file())


NODE_MINIMUM_MAJOR = 18
NODE_PROBE_TIMEOUT_SECONDS = 5.0


def _probe_node_version():
    return subprocess.run(
        ["node", "--version"], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=NODE_PROBE_TIMEOUT_SECONDS,
    )


def require_runtime() -> None:
    missing = [name for name in ("claude", "node") if shutil.which(name) is None]
    if missing:
        raise RuntimeError(
            "Missing required command(s): " + ", ".join(missing) +
            ". Install or repair them, then run this command again."
        )
    try:
        result = _probe_node_version()
    except (OSError, subprocess.SubprocessError):
        raise RuntimeError(
            "Could not read the Node.js version with 'node --version'. "
            f"Install or repair Node.js {NODE_MINIMUM_MAJOR} or newer, then run this command again."
        ) from None
    version = result.stdout.strip()
    match = re.match(r"v?(\d+)", version)
    if result.returncode or not match:
        raise RuntimeError(
            "Could not read the Node.js version with 'node --version'. "
            f"Install or repair Node.js {NODE_MINIMUM_MAJOR} or newer, then run this command again."
        )
    if int(match.group(1)) < NODE_MINIMUM_MAJOR:
        raise RuntimeError(
            f"Node.js {NODE_MINIMUM_MAJOR} or newer is required; this computer has Node.js {version}. "
            "Update Node.js, then run this command again."
        )


def runtime_findings(starter_path: str = "python") -> List[dict]:
    """The same checks require_runtime() enforces, reported instead of raised.

    A preview has to survive a machine that is not ready yet: the point is to
    show the person what is missing, not to refuse to describe the plan.
    """
    findings = []
    checks = [("claude", "Claude Code"), ("node", "Node.js")]
    if starter_path == "javascript":
        # The javascript route's first offered command is `git clone`, so a
        # missing `git` would fail that command exactly like a missing node
        # or claude would fail the others.
        checks.append(("git", "Git"))
    for name, label in checks:
        if shutil.which(name) is None:
            findings.append(evidence.finding(
                f"runtime.{name}.missing", "fail",
                f"{label} is not available in your command path.",
                f"Install or repair {label}, confirm '{name} --version' works, then run this again.",
            ))
    if any(item["id"] == "runtime.node.missing" for item in findings):
        return findings

    # A preview must answer even when the probe does not: a hung or unrunnable
    # `node` becomes an honest "unknown", never a hang or an escaped traceback.
    try:
        result = _probe_node_version()
    except (OSError, subprocess.SubprocessError):
        findings.append(evidence.finding(
            "runtime.node.version", "unknown",
            "'node --version' could not be run or did not answer within "
            f"{NODE_PROBE_TIMEOUT_SECONDS:g} seconds.",
            "Confirm 'node --version' works, install or repair Node.js "
            f"{NODE_MINIMUM_MAJOR} or newer, then run this again.",
        ))
        return findings
    version = result.stdout.strip()
    match = re.match(r"v?(\d+)", version)
    if result.returncode or not match:
        findings.append(evidence.finding(
            "runtime.node.version", "unknown",
            "Could not read the Node.js version with 'node --version'.",
            f"Install or repair Node.js {NODE_MINIMUM_MAJOR} or newer, then run this again.",
        ))
    elif int(match.group(1)) < NODE_MINIMUM_MAJOR:
        findings.append(evidence.finding(
            "runtime.node.version", "fail",
            f"Node.js {NODE_MINIMUM_MAJOR} or newer is required; this computer has Node.js {version}.",
            "Update Node.js, then run this again.",
        ))
    return findings


# Install rules that used to live only in AGENTS.md prose. A beginner-facing
# installer should not depend on the installing agent remembering them.
#
# Roots protected together with everything beneath them: installing into
# /usr/local/share or C:\Program Files\Kickstart is as wrong as installing
# directly into the root itself.
SYSTEM_ROOTS = (
    "/bin", "/sbin", "/usr", "/etc", "/var", "/opt",
    "/System", "/Library", "/Applications",
    "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)",
)

# Roots protected only as the exact target. Every path on the machine lives
# beneath "/" or "C:\", and the scratch folder a person is handed lives
# beneath /tmp, so a project folder inside these is ordinary and allowed.
SYSTEM_EXACT_ROOTS = ("/", "/tmp", "C:\\")

WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")


def path_parts(text: str) -> Tuple[str, ...]:
    """Comparable path components, case-folded only where the platform is.

    Windows treats C:\\WINDOWS and C:\\Windows as one folder, so a comparison
    that respected case there would let a protected root through under a
    different spelling. POSIX is case-sensitive, so folding it instead would
    refuse a legitimate /Usr or /Opt a person owns.
    """
    if WINDOWS_PATH.match(text):
        return tuple(part.lower() for part in PureWindowsPath(text).parts)
    return PurePosixPath(text).parts


def protected_root(target: str) -> Optional[str]:
    """The system root `target` is equal to or sits beneath, if any.

    Components are compared component-wise, never as string prefixes, so
    C:\\Program Files (x86) is not mistaken for a child of C:\\Program Files
    and /usrland is not mistaken for a child of /usr.
    """
    parts = path_parts(target)
    for root in SYSTEM_EXACT_ROOTS:
        if parts == path_parts(root):
            return root
    for root in SYSTEM_ROOTS:
        root_parts = path_parts(root)
        if parts[:len(root_parts)] == root_parts:
            return root
    return None


def target_problem(target: Path) -> Optional[Tuple[str, str]]:
    """Return (finding id, beginner-readable reason) if this target is unusable."""
    if target.exists() and not target.is_dir():
        return (
            "target.not-a-folder",
            f"{target} already exists and is not a folder. "
            "Agent Kickstart installs into a folder; point --target at a folder "
            "(existing or new) instead of a file.",
        )
    root = protected_root(str(target))
    if root is not None:
        placement = (
            f"{target} is a system path"
            if path_parts(str(target)) == path_parts(root)
            else f"{target} is inside {root}, a system path"
        )
        return (
            "target.system-path",
            f"{placement}. Agent Kickstart only installs into a project "
            "folder you own; make or choose a project folder and use it as --target.",
        )
    if target == Path.home():
        return (
            "target.home-root",
            f"{target} is your home directory itself. Agent Kickstart keeps everything "
            "inside one project folder; make a new folder inside your home directory "
            "and use that as --target.",
        )
    return None


def resolved_target(target: Path) -> Path:
    resolved = target.resolve()
    problem = target_problem(resolved)
    if problem:
        raise RuntimeError(problem[1])
    return resolved


def start_command(target: Path, platform: Optional[str] = None) -> str:
    platform = sys.platform if platform is None else platform
    if platform.startswith("win"):
        quoted_target = str(target).replace("'", "''")
        return f"Set-Location -LiteralPath '{quoted_target}'; claude '/kickstart'"
    return f'cd -- {shlex.quote(str(target))} && claude "/kickstart"'


def setup_commands(target: Path, starter_path: str) -> dict:
    """The commands a person actually types, per supported starter path."""
    posix_target = shlex.quote(str(target))
    windows_target = "'" + str(target).replace("'", "''") + "'"
    if starter_path == "python":
        return {
            "posix": [
                "pip install agent-kickstart",
                f"agent-kickstart install --target {posix_target}",
            ],
            "windows": [
                "pip install agent-kickstart",
                f"agent-kickstart install --target {windows_target}",
            ],
        }
    return {
        "posix": [
            f"git clone {REPOSITORY} {posix_target}",
            f"cd -- {posix_target}",
            "bash install.sh",
        ],
        "windows": [
            f"git clone {REPOSITORY} {windows_target}",
            f"Set-Location -LiteralPath {windows_target}",
            ".\\install.ps1",
        ],
    }


def managed_symlink(target: Path, relative: Path) -> Optional[Path]:
    """The first symlink among a managed path's components under target, if any.

    Kickstart never creates a symlink itself, so one appearing anywhere along
    a managed path — the file itself or a parent — could redirect a create or
    compare through it to somewhere outside `target`. Treat that path as
    unusable rather than following the link.
    """
    current = target
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return current
    return None


def file_actions(assets: Path, target: Path) -> List[dict]:
    rows = []
    for source in asset_files(assets):
        relative = source.relative_to(assets)
        dest = target / relative
        if managed_symlink(target, relative) is not None:
            action = "conflict"
        elif not dest.exists():
            action = "create"
        elif dest.is_file() and filecmp.cmp(source, dest, shallow=False):
            action = "unchanged"
        else:
            action = "conflict"
        rows.append({"path": relative.as_posix(), "action": action, "bytes": source.stat().st_size})
    return rows


def plan(target: Path, starter_path: str = "python") -> dict:
    """Describe an installation without touching the file system.

    Returns a Hermes Reliability Lab result envelope. Nothing under `target`
    is created, written, or modified. To classify a managed file as already
    installed or conflicting, its bytes are compared against the version
    Agent Kickstart would install; nothing else under `target` is read.
    """
    if starter_path not in STARTER_PATHS:
        raise RuntimeError(
            f"Unknown starter path: {starter_path}. Choose one of: {', '.join(STARTER_PATHS)}."
        )
    resolved = target.resolve()
    inputs = {
        "command": "plan",
        "starterPath": starter_path,
        "target": str(resolved),
    }
    findings: List[dict] = []
    rows: List[dict] = []
    summary = {"create": 0, "unchanged": 0, "conflict": 0}
    runtime_blocked = False

    problem = target_problem(resolved)
    if problem:
        findings.append(evidence.finding(problem[0], "fail", problem[1], path=str(resolved)))
        refused = True
    else:
        refused = False
        runtime_issues = runtime_findings(starter_path)
        findings.extend(runtime_issues)
        # Every claude/node case runtime_findings() reports — missing,
        # unreadable, timed out, or too old — is a case require_runtime()
        # would raise on, so install() would refuse before writing anything.
        # On the javascript route it also reports a missing `git`, which
        # would fail the offered `git clone` command instead.
        runtime_blocked = bool(runtime_issues)
        with as_file(asset_root()) as raw_assets:
            rows = file_actions(Path(raw_assets), resolved)
        for row in rows:
            summary[row["action"]] += 1
        if summary["conflict"]:
            findings.append(evidence.finding(
                "target.conflicting-files", "fail",
                f"{summary['conflict']} existing file(s) differ from the versions Agent Kickstart installs.",
                "Installation would stop before changing anything. Move or review these paths, then retry.",
            ))
        elif summary["create"] == 0:
            findings.append(evidence.finding(
                "target.already-installed", "warn",
                "Every managed file is already present and unchanged.",
                "Installing again would create nothing; the start command below still works.",
            ))
        if not resolved.exists():
            findings.append(evidence.finding(
                "target.will-be-created", "warn",
                f"{resolved} does not exist yet and would be created.",
                "Confirm this is the folder you meant before running the install command.",
            ))

    # The JavaScript route clones the whole repository into `target`, and Git
    # refuses to clone into a directory that already has anything in it — even
    # when none of Kickstart's own managed files would conflict.
    clone_blocked = (
        not refused and starter_path == "javascript"
        and resolved.is_dir() and any(resolved.iterdir())
    )
    if clone_blocked:
        findings.append(evidence.finding(
            "target.javascript-clone-nonempty", "fail",
            f"{resolved} already has files in it. The JavaScript route clones the "
            "repository directly into --target, and Git refuses to clone into a "
            "non-empty folder.",
            "Use an empty or new folder for --path javascript, or use the Python "
            "route (pip install agent-kickstart) to add Kickstart into this folder instead.",
        ))
    # Conflicts and runtime problems both stop the installer before it changes
    # anything, so a command offered here would be one the person pastes only
    # to watch it refuse.
    offer_commands = (
        not refused and not clone_blocked and not summary["conflict"] and not runtime_blocked
    )

    exit_code = 1 if evidence.worst_status(findings) == "fail" else 0
    return evidence.envelope(
        tool=TOOL,
        tool_version=__version__,
        command="plan",
        mode="preview",
        findings=findings,
        inputs=inputs,
        exit_code=exit_code,
        sha=evidence.git_sha(Path(__file__).resolve().parent),
        data={
            "starterPath": starter_path,
            "target": str(resolved),
            "repository": REPOSITORY,
            "refused": refused,
            "files": rows,
            "summary": summary,
            # Any blocking finding gets no runnable commands: offering one
            # would invite a person to paste the exact thing that was just
            # found to fail.
            "setupCommands": setup_commands(resolved, starter_path) if offer_commands else None,
            "startCommand": {
                "posix": start_command(resolved, platform="darwin"),
                "windows": start_command(resolved, platform="win32"),
            } if offer_commands else None,
        },
    )


def render_plan(result: dict) -> str:
    data = result["data"]
    lines = [
        f"Preview only — nothing was written. Target: {data['target']}",
        f"Starter path: {data['starterPath']}",
        "",
    ]
    if data["files"]:
        lines.append(f"Files Agent Kickstart would manage ({len(data['files'])}):")
        for row in data["files"]:
            lines.append(f"  {row['action']:<9} {row['path']}")
        summary = data["summary"]
        lines.append(
            f"  → create {summary['create']}, unchanged {summary['unchanged']}, conflict {summary['conflict']}"
        )
        lines.append("")
    if result["findings"]:
        lines.append("Findings:")
        for item in result["findings"]:
            lines.append(f"  [{item['severity']}] {item['summary']}")
            if item.get("detail"):
                lines.append(f"            {item['detail']}")
        lines.append("")
    if data["setupCommands"] is None:
        lines.append("No install command is offered for this target — see the findings above.")
        lines.append("")
    else:
        command_family = "windows" if sys.platform.startswith("win") else "posix"
        lines.append("Commands you would run:")
        for command in data["setupCommands"][command_family]:
            lines.append(f"  $ {command}")
        lines.append("")
        lines.append("Then, to start Kickstart:")
        lines.append(f"  $ {data['startCommand'][command_family]}")
        lines.append("")
    lines.append(f"Result: {result['status']} (preview, exit {result['exitCode']}). No files were changed.")
    return "\n".join(lines)


def run_plan(target: Path, starter_path: str, as_json: bool) -> int:
    result = plan(target, starter_path)
    print(json.dumps(result, indent=2) if as_json else render_plan(result))
    return result["exitCode"]


def install(target: Path) -> int:
    target = resolved_target(target)
    print(f"Installing Agent Kickstart inside: {target}")
    require_runtime()
    with as_file(asset_root()) as raw_assets:
        assets = Path(raw_assets)
        conflicts = [row["path"] for row in file_actions(assets, target) if row["action"] == "conflict"]
        if conflicts:
            listing = "\n".join(f"  - {path}" for path in conflicts)
            raise RuntimeError(
                "Installation stopped before changing files because these paths already differ:\n"
                f"{listing}\nMove or review them, then retry; nothing was overwritten."
            )
        created = 0
        for source in asset_files(assets):
            dest = target / source.relative_to(assets)
            if dest.exists():
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            created += 1

    engine = target / "agent-kickstart/bin/kickstart-state.mjs"
    engine.chmod(engine.stat().st_mode | 0o100)
    for action in ("init", "doctor"):
        result = subprocess.run(
            ["node", str(engine), action], cwd=target, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    print(f"Agent Kickstart is ready. Added {created} missing project-local file(s).")
    print("Claude Code must be closed and reopened once so the project command loads — part of installation, not an error.")
    print()
    print("──────────────── COPY THIS ONE LINE ────────────────")
    print(start_command(target))
    print("────────────────────────────────────────────────────")
    print()
    print("Paste it into your terminal (type /exit first if you are inside Claude Code). The same line works any time you want to come back.")
    return 0


def uninstall(target: Path) -> int:
    target = resolved_target(target)
    print(f"Removing managed Agent Kickstart files from: {target}")
    removed = 0
    preserved = []
    with as_file(asset_root()) as raw_assets:
        assets = Path(raw_assets)
        for source in asset_files(assets):
            relative = source.relative_to(assets)
            if relative.parts[:2] in (("agent-kickstart", "state"), ("agent-kickstart", "creations")):
                continue
            dest = target / relative
            if managed_symlink(target, relative) is not None:
                preserved.append(relative)
                continue
            if not dest.exists():
                continue
            if dest.is_file() and filecmp.cmp(source, dest, shallow=False):
                dest.unlink()
                removed += 1
            else:
                preserved.append(relative)
    print(f"Removed {removed} unchanged managed file(s).")
    print("Your state and agent-kickstart/creations/ were preserved.")
    if preserved:
        print("Locally changed files were also preserved:")
        for path in preserved:
            print(f"  - {path}")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog=TOOL)
    result.add_argument("--version", action="version", version=f"{TOOL} {__version__}")
    sub = result.add_subparsers(dest="command", required=True)
    commands = {}
    for name in ("install", "uninstall"):
        commands[name] = sub.add_parser(name)
        commands[name].add_argument("--target", type=Path, default=Path.cwd())
    commands["install"].add_argument(
        "--dry-run", action="store_true",
        help="show exactly what would be installed and change nothing",
    )
    commands["install"].add_argument(
        "--path", dest="starter_path", choices=STARTER_PATHS, default="python",
        help="starter path the preview should describe (with --dry-run)",
    )
    preview = sub.add_parser("plan", help="preview an installation without writing anything")
    preview.add_argument("--target", type=Path, default=Path.cwd())
    preview.add_argument("--path", dest="starter_path", choices=STARTER_PATHS, default="python")
    preview.add_argument("--json", dest="as_json", action="store_true",
                         help="emit a Hermes Reliability Lab result envelope")
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "plan":
            return run_plan(args.target, args.starter_path, args.as_json)
        if args.command == "install":
            if args.dry_run:
                return run_plan(args.target, args.starter_path, as_json=False)
            return install(args.target)
        return uninstall(args.target)
    except (RuntimeError, OSError) as error:
        print(f"Agent Kickstart could not complete {args.command}.", file=sys.stderr)
        print(f"What happened: {error}", file=sys.stderr)
        print("No existing user work was deleted or overwritten.", file=sys.stderr)
        return 1
