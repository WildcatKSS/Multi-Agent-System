import re
from importlib.metadata import entry_points

import mas


def test_package_version_is_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", mas.__version__)


def test_mas_console_script_is_registered() -> None:
    mas_eps = [
        ep for ep in entry_points(group="console_scripts") if ep.name == "mas"
    ]
    assert len(mas_eps) == 1
    assert mas_eps[0].value == "mas.cli:main"
