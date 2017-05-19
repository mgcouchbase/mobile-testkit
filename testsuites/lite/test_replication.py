import pytest

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.document import create_docs


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.session
@pytest.mark.parametrize("num_docs_per_db, seeded_client_db, replication_type, continuous", [
    # (100, False, "push", True),  # Continuous push - no seed
    (100, True, "push", True),  # Continuous push - with seed
    # (100, False, "pull", True),  # Continuous pull - no seed
    # (100, True, "pull", True),  # Continuous pull - with seed
    # (100, False, "pull", False),  # One shot pull - no seed
    # (100, True, "pull", False),  # One shot pull - with seed
    (100, False, "push", False),  # One shot push - no seed
    # (100, True, "push", False),  # One shot push - with seed
])
def test_replication(setup_client_test, num_docs_per_db, seeded_client_db, replication_type, continuous):
    server_url = setup_client_test["server_url"]
    client_url = setup_client_test["client_url"]
    server_platform = setup_client_test["server_platform"]
    client = MobileRestClient()

    log_info("Creating databases")

    if server_platform == "sync_gateway":
        ls_db1 = "db"
        blip_url_one = server_url.replace("http", "blip")
    else:
        ls_db1 = client.create_database(url=server_url, name="ls_db1")

    ls_db2 = client.create_database(url=client_url, name="ls_db2")

    log_info("server_url: {}".format(server_url))
    log_info("client_url: {}".format(client_url))

    ls_db2_docs_seed = None
    if seeded_client_db:
        bulk_docs = create_docs("test_ls_db2_seed", num_docs_per_db)
        ls_db2_docs_seed = client.add_bulk_docs(url=client_url, db=ls_db2, docs=bulk_docs)
        assert len(ls_db2_docs_seed) == num_docs_per_db

    from_db = None
    from_url = None
    to_db = None
    to_url = None

    if replication_type == "push":
        from_db = ls_db2
        to_url = blip_url_one
        to_db = ls_db1
    elif replication_type == "pull":
        from_db = ls_db1
        from_url = blip_url_one
        to_db = ls_db2

    ls_db1_docs = client.add_docs(url=server_url, db=ls_db1, number=num_docs_per_db, id_prefix="test_ls_db1")
    assert len(ls_db1_docs) == num_docs_per_db

    ls_db2_docs = client.add_docs(url=client_url, db=ls_db2, number=num_docs_per_db, id_prefix="test_ls_db2")
    assert len(ls_db2_docs) == num_docs_per_db

    # Setup replication from from_db to to_db
    repl_one = client.start_replication(
        url=client_url,
        continuous=continuous,
        from_db=from_db, from_url=from_url,
        to_url=to_url, to_db=to_db
    )

    if continuous:
        client.wait_for_replication_status_idle(url=client_url, replication_id=repl_one)
        client_url_replications = client.get_replications(client_url)
        assert len(client_url_replications) == 1

    if replication_type == "pull":
        expected_docs_sg = ls_db1_docs
        expected_docs_ls = client.merge(ls_db1_docs, ls_db2_docs)
    elif replication_type == "push":
        expected_docs_sg = client.merge(ls_db1_docs, ls_db1_docs)
        expected_docs_ls = ls_db2_docs

    if seeded_client_db:
        expected_docs_ls.extend(ls_db2_docs_seed)
        if replication_type == "push":
            expected_docs_sg.extend(ls_db2_docs_seed)

    client.verify_docs_present(url=server_url, db=ls_db1, expected_docs=expected_docs_sg)
    client.verify_docs_present(url=client_url, db=ls_db2, expected_docs=expected_docs_ls)

    client.verify_docs_in_changes(url=server_url, db=ls_db1, expected_docs=expected_docs_sg)
    # LiteCoreServ does not have a Changes feed REST end point

    if continuous:
        client.stop_replication(
            url=client_url,
            continuous=continuous,
            from_db=from_db, from_url=from_url,
            to_url=to_url, to_db=to_db
        )
