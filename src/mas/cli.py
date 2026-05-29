import argparse
from collections.abc import Sequence

from mas import __version__

_PLACEHOLDER_MESSAGE = (
    "mas: MVP not implemented yet. "
    "See docs/roadmap.md for the milestone breakdown."
)

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
        help=_PLACEHOLDER_MESSAGE,
        description=_PLACEHOLDER_MESSAGE,
    )
    return parser


def _get_parser() -> argparse.ArgumentParser:
    global _PARSER
    if _PARSER is None:
        _PARSER = build_parser()
    return _PARSER


def _handle_run() -> None:
    print(_PLACEHOLDER_MESSAGE)


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
