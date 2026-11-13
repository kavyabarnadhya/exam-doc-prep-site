import base64
import json
import sys
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sign_rules as s  # noqa: E402


def rules(version=5, **over):
    j = {"schema": 1, "version": version, "published": "2026-11-14",
         "rules": [{"id": "a", "status": "current", "source_url": "https://x.gov.in/n.pdf"}]}
    j.update(over)
    return json.dumps(j).encode()


class Validate(unittest.TestCase):
    def test_good(self):
        self.assertEqual(s.validate(rules(), 4)["version"], 5)

    def test_not_newer(self):
        with self.assertRaises(ValueError):
            s.validate(rules(4), 4)

    def test_bad_schema_status_url_dupes(self):
        for bad in (rules(schema=2), rules(rules=[]),
                    rules(rules=[{"id": "a", "status": "x", "source_url": "https://a"}]),
                    rules(rules=[{"id": "a", "status": "current", "source_url": "http://a"}]),
                    rules(rules=[{"id": "a", "status": "current", "source_url": "https://a"}] * 2)):
            with self.assertRaises(ValueError):
                s.validate(bad, 4)

    def test_too_large(self):
        with self.assertRaises(ValueError):
            s.validate(b" " * (s.MAX_BYTES + 1), 4)


class Sign(unittest.TestCase):
    def setUp(self):
        k = Ed25519PrivateKey.generate()
        self.seed = base64.b64encode(k.private_bytes(
            serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
            serialization.NoEncryption())).decode()
        self.pub = base64.b64encode(k.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()

    def test_signs_with_matching_key(self):
        self.assertEqual(len(s.sign(b"data", self.seed, self.pub)), 64)

    def test_refuses_a_key_that_does_not_match_the_app(self):
        with self.assertRaises(Exception):
            s.sign(b"data", self.seed)  # app's public key, different private key


if __name__ == "__main__":
    unittest.main()
