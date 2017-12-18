import pytest

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import log_info
from libraries.testkit import cluster


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.attachments
def test_setup_android_app(params_from_base_test_setup):
    """
    1. Set up couchbase server.
    2. Set up sync-gateway
    3. Reset with sync-gateway with specified config
    4. This is only for Android app set up.
    """

    log_info("Running 'test_inline_large_attachments' ...")

    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_mode = params_from_base_test_setup["mode"]

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_travel_sample", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
