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
    1.  Start LiteServ and Sync Gateway
    2.  Create 2 databases on LiteServ (ls_db1, ls_db2)
    3.  Start continuous push replication from ls_db1 to sg_db
    4.  Start continuous pull replication from sg_db to ls_db2
    5.  PUT 5 large inline attachments to ls_db1
    6.  DELETE the docs on ls_db1
    7.  PUT same 5 large inline attachments to ls_db1
    8.  Verify docs replicate to ls_db2
    9.  Purge ls_db1
    10. Verify docs removed
    """

    log_info("Running 'test_inline_large_attachments' ...")

    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_mode = params_from_base_test_setup["mode"]
    

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_travel_sample", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
