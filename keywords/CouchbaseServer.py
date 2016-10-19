import requests
import time
import json

from couchbase.bucket import Bucket
from couchbase.exceptions import ProtocolError
from couchbase.exceptions import TemporaryFailError
from couchbase.exceptions import NotFoundError

from constants import CLIENT_REQUEST_TIMEOUT
from utils import log_r
from utils import log_info
from utils import log_debug


def get_server_version(host):
    resp = requests.get("http://Administrator:password@{}:8091/pools".format(host))
    log_r(resp)
    resp.raise_for_status()
    resp_obj = resp.json()

    # Actual version is the following format 4.1.1-5914-enterprise
    running_server_version = resp_obj["implementationVersion"]
    running_server_version_parts = running_server_version.split("-")

    # Return version in the formatt 4.1.1-5487
    return "{}-{}".format(running_server_version_parts[0], running_server_version_parts[1])


def verify_server_version(host, expected_server_version):
    running_server_version = get_server_version(host)
    expected_server_version_parts = expected_server_version.split("-")

    # Check both version parts if expected version contains a build
    if len(expected_server_version_parts) == 2:
        # 4.1.1-5487
        log_info("Expected Server Version: {}".format(expected_server_version))
        log_info("Running Server Version: {}".format(running_server_version))
        assert running_server_version == expected_server_version, "Unexpected server version!! Expected: {} Actual: {}".format(expected_server_version, running_server_version)
    elif len(expected_server_version_parts) == 1:
        # 4.1.1
        running_server_version_parts = running_server_version.split("-")
        log_info("Expected Server Version: {}".format(expected_server_version))
        log_info("Running Server Version: {}".format(running_server_version_parts[0]))
        assert expected_server_version == running_server_version_parts[0], "Unexpected server version!! Expected: {} Actual: {}".format(expected_server_version, running_server_version_parts[0])
    else:
        raise ValueError("Unsupported version format")


