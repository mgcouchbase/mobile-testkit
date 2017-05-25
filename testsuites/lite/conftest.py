import pytest
import os

from keywords.exceptions import ProvisioningError
from keywords.ClusterKeywords import ClusterKeywords
from keywords.utils import log_info
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient
from libraries.testkit import cluster


def pytest_addoption(parser):
    parser.addoption("--server-platform", action="store", help="server-platform: the platform to assign to the first client")
    parser.addoption("--server-version", action="store", help="server-version: the version to download / install for the first client")
    parser.addoption("--server-host", action="store", help="server-host: the host to start to the first client on")
    parser.addoption("--server-port", action="store", help="server-port: the port to assign to the first client")
    parser.addoption("--server-mode", action="store", help="server-mode: the mode of sync_gateway to run tests against, channel_cache ('cc') or distributed_index ('di')")
    parser.addoption("--server-storage-engine", action="store", help="server-storage-engine: the storage engine to use with the first client")

    parser.addoption("--client-platform", action="store", help="client-platform: the platform to assign to the first client")
    parser.addoption("--client-version", action="store", help="client-version: the version to download / install for the first client")
    parser.addoption("--client-host", action="store", help="client-host: the host to start to the first client on")
    parser.addoption("--client-port", action="store", help="client-port: the port to assign to the first client")
    parser.addoption("--client-storage-engine", action="store", help="client-storage-engine: the storage engine to use with the first client")
    parser.addoption("--cbs-server-version", action="store", help="cbs-server-version: version of Couchbase Server to install and run tests against")
    parser.addoption("--skip-provisioning", action="store_true", help="Skip cluster provisioning at setup", default=False)


# This will get called once before the first test that
# runs with this as input parameters in this file
# This setup will be called once for all tests in the
# testsuites/listener/shared/client_sg/ directory
@pytest.fixture(scope="session")
def setup_client_suite(request):
    """Suite setup fixture for client tests"""
    server_platform = request.config.getoption("--server-platform")
    server_version = request.config.getoption("--server-version")
    server_host = request.config.getoption("--server-host")
    server_port = request.config.getoption("--server-port")
    server_storage_engine = request.config.getoption("--server-storage-engine")

    client_platform = request.config.getoption("--client-platform")
    client_version = request.config.getoption("--client-version")
    client_host = request.config.getoption("--client-host")
    client_port = request.config.getoption("--client-port")
    client_storage_engine = request.config.getoption("--client-storage-engine")

    if server_platform == "sync_gateway" and client_platform == "sync_gateway":
        raise ProvisioningError("Both platforms cannot be sync_gateway")

    # We'll enforce server as SG for SG <-> CBL replication
    if client_platform == "sync_gateway":
        raise ProvisioningError("sync_gateway has to be server-platform")

    cluster_config = None
    sync_gateway_mode = None
    sg_config = None

    if server_platform == "sync_gateway":
        # SG <-> CBL replication
        server = "sync_gateway"
        skip_provisioning = request.config.getoption("--skip-provisioning")
        sync_gateway_version = server_version
        sync_gateway_mode = request.config.getoption("--server-mode")
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
        server = LiteServFactory.create(platform=server_platform,
                                        version_build=server_version,
                                        host=server_host,
                                        port=server_port,
                                        storage_engine=server_storage_engine)

        log_info("Downloading LiteCoreServ ...")
        # Download LiteServ
        # server.download()

        # Install LiteServ
        # server.install()

    # Client 2 setup is common
    client = LiteServFactory.create(platform=client_platform,
                                    version_build=client_version,
                                    host=client_host,
                                    port=client_port,
                                    storage_engine=client_storage_engine)

    log_info("Downloading LiteCoreServ ...")
    # Download LiteServ
    # client.download()

    # Install LiteServ
    # client.install()

    # Wait at the yeild until tests referencing this suite setup have run,
    # Then execute the teardown
    yield {
        "server": server,
        "server_platform": server_platform,
        "cluster_config": cluster_config,
        "sg_mode": sync_gateway_mode,
        "client": client,
        "sg_config": sg_config
    }

    log_info("Tearing down suite ...")


# Passed to each testcase, run for each test_* method in client_sg folder
@pytest.fixture(scope="function")
def setup_client_test(request, setup_client_suite):
    """Test setup fixture for client tests"""
    log_info("Setting up client test ...")

    server = setup_client_suite["server"]
    server_platform = setup_client_suite["server_platform"]
    client = setup_client_suite["client"]
    cluster_config = setup_client_suite["cluster_config"]
    sg_config = setup_client_suite["sg_config"]
    test_name = request.node.name

    client = MobileRestClient()

    # Start LiteCoreServ and delete any databases
    #ls_url = liteserv.start("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now()))
    client_url = "http://localhost:52000"
    client.delete_databases(client_url)

    server_url = None
    server_admin_url = None

    if server_platform == "sync_gateway":
        cluster_helper = ClusterKeywords()
        cluster_hosts = cluster_helper.get_cluster_topology(cluster_config=cluster_config)

        server_url = cluster_hosts["sync_gateways"][0]["public"]
        server_admin_url = cluster_hosts["sync_gateways"][0]["admin"]

        clstr = cluster.Cluster(config=cluster_config)
        clstr.reset(sg_config_path=sg_config)
    else:
        # server_url = liteserv.start("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now()))
        server_url = "http://localhost:51000"

    # Yield values to test case via fixture argument
    yield {
        "cluster_config": cluster_config,
        "client_url": client_url,
        "server_url": server_url,
        "server_url_admin": server_admin_url,
        "server_platform": server_platform
    }

    log_info("Tearing down test")
    client.delete_databases(client_url)

    if server_platform != "sync_gateway":
        client.delete_databases(server_url)
