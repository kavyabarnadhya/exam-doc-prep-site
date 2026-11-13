"""Sign and publish a prepared exam-rules file (run by .github/workflows/sign-rules.yml).

    python tools/sign_rules.py <prepared rules.json>

Reads the signing key from the RULES_SIGNING_KEY environment variable (a
GitHub Actions secret; base64 Ed25519 seed). Never prints it. Refuses anything
the app would refuse, anything not newer than the published file, and any key
that does not match the public key built into the app. Writes the exact bytes
to rules/v1/rules.json and the base64 signature to rules/v1/rules.json.sig.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

# Same public key as the app (lib/rules/rules_config.dart kRulesPublicKey).
APP_PUBLIC_KEY = "HxVeQjSIpawpHgwTCFDZBWaJx3GEa1dHAYW+kMJ2dVI="  # pragma: allowlist secret
SCHEMA = 1
MAX_BYTES = 1024 * 1024
OUT = Path("rules/v1")


def validate(data: bytes, live_version: int) -> dict:
    """The app's own checks (RulesBundle.parse) plus 'newer than live'."""
    if len(data) > MAX_BYTES:
        raise ValueError("file too large")
    j = json.loads(data.decode("utf-8"))
    if not isinstance(j, dict) or j.get("schema") != SCHEMA:
        raise ValueError("unknown schema")
    v = j.get("version")
    if not isinstance(v, int) or isinstance(v, bool) or v < 1:
        raise ValueError("bad version")
    if v <= live_version:
        raise ValueError(f"version {v} is not newer than the published {live_version}")
    dt.date.fromisoformat(str(j.get("published", "")))
    rules = j.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("no rules")
    ids = [r.get("id") for r in rules if isinstance(r, dict)]
    if len(ids) != len(rules) or len(set(ids)) != len(ids):
        raise ValueError("missing or duplicate rule id")
    for r in rules:
        if r.get("status") not in ("historic", "current", "unconfirmed"):
            raise ValueError(f"{r['id']}: bad status")
        if not str(r.get("source_url", "")).startswith("https://"):
            raise ValueError(f"{r['id']}: source must be https")
    return j


def sign(data: bytes, seed_b64: str, public_b64: str = APP_PUBLIC_KEY) -> bytes:
    key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(seed_b64.strip()))
    sig = key.sign(data)
    Ed25519PublicKey.from_public_bytes(base64.b64decode(public_b64)).verify(sig, data)  # wrong key fails here
    return sig


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 64
    seed = os.environ.get("RULES_SIGNING_KEY", "")
    if not seed:
        print("RULES_SIGNING_KEY secret is not set")
        return 1
    data = Path(argv[0]).read_bytes()
    live = json.loads((OUT / "rules.json").read_text(encoding="utf-8"))["version"]
    j = validate(data, live)
    try:
        sig = sign(data, seed)
    except Exception:  # noqa: BLE001 - never echo key material
        print("signing failed: the secret does not match the app's public key")
        return 1
    (OUT / "rules.json").write_bytes(data)
    (OUT / "rules.json.sig").write_text(base64.b64encode(sig).decode() + "\n", encoding="ascii")
    print(f"signed rules version {j['version']} ({len(j['rules'])} rules)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
