import argparse
from collections.abc import Sequence

from mas import __version__
from mas.domain.plan import Plan, Step
from mas.runtime import Runtime
from mas.workflow import PolicyEngine

_RUN_HELP = "Run a demo plan through the single-worker runtime."

_PARSER: argparse.ArgumentParser | None = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mas",
        description="Multi-Agent System command-line interface (MVP scaffold).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"mas {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "run",
        help=_RUN_HELP,
        description=_RUN_HELP,
    )
    return parser


def _get_parser() -> argparse.ArgumentParser:
    global _PARSER
    if _PARSER is None:
        _PARSER = build_parser()
    return _PARSER


def _demo_plan() -> Plan:
    """Build a small example plan to demonstrate the runtime."""
    return Plan(
        id="demo-plan",
        task_id="demo-task",
        steps=[
            Step(id="fetch", action="fetch_input"),
            Step(id="process", action="process_data", depends_on=["fetch"]),
            Step(id="summarize", action="write_summary", depends_on=["process"]),
        ],
        reasoning="Linear demo plan executed by the baseline single-worker runtime.",
    )


def _handle_run() -> None:
    result = Runtime(PolicyEngine()).run(_demo_plan())
    print(f"workflow: {result.workflow_id}")
    print(f"final state: {result.final_state.value}")
    print(f"completed: {result.completed}")
    for step_result in result.step_results:
        status = "ok" if step_result.success else f"failed ({step_result.error})"
        print(f"  - {step_result.step_id}: {status}")


_COMMAND_HANDLERS = {
    "run": _handle_run,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = _get_parser()
    args = parser.parse_args(argv)
    handler = _COMMAND_HANDLERS.get(args.command)
    if handler:
        handler()
    return 0