class CouchbaseServer:
    """ Installs Couchbase Server on machine host"""

    def __init__(self):
        self._headers = {"Content-Type": "application/json"}
        self._auth = ("Administrator", "password")

    def delete_buckets(self, url):
        count = 0
        while count < 3:
            resp = requests.get("{}/pools/default/buckets".format(url), auth=self._auth, headers=self._headers)
            log_r(resp)
            resp.raise_for_status()

            obj = json.loads(resp.text)

            existing_bucket_names = []
            for entry in obj:
                existing_bucket_names.append(entry["name"])

            log_info("Existing buckets: {}".format(existing_bucket_names))
            log_info("Deleting buckets: {}".format(existing_bucket_names))

            # HACK around Couchbase Server issue where issuing a bucket delete via REST occasionally returns 500 error
            delete_num = 0
            # Delete existing buckets
            for bucket_name in existing_bucket_names:
                resp = requests.delete("{0}/pools/default/buckets/{1}".format(url, bucket_name), auth=self._auth, headers=self._headers)
                log_r(resp)
                if resp.status_code == 200:
                    delete_num += 1

            if delete_num == len(existing_bucket_names):
                break
            else:
                # A 500 error may have occured, query for buckets and try to delete them again
                time.sleep(5)
                count += 1

        # Check that max retries did not occur
        assert count != 3, "Could not delete bucket"

    def wait_for_ready_state(self, url):
        """
        Verify all server node is in are in a "healthy" state to avoid sync_gateway startup failures
        Work around for this - https://github.com/couchbase/sync_gateway/issues/1745
        """
        start = time.time()
        while True:

            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise Exception("Verify Docs Present: TIMEOUT")

            # Verfy the server is in a "healthy", not "warmup" state
            resp = requests.get("{}/pools/nodes".format(url), auth=self._auth, headers=self._headers)
            log_r(resp)

            resp_obj = resp.json()

            all_nodes_healthy = True
            for node in resp_obj["nodes"]:
                if node["status"] != "healthy":
                    all_nodes_healthy = False
                    log_info("Node: {} is still not healthy. Retrying ...".format(node))
                    time.sleep(1)

            if not all_nodes_healthy:
                continue

            log_info("All nodes are healthy")
            log_debug(resp_obj)
            # All nodes are heathy if it made it to here
            break

    def get_available_ram(self, url):
        """
        Call the Couchbase REST API to get the total memory available on the machine
        """
        resp = requests.get("{}/pools/default".format(url), auth=self._auth)
        resp.raise_for_status()
        resp_json = resp.json()

        # Workaround for https://github.com/couchbaselabs/mobile-testkit/issues/709
        # where some node report mem_total = 0. Loop over all the nodes and find highest val
        mem_total_highest = 0
        for node in resp_json["nodes"]:
            mem_total = node["systemStats"]["mem_total"]
            if mem_total > mem_total_highest:
                mem_total_highest = mem_total
        return mem_total_highest

    def create_buckets(self, url, bucket_names):
        """
        # Figure out what total ram available is
        # Divide by number of buckets
        """
        if len(bucket_names) == 0:
            return
        log_info("Creating buckets: {}".format(bucket_names))
        ram_multiplier = 0.80
        total_avail_ram_bytes = self.get_available_ram(url)
        total_avail_ram_mb = int(total_avail_ram_bytes / (1024 * 1024))
        n1ql_indexer_ram_mb = 512
        effective_avail_ram_mb = int(total_avail_ram_mb * ram_multiplier) - n1ql_indexer_ram_mb
        per_bucket_ram_mb = int(effective_avail_ram_mb / len(bucket_names))
        log_info("total_avail_ram_mb: {} effective_avail_ram_mb: {} effective_avail_ram_mb: {}".format(total_avail_ram_mb, effective_avail_ram_mb, effective_avail_ram_mb))
        for bucket_name in bucket_names:
            log_info("Create bucket {} with per_bucket_ram_mb {}".format(bucket_name, per_bucket_ram_mb))
            self.create_bucket(url, bucket_name, per_bucket_ram_mb)

    def create_bucket(self, url, name, ramQuotaMB=1024):
        """
        1. Create CBS bucket via REST
        2. Create client connection and poll until bucket is available
           Catch all connection exception and break when KeyNotFound error is thrown
        3. Verify all server nodes are in a 'healthy' state before proceeding

        Followed the docs below that suggested this approach.
        http://docs.couchbase.com/admin/admin/REST/rest-bucket-create.html
        """

        log_info("Creating bucket {} with RAM {}".format(name, ramQuotaMB))

        data = {
            "name": name,
            "ramQuotaMB": str(ramQuotaMB),
            "authType": "sasl",
            "proxyPort": "11211",
            "bucketType": "couchbase",
            "flushEnabled": "1"
        }

        resp = requests.post("{}/pools/default/buckets".format(url), auth=self._auth, data=data)
        log_info("{0} {1}\nHEADERS = {2}\nBODY = {3}".format(
            resp.request.method,
            resp.request.url,
            resp.request.headers,
            resp.request.body))

        log_info("{}".format(resp.text))

        resp.raise_for_status()

        # Create client an retry until KeyNotFound error is thrown
        client_host = url.replace("http://", "")
        client_host = client_host.replace(":8091", "")
        log_info(client_host)

        start = time.time()
        while True:

            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise Exception("Verify Docs Present: TIMEOUT")
            try:
                bucket = Bucket("couchbase://{}/{}".format(client_host, name))
                bucket.get('foo')
            except ProtocolError as pe:
                log_info("Client Connection failed: {} Retrying ...".format(pe))
                time.sleep(1)
                continue
            except TemporaryFailError as te:
                log_info("Failure from server: {} Retrying ...".format(te))
                time.sleep(1)
                continue
            except NotFoundError as nfe:
                log_info("Key not found error: {} Bucket is ready!".format(nfe))
                break

        self.wait_for_ready_state(url)

        return name

    def delete_couchbase_server_cached_rev_bodies(self, url, bucket):
        """
        Deletes docs that follow the below format
        _sync:rev:att_doc:34:1-e7fa9a5e6bb25f7a40f36297247ca93e
        """
        client_host = url.replace("http://", "")
        client_host = client_host.replace(":8091", "")

        b = Bucket("couchbase://{}/{}".format(client_host, bucket))

        cached_rev_doc_ids = []
        b.n1ql_query("CREATE PRIMARY INDEX ON `{}`".format(bucket)).execute()
        for row in b.n1ql_query("SELECT meta(`{}`) FROM `{}`".format(bucket, bucket)):
            if row["$1"]["id"].startswith("_sync:rev"):
                cached_rev_doc_ids.append(row["$1"]["id"])

        log_info("Found temp rev docs: {}".format(cached_rev_doc_ids))
        for doc_id in cached_rev_doc_ids:
            log_debug("Removing: {}".format(doc_id))
            b.remove(doc_id)

    def get_server_docs_with_prefix(self, url, bucket, prefix):
        """
        Returns server doc ids matching a prefix (ex. '_sync:rev:')
        """
        client_host = url.replace("http://", "")
        client_host = client_host.replace(":8091", "")

        b = Bucket("couchbase://{}/{}".format(client_host, bucket))

        found_ids = []
        b.n1ql_query("CREATE PRIMARY INDEX ON `{}`".format(bucket)).execute()
        for row in b.n1ql_query("SELECT meta(`{}`) FROM `{}`".format(bucket, bucket)):
            if row["$1"]["id"].startswith(prefix):
                found_ids.append(row["$1"]["id"])

        return found_ids
