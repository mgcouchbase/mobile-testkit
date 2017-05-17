import logging

from keywords.utils import log_info


def verify_docs_present(expected_docs, actual_docs, server_type):
    missing_docs = []

    for actual_doc in actual_docs["rows"]:
        if "error" in actual_doc or ("value" in actual_doc and len(actual_doc["value"]) == 0):
            # Doc not found
            missing_docs.append(actual_doc)
        elif server_type == "listener" and actual_doc["value"]["rev"] != expected_docs[actual_doc["id"]]:
            # Found the doc but unexpected rev on LiteServ
            missing_docs.append(actual_doc)
        elif server_type == "sync_gateway" and actual_doc["_rev"] != expected_docs[actual_doc["_id"]]:
            # Found the doc but unexpected rev on LiteServ
            missing_docs.append(actual_doc)

    logging.debug("Missing Docs = {}".format(missing_docs))
    log_info("Num found docs: {}".format(len(actual_docs["rows"]) - len(missing_docs)))
    log_info("Num missing docs: {}".format(len(missing_docs)))

    if len(missing_docs) > 0:
        return False
    elif expected_docs != actual_docs:
        return False

    return True
