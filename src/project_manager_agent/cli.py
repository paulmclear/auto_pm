"""
Interactive CLI for the Project Manager Agent.

Launch the interactive shell:
    uv run pm

Run a single command:
    uv run pm daily --project 1
    uv run pm report --project 2
    uv run pm weekly
    uv run pm web
    uv run pm seed
    uv run pm reset
"""

import argparse
import cmd
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Optional

from project_manager_agent.core.db.engine import create_tables


def _run_daily(project_id: Optional[int] = None) -> None:
    from project_manager_agent.agents.project_manager.agent import run

    create_tables()
    run(project_id=project_id)


def _run_report(project_id: Optional[int] = None, output: Optional[Path] = None) -> None:
    from project_manager_agent.agents.reporter.agent import run

    run(output_path=output, project_id=project_id)


def _run_weekly(output: Optional[Path] = None) -> None:
    from project_manager_agent.agents.reporter.weekly import run

    run(output_path=output)


def _run_web() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "project_manager_agent.web.app:create_app",
            "--factory",
            "--reload",
        ],
    )


def _run_seed() -> None:
    from project_manager_agent.core.db.engine import get_session
    from project_manager_agent.core.db.seed import seed_all_demo_data

    create_tables()
    with get_session() as session:
        project_ids = seed_all_demo_data(session)
    print(f"Seeded {len(project_ids)} demo projects.")


def _run_reset() -> None:
    subprocess.run([sys.executable, "reset.py"])


# ---------------------------------------------------------------------------
# Interactive shell
# ---------------------------------------------------------------------------


class PMShell(cmd.Cmd):
    intro = "Project Manager CLI. Type help or ? for commands.\n"
    prompt = "pm> "

    def do_daily(self, arg: str) -> None:
        """Run the PM agent daily loop.  Usage: daily [--project ID]"""
        parser = argparse.ArgumentParser(prog="daily")
        parser.add_argument("--project", type=int, default=None)
        try:
            args = parser.parse_args(shlex.split(arg))
        except SystemExit:
            return
        _run_daily(project_id=args.project)

    def do_report(self, arg: str) -> None:
        """Generate a status report.  Usage: report [--project ID] [--output PATH]"""
        parser = argparse.ArgumentParser(prog="report")
        parser.add_argument("--project", type=int, default=None)
        parser.add_argument("--output", type=Path, default=None)
        try:
            args = parser.parse_args(shlex.split(arg))
        except SystemExit:
            return
        _run_report(project_id=args.project, output=args.output)

    def do_weekly(self, arg: str) -> None:
        """Generate a weekly summary report.  Usage: weekly [--output PATH]"""
        parser = argparse.ArgumentParser(prog="weekly")
        parser.add_argument("--output", type=Path, default=None)
        try:
            args = parser.parse_args(shlex.split(arg))
        except SystemExit:
            return
        _run_weekly(output=args.output)

    def do_web(self, arg: str) -> None:
        """Start the web UI (uvicorn with --reload)."""
        _run_web()

    def do_seed(self, arg: str) -> None:
        """Load demo data into the database."""
        _run_seed()

    def do_reset(self, arg: str) -> None:
        """Reset all runtime data to a clean state."""
        _run_reset()

    def do_quit(self, arg: str) -> bool:
        """Exit the CLI."""
        return True

    do_exit = do_quit
    do_EOF = do_quit


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) > 1:
        # Non-interactive: run a single command
        command = sys.argv[1]
        rest = sys.argv[2:]

        dispatch = {
            "daily": lambda: _run_daily(
                project_id=_parse_project(rest),
            ),
            "report": lambda: _run_report(
                project_id=_parse_project(rest),
                output=_parse_output(rest),
            ),
            "weekly": lambda: _run_weekly(
                output=_parse_output(rest),
            ),
            "web": _run_web,
            "seed": _run_seed,
            "reset": _run_reset,
        }

        if command in ("--help", "-h"):
            print("Usage: pm [command] [options]")
            print()
            print("Commands:")
            print("  daily    Run the PM agent daily loop")
            print("  report   Generate a status report")
            print("  weekly   Generate a weekly summary report")
            print("  web      Start the web UI")
            print("  seed     Load demo data into the database")
            print("  reset    Reset all runtime data")
            print()
            print("Run with no arguments for interactive mode.")
        elif command in dispatch:
            dispatch[command]()
        else:
            print(f"Unknown command: {command}")
            print(f"Available: {', '.join(dispatch)}")
            sys.exit(1)
    else:
        PMShell().cmdloop()


def _parse_project(args: list[str]) -> Optional[int]:
    if "--project" in args:
        idx = args.index("--project")
        return int(args[idx + 1])
    return None


def _parse_output(args: list[str]) -> Optional[Path]:
    if "--output" in args:
        idx = args.index("--output")
        return Path(args[idx + 1])
    return None


if __name__ == "__main__":
    main()
