"""TEST_FIXTURE public-contract fingerprint reference; snapshot-only, not executed."""

import hashlib
import json


def fixture_fingerprint(public_contract_fields):
    payload = json.dumps(public_contract_fields, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
