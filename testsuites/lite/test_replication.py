import pytest

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.document import create_docs
from keywords import attachment


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.session
@pytest.mark.parametrize("num_docs_per_db, seeded_client_db, client_replication_type, continuous, attachments_generator, server_replication_type, client_dbs", [
    # (100, False, "push", True, None, False, 1),  # Continuous push - no seed, no attachments
    # (100, False, "bidi", True, None, False, 1),  # Continuous push pull - no seed, no attachments
    # (100, True, "push", True, None, False, 1),  # Continuous push - seed, no attachments
    # (100, False, "pull", True, None, False, 1),  # Continuous pull - no seed, no attachments
    # (100, True, "pull", True, None, False, 1),  # Continuous pull - seed, no attachments
    # (100, False, "bidi", True, None, "bidi", 1),  # Continuous push pull - no seed, no attachments
    (100, False, "bidi", False, None, "False", 2),  # One shot push pull - no seed, no attachments
    # (100, False, "pull", False, None, False, 1),  # One shot pull - no seed, no attachments
    # (100, True, "pull", False, None, False, 1),  # One shot pull - seed, no attachments
    # (100, False, "push", False, None, False, 1),  # One shot push - no seed
    # (100, True, "push", False, None, False, 1),  # One shot push - seed
    # (100, False, "push", False, attachment.generate_png_100_100, False, 1),  # One shot push, no seed, attachments
    # (100, False, "pull", False, attachment.generate_png_100_100, False, 1),  # One shot pull, no seed, attachments
    # (100, False, "push", True, attachment.generate_png_100_100, False, 1),  # Continuous push, no seed, attachments
    # (100, False, "pull", True, attachment.generate_png_100_100, False, 1),  # Continuous pull, no seed, attachments
])
def test_replication(setup_client_test, num_docs_per_db, seeded_client_db, client_replication_type, continuous, attachments_generator, server_replication_type, client_dbs):
    """ Replication test
    Server: sync_gateway/macosx, net-mono, net-msft, ios, android
    num_docs_per_db - Number of docs to add to the DB
    seeded_client_db - True/False - Whether to seed the DB with docs beforehand
    replication_type - push/pull/bidi(Bidirectional)
    continuous - True/False(One shot)
    attachments_generator - attachment_generator/None - Add attachements to docs
    server_replication - False/push/pull/bidi - Start replication on the server litecore
    """
    server_url = setup_client_test["server_url"]
    client_url = setup_client_test["client_url"]
    server_platform = setup_client_test["server_platform"]
    client = MobileRestClient()
    client_db_list = setup_client_test["client_db_list"]
    server_db_list = setup_client_test["server_db_list"]

    server_db = server_db_list[0]

    blip_url_one = server_url.replace("http", "blip")
    blip_url_two = client_url.replace("http", "blip")

    log_info("server_url: {}".format(server_url))
    log_info("client_url: {}".format(client_url))

    attachments = False

    if attachments_generator:
        log_info("Running test_peer_2_peer_sanity_pull with attachment {}".format(attachments_generator))
        attachments = True

    server_db_docs = client.add_docs(url=server_url, db=server_db, number=num_docs_per_db, id_prefix="test_server_db", attachments_generator=attachments_generator)
    assert len(server_db_docs) == num_docs_per_db

    expected_docs_server = []
    expected_docs_client = []

    i = 0
    for client_db in client_db_list:
        if i == client_dbs:
            break

        client_db_docs_seed = None
        if seeded_client_db:
            bulk_docs = create_docs("test_client_db_seed", num_docs_per_db)
            client_db_docs_seed = client.add_bulk_docs(url=client_url, db=client_db, docs=bulk_docs)
            assert len(client_db_docs_seed) == num_docs_per_db

        client_db_docs = client.add_docs(url=client_url, db=client_db, number=num_docs_per_db, id_prefix="test_{}".format(client_db), attachments_generator=attachments_generator)
        assert len(client_db_docs) == num_docs_per_db

        # Start Client replication
        client_from_db = None
        client_from_url = None
        client_to_db = None
        client_to_url = None
        client_bidi = None

        if client_replication_type == "push" or client_replication_type == "bidi":
            client_from_db = client_db
            client_to_url = blip_url_one
            client_to_db = server_db
        elif client_replication_type == "pull" or client_replication_type == "bidi":
            client_from_db = server_db
            client_from_url = blip_url_one
            client_to_db = client_db

        if client_replication_type == "bidi":
            client_bidi = True

        # Setup replication from from_db to to_db
        log_info("Starting {} replication from {}/{} to {}/{}".format(client_replication_type, client_from_url, client_from_db, client_to_url, client_to_db))
        repl_one = client.start_replication(
            url=client_url,
            continuous=continuous,
            from_db=client_from_db, from_url=client_from_url,
            to_url=client_to_url, to_db=client_to_db,
            bidi=client_bidi
        )

        i += 1

        # Start server replication
        if server_replication_type and server_platform != "sync_gateway":
            server_from_db = None
            server_from_url = None
            server_to_db = None
            server_to_url = None
            server_bidi = None

            if server_replication_type == "push":
                server_from_db = server_db
                server_to_url = blip_url_two
                server_to_db = client_db
            elif server_replication_type == "pull" or server_replication_type == "bidi":
                server_from_db = client_db
                server_from_url = blip_url_two
                server_to_db = server_db

            if server_replication_type == "bidi":
                server_bidi = True

            # Setup replication from from_db to to_db
            repl_two = client.start_replication(
                url=server_url,
                continuous=continuous,
                from_db=server_from_db, from_url=server_from_url,
                to_url=server_to_url, to_db=server_to_db,
                bidi=server_bidi
            )

            # Wait for replications to go idle
            if continuous:
                client.wait_for_replication_status_idle(url=client_url, replication_id=repl_one)
                client_url_replications = client.get_replications(client_url)
                assert len(client_url_replications) == 1

        # Set the right expected docs
        if client_replication_type == "pull":
            expected_docs_server = server_db_docs
            expected_docs_client = server_db_docs + client_db_docs
        elif client_replication_type == "push":
            expected_docs_server = server_db_docs + client_db_docs
            expected_docs_client = client_db_docs
        elif client_replication_type == "bidi":
            expected_docs_server = server_db_docs + client_db_docs
            expected_docs_client = server_db_docs + client_db_docs

        if seeded_client_db:
            expected_docs_client.extend(client_db_docs_seed)
            if client_replication_type == "push":
                expected_docs_server.extend(client_db_docs_seed)

    client.verify_docs_present(url=client_url, db=client_db, expected_docs=expected_docs_client, attachments=attachments)

    # LiteCoreServ does not have a Changes feed REST end point
    if server_platform == "sync_gateway":
        client.verify_docs_in_changes(url=server_url, db=server_db, expected_docs=expected_docs_server)

    # Stop replications
    if continuous:
        client.stop_replication(
            url=client_url,
            continuous=continuous,
            from_db=client_from_db, from_url=client_from_url,
            to_url=client_to_url, to_db=client_to_db
        )

    # Wait for replications to go idle
    if continuous:
        if server_replication_type:
            client.wait_for_replication_status_idle(url=server_url, replication_id=repl_two)
            server_url_replications = client.get_replications(server_url)
            assert len(server_url_replications) == 1

    if server_replication_type and server_platform != "sync_gateway":
        if server_replication_type == "pull":
            expected_docs_server += client_db_docs
        elif server_replication_type == "push":
            expected_docs_client += client_db_docs

    client.verify_docs_present(url=server_url, db=server_db, expected_docs=expected_docs_server, attachments=attachments)

    # Stop replications
    if continuous:
        if server_replication_type:
            client.stop_replication(
                url=server_url,
                continuous=continuous,
                from_db=server_from_db, from_url=server_from_url,
                to_url=server_to_url, to_db=server_to_db
            )
