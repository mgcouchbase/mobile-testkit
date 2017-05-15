import pytest

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.session
def test_replication(setup_client_test):
    ls_url_one = setup_client_test["ls_url_one"]
    ls_url_two = setup_client_test["ls_url_two"]
    sg_mode = setup_client_test["sg_mode"]

    num_docs_per_db = 100
    client = MobileRestClient()

    log_info("Creating databases")

    if sg_mode:
        ls_db1 = "db"
    else:
        ls_db1 = client.create_database(url=ls_url_one, name="ls_db1")
        blip_url_one = ls_url_one.replace("http", "blip")

    ls_db2 = client.create_database(url=ls_url_two, name="ls_db2")
    blip_url_one = ls_url_one.replace("http", "blip")
    blip_url_two = ls_url_two.replace("http", "blip")

    log_info("ls_url_one: {}".format(ls_url_one))
    log_info("ls_url_two: {}".format(ls_url_two))

    # Setup continuous push / pull replication from client 2 ls_db2 to client 1 ls_db1
    repl_three = client.start_replication(
        url=ls_url_two,
        continuous=True,
        from_db=ls_db2,
        to_url=blip_url_one, to_db=ls_db1
    )

    repl_four = client.start_replication(
        url=ls_url_two,
        continuous=True,
        from_url=blip_url_one, from_db=ls_db1,
        to_db=ls_db2
    )

    client.wait_for_replication_status_idle(url=ls_url_two, replication_id=repl_three)
    client.wait_for_replication_status_idle(url=ls_url_two, replication_id=repl_four)

    ls_url_two_replications = client.get_replications(ls_url_two)
    assert len(ls_url_two_replications) == 2

    ls_db1_docs = client.add_docs(url=ls_url_one, db=ls_db1, number=num_docs_per_db, id_prefix="test_ls_db1")
    assert len(ls_db1_docs) == num_docs_per_db

    ls_db2_docs = client.add_docs(url=ls_url_two, db=ls_db2, number=num_docs_per_db, id_prefix="test_ls_db2")
    assert len(ls_db2_docs) == num_docs_per_db

    all_docs = client.merge(ls_db1_docs, ls_db2_docs)
    assert len(all_docs) == 200

    client.verify_docs_present(url=ls_url_one, db=ls_db1, expected_docs=all_docs)
    client.verify_docs_present(url=ls_url_two, db=ls_db2, expected_docs=all_docs)

    client.verify_docs_in_changes(url=ls_url_one, db=ls_db1, expected_docs=all_docs)
    client.verify_docs_in_changes(url=ls_url_two, db=ls_db2, expected_docs=all_docs)
