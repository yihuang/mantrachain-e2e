import pytest

from .network import (
    connect_custom_mantra,
    setup_geth,
    setup_mantra,
)


def pytest_addoption(parser):
    parser.addoption(
        "--chain-config",
        default="mantrachaind",
        action="store",
        metavar="CHAIN_CONFIG",
        required=False,
        help="Specify chain config to test",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "unmarked: fallback mark for unmarked tests")
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "asyncio: marks tests as asyncio")
    config.addinivalue_line("markers", "connect: marks connect related tests")
    config.addinivalue_line("markers", "skipped: marks skipped not supported tests")


def pytest_collection_modifyitems(items, config):
    keywordexpr = config.option.keyword
    markexpr = config.option.markexpr
    skip_connect = pytest.mark.skip(reason="Skipping connect tests by default")
    skip_rollback = pytest.mark.skip(
        reason="Skipping tests not supported for inveniemd"
    )
    chain_config = config.getoption("chain_config")

    for item in items:
        # add "unmarked" marker to tests that have no markers
        if not any(item.iter_markers()):
            item.add_marker("unmarked")

        # skip connect-marked tests unless explicitly requested
        if "connect" in item.keywords:
            if not (
                (keywordexpr and "connect" in keywordexpr)
                or (markexpr and "connect" in markexpr)
            ):
                item.add_marker(skip_connect)

        if "skipped" in item.keywords:
            if chain_config != "mantrachaind" and not (
                (keywordexpr and "skipped" in keywordexpr)
                or (markexpr and "skipped" in markexpr)
            ):
                item.add_marker(skip_rollback)


@pytest.fixture(scope="session")
def suspend_capture(pytestconfig):
    """
    used to pause in testing

    Example:
    ```
    def test_simple(suspend_capture):
        with suspend_capture:
            # read user input
            print(input())
    ```
    """

    class SuspendGuard:
        def __init__(self):
            self.capmanager = pytestconfig.pluginmanager.getplugin("capturemanager")

        def __enter__(self):
            self.capmanager.suspend_global_capture(in_=True)

        def __exit__(self, _1, _2, _3):
            self.capmanager.resume_global_capture()

    yield SuspendGuard()


@pytest.fixture(scope="session", params=[True])
def mantra(request, tmp_path_factory):
    chain = request.config.getoption("chain_config")
    path = tmp_path_factory.mktemp("mantra")
    yield from setup_mantra(path, 26650, chain)


@pytest.fixture(scope="session", params=[True])
def connect_mantra():
    yield from connect_custom_mantra()


@pytest.fixture(scope="session")
def geth(tmp_path_factory):
    path = tmp_path_factory.mktemp("geth")
    yield from setup_geth(path, 8545)
