import pytest

from keywords.exceptions import ProvisioningError
from keywords.ClusterKeywords import ClusterKeywords
from keywords.utils import log_info
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient


def pytest_addoption(parser):
    parser.addoption("--client-one-platform", action="store", help="client-one-platform: the platform to assign to the first client")
    parser.addoption("--client-one-version", action="store", help="client-one-version: the version to download / install for the first client")
    parser.addoption("--client-one-host", action="store", help="client-one-host: the host to start to the first client on")
    parser.addoption("--client-one-port", action="store", help="client-one-port: the port to assign to the first client")
    parser.addoption("--client-one-mode", action="store", help="client-one-mode: the mode of sync_gateway to run tests against, channel_cache ('cc') or distributed_index ('di')")
    parser.addoption("--client-one-storage-engine", action="store", help="client-one-storage-engine: the storage engine to use with the first client")

    parser.addoption("--client-two-platform", action="store", help="client-two-platform: the platform to assign to the first client")
    parser.addoption("--client-two-version", action="store", help="client-two-version: the version to download / install for the first client")
    parser.addoption("--client-two-host", action="store", help="client-two-host: the host to start to the first client on")
    parser.addoption("--client-two-port", action="store", help="client-two-port: the port to assign to the first client")
    parser.addoption("--client-two-storage-engine", action="store", help="client-two-storage-engine: the storage engine to use with the first client")
    parser.addoption("--cbs-server-version", action="store", help="cbs-server-version: version of Couchbase Server to install and run tests against")
    parser.addoption("--skip-provisioning", action="store_true", help="Skip cluster provisioning at setup", default=False)


# This will get called once before the first test that
# runs with this as input parameters in this file
# This setup will be called once for all tests in the
# testsuites/listener/shared/client_sg/ directory
@pytest.fixture(scope="session")
def setup_client_suite(request):
    """Suite setup fixture for client tests"""
    client_one_platform = request.config.getoption("--client-one-platform")
    client_one_version = request.config.getoption("--client-one-version")
    client_one_host = request.config.getoption("--client-one-host")
    client_one_port = request.config.getoption("--client-one-port")
    client_one_storage_engine = request.config.getoption("--client-one-storage-engine")

    client_two_platform = request.config.getoption("--client-two-platform")
    client_two_version = request.config.getoption("--client-two-version")
    client_two_host = request.config.getoption("--client-two-host")
    client_two_port = request.config.getoption("--client-two-port")
    client_two_storage_engine = request.config.getoption("--client-two-storage-engine")

    if client_one_platform == "sync_gateway" and client_two_platform == "sync_gateway":
        raise ProvisioningError("Both platforms cannot be sync_gateway")

    # We'll enforce client_one as SG for SG <-> CBL replication
    if client_two_platform == "sync_gateway":
        raise ProvisioningError("sync_gateway has to be client-one-platform")

    if client_one_platform == "sync_gateway":
        # SG <-> CBL replication
        client_one = "sync_gateway"
        skip_provisioning = request.config.getoption("--skip-provisioning")
        sync_gateway_version = client_one_version
        sync_gateway_mode = request.config.getoption("--client-one-mode")
        cbs_server_version = request.config.getoption("--cbs-server-version")

        cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, sync_gateway_mode)
        sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sync_gateway_mode)

        if not skip_provisioning:
            log_info("Installing Sync Gateway + Couchbase Server + Accels ('di' only)")
            cluster_utils = ClusterKeywords()
            cluster_utils.provision_cluster(
                cluster_config=cluster_config,
                server_version=cbs_server_version,
                sync_gateway_version=sync_gateway_version,
                sync_gateway_config=sg_config
            )
    else:
        # No SG, its P2P replication
        # We'll setup client 1 here
        client_one = LiteServFactory.create(platform=client_one_platform,
                                            version_build=client_one_version,
                                            host=client_one_host,
                                            port=client_one_port,
                                            storage_engine=client_one_storage_engine)

        log_info("Downloading LiteCoreServ ...")
        # Download LiteServ
        client_one.download()

        # Install LiteServ
        client_one.install()

    # Client 2 setup is common
    client_two = LiteServFactory.create(platform=client_two_platform,
                                        version_build=client_two_version,
                                        host=client_two_host,
                                        port=client_two_port,
                                        storage_engine=client_two_storage_engine)

    log_info("Downloading LiteCoreServ ...")
    # Download LiteServ
    # client_two.download()

    # Install LiteServ
    # client_two.install()

    # Wait at the yeild until tests referencing this suite setup have run,
    # Then execute the teardown
    yield {
        "client_one": client_one,
        "cluster_config": cluster_config,
        "sg_mode": sync_gateway_mode,
        "client_two": client_two
    }

    log_info("Tearing down suite ...")


# Passed to each testcase, run for each test_* method in client_sg folder
@pytest.fixture(scope="function")
def setup_client_test(request, setup_client_suite):
    """Test setup fixture for client tests"""
    log_info("Setting up client test ...")

    client_one = setup_client_suite["client_one"]
    client_two = setup_client_suite["client_two"]
    cluster_config = setup_client_suite["cluster_config"]
    test_name = request.node.name

    client = MobileRestClient()

    # Start LiteCoreServ and delete any databases
    #ls_url = liteserv.start("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now()))
    ls_url_two = "http://10.17.0.22:52000"
    client.delete_databases(ls_url_two)

    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config=cluster_config)

    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]

    # Yield values to test case via fixture argument
    yield {
        "cluster_config": cluster_config,
        "sg_mode": setup_client_suite["sg_mode"],
        "ls_url_two": ls_url_two,
        "ls_url_one": sg_url,
        "ls_url_one_admin": sg_admin_url
    }

    log_info("Tearing down test")
