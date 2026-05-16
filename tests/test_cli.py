import pytest

from mas import __version__
from mas.cli import PLACEHOLDER_MESSAGE, main


def test_version_flag_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_run_subcommand_prints_placeholder(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["run"])
    assert exit_code == 0
    assert PLACEHOLDER_MESSAGE in capsys.readouterr().out


def test_no_args_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])
    assert exit_code == 0
    assert "usage:" in capsys.readouterr().out.lower()
