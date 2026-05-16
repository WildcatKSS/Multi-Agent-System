import re

import mas


def test_package_version_is_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", mas.__version__)
