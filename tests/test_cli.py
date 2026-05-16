import pytest

from mas import __version__
from mas.cli import main


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
    assert "MVP not implemented yet" in capsys.readouterr().out


def test_run_subcommand_help_lists_description(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["run", "--help"])
    assert excinfo.value.code == 0
    assert "Placeholder entrypoint" in capsys.readouterr().out


def test_no_args_exits_with_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code == 2
    assert "required" in capsys.readouterr().err.lower()
