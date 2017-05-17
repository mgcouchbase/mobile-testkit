import pytest
import time

from requests import Session

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.document import create_docs
from keywords.verification import verify_docs_present
from keywords.exceptions import TimeoutException
from keywords.constants import CLIENT_REQUEST_TIMEOUT


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.session
@pytest.mark.parametrize("num_docs_per_db, seeded_client_db, replication_type, continuous", [
    (100, False, "push", True),
])
def test_replication(setup_client_test, num_docs_per_db, seeded_client_db, replication_type, continuous):
    ls_url_one = setup_client_test["ls_url_one"]
    ls_url_two = setup_client_test["ls_url_two"]
    server_platform = setup_client_test["server_platform"]

    num_docs_per_db = 100
    client = MobileRestClient()

    log_info("Creating databases")

    if server_platform == "sync_gateway":
        ls_db1 = "db"
        blip_url_one = ls_url_one.replace("http", "blip")
    else:
        ls_db1 = client.create_database(url=ls_url_one, name="ls_db1")

    ls_db2 = client.create_database(url=ls_url_two, name="ls_db2")

    log_info("ls_url_one: {}".format(ls_url_one))
    log_info("ls_url_two: {}".format(ls_url_two))

    if seeded_client_db:
        bulk_docs = create_docs("test_ls_db2_seed", num_docs_per_db)
        ls_db2_docs_seed = client.add_bulk_docs(url=ls_url_two, db=ls_db2, docs=bulk_docs)
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

    # Setup replication from from_db to to_db
    repl_one = client.start_replication(
        url=ls_url_two,
        continuous=continuous,
        from_db=from_db, from_url=from_url,
        to_url=to_url, to_db=to_db
    )

    client.wait_for_replication_status_idle(url=ls_url_two, replication_id=repl_one)

    ls_url_two_replications = client.get_replications(ls_url_two)
    assert len(ls_url_two_replications) == 1

    ls_db1_docs = client.add_docs(url=ls_url_one, db=ls_db1, number=num_docs_per_db, id_prefix="test_ls_db1")
    assert len(ls_db1_docs) == num_docs_per_db

    ls_db2_docs = client.add_docs(url=ls_url_two, db=ls_db2, number=num_docs_per_db, id_prefix="test_ls_db2")
    assert len(ls_db2_docs) == num_docs_per_db

    # all_docs = client.merge(ls_db1_docs, ls_db2_docs)
    all_docs = ls_db2_docs
    assert len(all_docs) == 100

    # client.verify_docs_present(url=ls_url_one, db=ls_db1, expected_docs=all_docs)
    sg_expected_doc_map = {all_doc["id"]: all_doc["rev"] for all_doc in all_docs}

    session = Session()
    resp = session.get("{}/{}/_all_docs".format(ls_url_one, ls_db1))
    resp.raise_for_status()
    resp_obj = resp.json()

    start = time.time()
    while True:
        if time.time() - start > CLIENT_REQUEST_TIMEOUT:
            raise TimeoutException("Verify Docs Present: TIMEOUT")

        docs_present = verify_docs_present(sg_expected_doc_map, resp_obj, "sync_gateway")
        if docs_present:
            break
        else:
            log_info("Retrying to verify all docs are present...")

    # client.verify_docs_present(url=ls_url_two, db=ls_db2, expected_docs=all_docs)

    # client.verify_docs_in_changes(url=ls_url_one, db=ls_db1, expected_docs=all_docs)
    # client.verify_docs_in_changes(url=ls_url_two, db=ls_db2, expected_docs=all_docs)

    client.stop_replication(
        url=ls_url_two,
        continuous=continuous,
        from_db=from_db, from_url=from_url,
        to_url=to_url, to_db=to_db
    )
