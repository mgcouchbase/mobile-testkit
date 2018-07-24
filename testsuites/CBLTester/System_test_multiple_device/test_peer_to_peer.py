import pytest
import time

from concurrent.futures import ThreadPoolExecutor
from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from keywords import document, attachment
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from CBLClient.PeerToPeer import PeerToPeer
from requests.exceptions import HTTPError

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit.cluster import Cluster
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf

@pytest.mark.sanity
@pytest.mark.listener
def test_peer_to_peer_iosAndroid(params_from_base_suite_setup):
    """
        @summary:
        1. Enable allow_conflicts = true in SG config or do not set allow_conflicts
        2. Create docs on CBL.
        3. Update the doc few times.
        4. Do push replication to SG
        5. Create conflict on SG
        6. Do pull replication to CBL.
        7. Check the revision list for the doc
    """
    sg_db = "db"
    sg_url = params_from_base_suite_setup["sg_url"]
    sg_admin_url = params_from_base_suite_setup["sg_admin_url"]
    sg_mode = params_from_base_suite_setup["mode"]
    cluster_config = params_from_base_suite_setup["cluster_config"]
    sg_blip_url = params_from_base_suite_setup["target_url"]
    no_conflicts_enabled = params_from_base_suite_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_suite_setup["sync_gateway_version"]
    num_of_docs = 10
    channels = ["ABC"]
    # db = params_from_base_suite_setup["db"]
    # cbl_db = params_from_base_suite_setup["source_db"]   
    base_url_list = params_from_base_suite_setup["base_url_list"]
    socket_host_list = params_from_base_suite_setup["socket_host_list"]
    socket_port_list = params_from_base_suite_setup["socket_port_list"]
    cbl_db_list = params_from_base_suite_setup["cbl_db_list"]
    db_obj_list = params_from_base_suite_setup["db_obj_list"]
    db_name_list = params_from_base_suite_setup["db_name_list"]
    sg_config = params_from_base_suite_setup["sg_config"]
    username = "autotest"
    password = "password"
    channel = ["peerToPeer"]

    # Reset cluster to ensure no data in system
    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=sg_config)
    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channel)
    base_url_client = base_url_list[1]
    # base_url_android = base_url_list[0]
    base_url_server = base_url_list[0]

    peerToPeer_client = PeerToPeer(base_url_client)
    # peerToPeer_android = PeerToPeer(base_url_ios2)
    peerToPeer_server = PeerToPeer(base_url_server)
    # for base_url in zip(base_url_list):
    cbl_db_server = cbl_db_list[0]
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]
    
    server_host = socket_host_list[0]
    server_port = socket_port_list[0]
    client_host = socket_host_list[1]
    client_port = socket_port_list[1]
    # android_host = socket_host_list[0]
    # android_port = socket_port_list[0]
    print "base url list ", base_url_list
    # base_url_android = base_url_list[0]

    db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel)
    server_port_re = int(server_port)
    client_port_re = int(client_port)
    # server = peerToPeer_android.socket_connection(ios_port_re)
    peerToPeer_server.server_start(cbl_db_server)
    print "server starting ....."
    # server = peerToPeer_server.socket_connection(server_port_re)
    peerToPeer_client.client_start(host=server_host, port=server_port_re, server_db_name=db_name_server, client_database=cbl_db_client)
    print "client connecting ....."
    # peerToPeer_client.socket_clientConnection(ios_host, server_port_re)
    """
    with ThreadPoolExecutor(max_workers=1) as tpe:
        server_connection = tpe.submit(
            peerToPeer_server.socket_connection,
            server_port_re
        )
        client_connection = tpe.submit(
            peerToPeer_client.socket_clientConnection,
            server_host,
            server_port_re
        )

        server_connection.result()
        client_connection.result()

    print "socket connection started, now calling initialize"
    peerToPeerObj = peerToPeer_client.peer_intialize(cbl_db_client, False, server_host, server_port_re)
    # peerToPeer_android.accept_client(server)
    print " going to start ios peer to peer"
    peerToPeer_client.start(peerToPeerObj)
    print " going to read data fraom client by android"
    time.sleep(15)
    peerToPeer_client.stop(peerToPeerObj)
    count = db_obj_server.getCount(cbl_db_server)
    print "count for android is ", count
    count1 = db_obj_client.getCount(cbl_db_client)
    print "count for ios is ", count1
    # peerToPeer_android.read_data_fromClient(socket)
    """
