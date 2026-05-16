import re
import subprocess
import sys
from importlib.metadata import entry_points

import mas


def test_package_version_is_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:[-+]\S+)?", mas.__version__)


def test_mas_console_script_is_registered() -> None:
    mas_eps = [
        ep for ep in entry_points(group="console_scripts") if ep.name == "mas"
    ]
    assert len(mas_eps) == 1
    assert mas_eps[0].value == "mas.cli:main"


def test_python_dash_m_invocation_prints_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mas", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert mas.__version__ in result.stdout
