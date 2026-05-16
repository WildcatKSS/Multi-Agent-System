import argparse
from collections.abc import Sequence

from mas import __version__

_PLACEHOLDER_MESSAGE = (
    "mas: MVP not implemented yet. "
    "See docs/roadmap.md for the milestone breakdown."
)
_RUN_HELP = "Placeholder entrypoint; prints a notice and exits."


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
    subparsers.add_parser("run", help=_RUN_HELP, description=_RUN_HELP)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        print(_PLACEHOLDER_MESSAGE)
    return 0
