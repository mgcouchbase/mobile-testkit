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
@pytest.mark.parametrize("num_docs_per_db, seeded_client_db, client_replication_type, continuous, attachments_generator, server_replication_type", [
    # (100, False, "push", True, None, False),  # Continuous push - no seed, no attachments
    # (100, False, "bidi", True, None, False),  # Continuous push pull - no seed, no attachments
    # (100, True, "push", True, None, False),  # Continuous push - seed, no attachments
    # (100, False, "pull", True, None, False),  # Continuous pull - no seed, no attachments
    # (100, True, "pull", True, None, False),  # Continuous pull - seed, no attachments
    # (100, False, "bidi", True, None, "bidi"),  # Continuous push pull - no seed, no attachments
    (100, False, "bidi", False, None, "bidi"),  # One shot push pull - no seed, no attachments
    # (100, False, "pull", False, None, False),  # One shot pull - no seed, no attachments
    # (100, True, "pull", False, None, False),  # One shot pull - seed, no attachments
    # (100, False, "push", False, None, False),  # One shot push - no seed
    # (100, True, "push", False, None, False),  # One shot push - seed
    # (100, False, "push", False, attachment.generate_png_100_100, False),  # One shot push, no seed, attachments
    # (100, False, "pull", False, attachment.generate_png_100_100, False),  # One shot pull, no seed, attachments
    # (100, False, "push", True, attachment.generate_png_100_100, False),  # Continuous push, no seed, attachments
    # (100, False, "pull", True, attachment.generate_png_100_100, False),  # Continuous pull, no seed, attachments
])
def test_replication(setup_client_test, num_docs_per_db, seeded_client_db, client_replication_type, continuous, attachments_generator, server_replication_type):
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
    sg_bucket_list = setup_client_test["sg_bucket_list"]
    client = MobileRestClient()

    log_info("Creating databases")

    if server_platform == "sync_gateway":
        ls_db1 = sg_bucket_list[0]
    else:
        ls_db1 = client.create_database(url=server_url, name="ls_db1")

    ls_db2 = client.create_database(url=client_url, name="ls_db2")
    blip_url_one = server_url.replace("http", "blip")
    blip_url_two = client_url.replace("http", "blip")

    log_info("server_url: {}".format(server_url))
    log_info("client_url: {}".format(client_url))

    attachments = False

    if attachments_generator:
        log_info("Running test_peer_2_peer_sanity_pull with attachment {}".format(attachments_generator))
        attachments = True

    ls_db2_docs_seed = None
    if seeded_client_db:
        bulk_docs = create_docs("test_ls_db2_seed", num_docs_per_db)
        ls_db2_docs_seed = client.add_bulk_docs(url=client_url, db=ls_db2, docs=bulk_docs)
        assert len(ls_db2_docs_seed) == num_docs_per_db

    ls_db1_docs = client.add_docs(url=server_url, db=ls_db1, number=num_docs_per_db, id_prefix="test_ls_db1", attachments_generator=attachments_generator)
    assert len(ls_db1_docs) == num_docs_per_db

    ls_db2_docs = client.add_docs(url=client_url, db=ls_db2, number=num_docs_per_db, id_prefix="test_ls_db2", attachments_generator=attachments_generator)
    assert len(ls_db2_docs) == num_docs_per_db

    # Start Client replication
    client_from_db = None
    client_from_url = None
    client_to_db = None
    client_to_url = None
    client_bidi = None

    if client_replication_type == "push":
        client_from_db = ls_db2
        client_to_url = blip_url_one
        client_to_db = ls_db1
    elif client_replication_type == "pull" or client_replication_type == "bidi":
        client_from_db = ls_db1
        client_from_url = blip_url_one
        client_to_db = ls_db2

    if client_replication_type == "bidi":
        client_bidi = True

    # Setup replication from from_db to to_db
    repl_one = client.start_replication(
        url=client_url,
        continuous=continuous,
        from_db=client_from_db, from_url=client_from_url,
        to_url=client_to_url, to_db=client_to_db,
        bidi=client_bidi
    )

    # Start server replication
    if server_replication_type and server_platform != "sync_gateway":
        server_from_db = None
        server_from_url = None
        server_to_db = None
        server_to_url = None
        server_bidi = None

        if server_replication_type == "push":
            server_from_db = ls_db1
            server_to_url = blip_url_two
            server_to_db = ls_db2
        elif server_replication_type == "pull" or server_replication_type == "bidi":
            server_from_db = ls_db2
            server_from_url = blip_url_two
            server_to_db = ls_db1

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

        if server_replication_type:
            client.wait_for_replication_status_idle(url=server_url, replication_id=repl_two)
            server_url_replications = client.get_replications(server_url)
            assert len(server_url_replications) == 1

    # Set the right expected docs
    if client_replication_type == "pull":
        expected_docs_server = ls_db1_docs
        expected_docs_client = client.merge(ls_db1_docs, ls_db2_docs)
    elif client_replication_type == "push":
        expected_docs_server = client.merge(ls_db1_docs, ls_db2_docs)
        expected_docs_client = ls_db2_docs
    elif client_replication_type == "bidi":
        expected_docs_server = client.merge(ls_db1_docs, ls_db2_docs)
        expected_docs_client = client.merge(ls_db1_docs, ls_db2_docs)

    if server_replication_type and server_platform != "sync_gateway":
        if server_replication_type == "pull":
            expected_docs_server = client.merge(expected_docs_server, ls_db2_docs)
        elif server_replication_type == "push":
            expected_docs_client = client.merge(expected_docs_client, ls_db2_docs)

    if seeded_client_db:
        expected_docs_client.extend(ls_db2_docs_seed)
        if client_replication_type == "push":
            expected_docs_server.extend(ls_db2_docs_seed)

    client.verify_docs_present(url=server_url, db=ls_db1, expected_docs=expected_docs_server, attachments=attachments)
    client.verify_docs_present(url=client_url, db=ls_db2, expected_docs=expected_docs_client, attachments=attachments)

    # LiteCoreServ does not have a Changes feed REST end point
    if server_platform == "sync_gateway":
        client.verify_docs_in_changes(url=server_url, db=ls_db1, expected_docs=expected_docs_server)

    # Stop replications
    if continuous:
        client.stop_replication(
            url=client_url,
            continuous=continuous,
            from_db=client_from_db, from_url=client_from_url,
            to_url=client_to_url, to_db=client_to_db
        )

        if server_replication_type:
            client.stop_replication(
                url=server_url,
                continuous=continuous,
                from_db=server_from_db, from_url=server_from_url,
                to_url=server_to_url, to_db=server_to_db
            )
