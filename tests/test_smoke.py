import mas


def test_package_imports_and_exposes_version() -> None:
    assert isinstance(mas.__version__, str)
    assert mas.__version__
