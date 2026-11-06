# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: Ed25519 evidence-pack signing (fail-closed).

Every negative case must raise SignatureError â€” never a silent
pass, never a partial trust verdict.
"""
import base64
import json

import pytest

pytest.importorskip("cryptography", reason="cryptography not installed")

from genesis_rt import signing  # noqa: E402
from genesis_rt.signing import (PURPOSE_EVIDENCE_PACK, SignatureError,  # noqa: E402
                                generate_keypair, sign_manifest,
                                verify_envelope)

MANIFEST = b'{"pack":"demo","files":{"a":1}}'
SCOPE = {"pack": "demo"}


@pytest.fixture()
def keys():
    return generate_keypair()


def _sign(keys, manifest=MANIFEST, purpose=PURPOSE_EVIDENCE_PACK,
          scope=SCOPE, **kw):
    return sign_manifest(manifest_bytes=manifest, purpose=purpose,
                         signer_id="alice@example.com", key_id="k1",
                         private_pem=keys["private_pem"], scope=scope, **kw)


def test_round_trip_verifies(keys):
    env = _sign(keys)
    body = verify_envelope(envelope=env, manifest_bytes=MANIFEST,
                           trust={"k1": keys["public_pem"]},
                           purpose=PURPOSE_EVIDENCE_PACK, scope=SCOPE)
    assert body["signer_id"] == "alice@example.com"
    assert body["key_id"] == "k1"
    assert "signature" not in body


def test_tampered_manifest_bytes_rejected(keys):
    env = _sign(keys)
    with pytest.raises(SignatureError, match="differ from signed digest"):
        verify_envelope(envelope=env, manifest_bytes=MANIFEST + b" ",
                        trust={"k1": keys["public_pem"]},
                        purpose=PURPOSE_EVIDENCE_PACK, scope=SCOPE)


def test_tampered_envelope_field_rejected(keys):
    env = _sign(keys)
    env["signer_id"] = "mallory@example.com"
    with pytest.raises(SignatureError, match="does not verify"):
        verify_envelope(envelope=env, manifest_bytes=MANIFEST,
                        trust={"k1": keys["public_pem"]},
                        purpose=PURPOSE_EVIDENCE_PACK, scope=SCOPE)


def test_flipped_signature_bit_rejected(keys):
    env = _sign(keys)
    raw = bytearray(base64.b64decode(env["signature"]))
    raw[0] ^= 1
    env["signature"] = base64.b64encode(bytes(raw)).decode("ascii")
    with pytest.raises(SignatureError, match="does not verify"):
        verify_envelope(envelope=env, manifest_bytes=MANIFEST,
                        trust={"k1": keys["public_pem"]},
                        purpose=PURPOSE_EVIDENCE_PACK, scope=SCOPE)


def test_wrong_purpose_rejected(keys):
    env = _sign(keys, purpose=PURPOSE_EVIDENCE_PACK)
    with pytest.raises(SignatureError, match="purpose mismatch"):
        verify_envelope(envelope=env, manifest_bytes=MANIFEST,
                        trust={"k1": keys["public_pem"]},
                        purpose="genesis-proofos-plan/1", scope=SCOPE)


def test_cross_pack_replay_rejected(keys):
    env = _sign(keys, scope={"pack": "pack-a"})
    with pytest.raises(SignatureError, match="scope mismatch"):
        verify_envelope(envelope=env, manifest_bytes=MANIFEST,
                        trust={"k1": keys["public_pem"]},
                        purpose=PURPOSE_EVIDENCE_PACK,
                        scope={"pack": "pack-b"})


def test_unknown_key_id_rejected(keys):
    env = _sign(keys)
    with pytest.raises(SignatureError, match="not trusted"):
        verify_envelope(envelope=env, manifest_bytes=MANIFEST,
                        trust={"other": keys["public_pem"]},
                        purpose=PURPOSE_EVIDENCE_PACK, scope=SCOPE)


def test_wrong_key_for_key_id_rejected(keys):
    env = _sign(keys)
    other = generate_keypair()
    with pytest.raises(SignatureError, match="does not verify"):
        verify_envelope(envelope=env, manifest_bytes=MANIFEST,
                        trust={"k1": other["public_pem"]},
                        purpose=PURPOSE_EVIDENCE_PACK, scope=SCOPE)


def test_rotation_old_key_removed_rejected_new_accepted(keys):
    old = generate_keypair()
    new = generate_keypair()
    env = sign_manifest(
        manifest_bytes=MANIFEST, purpose=PURPOSE_EVIDENCE_PACK,
        signer_id="alice@example.com", key_id="k2",
        private_pem=new["private_pem"], scope=SCOPE, supersedes="k1")
    assert env["supersedes"] == "k1"
    # Trust store migrated to k2 only: new signature verifies.
    verify_envelope(envelope=env, manifest_bytes=MANIFEST,
                    trust={"k2": new["public_pem"]},
                    purpose=PURPOSE_EVIDENCE_PACK, scope=SCOPE)
    # Old signatures no longer verify once k1 is dropped.
    stale = sign_manifest(
        manifest_bytes=MANIFEST, purpose=PURPOSE_EVIDENCE_PACK,
        signer_id="alice@example.com", key_id="k1",
        private_pem=old["private_pem"], scope=SCOPE)
    with pytest.raises(SignatureError, match="not trusted"):
        verify_envelope(envelope=stale, manifest_bytes=MANIFEST,
                        trust={"k2": new["public_pem"]},
                        purpose=PURPOSE_EVIDENCE_PACK, scope=SCOPE)


def test_malformed_inputs_rejected(keys):
    good = _sign(keys)
    trust = {"k1": keys["public_pem"]}
    for bad in (None, [], "x", {"sig_version": 99},
                {"sig_version": 1}):
        with pytest.raises(SignatureError):
            verify_envelope(envelope=bad, manifest_bytes=MANIFEST,
                            trust=trust, purpose=PURPOSE_EVIDENCE_PACK,
                            scope=SCOPE)
    bad_sig = dict(good)
    bad_sig["signature"] = "!!!not-base64!!!"
    with pytest.raises(SignatureError, match="malformed signature"):
        verify_envelope(envelope=bad_sig, manifest_bytes=MANIFEST,
                        trust=trust, purpose=PURPOSE_EVIDENCE_PACK,
                        scope=SCOPE)
    short = dict(good)
    short["signature"] = base64.b64encode(b"short").decode("ascii")
    with pytest.raises(SignatureError, match="not 64 bytes"):
        verify_envelope(envelope=short, manifest_bytes=MANIFEST,
                        trust=trust, purpose=PURPOSE_EVIDENCE_PACK,
                        scope=SCOPE)


def test_sign_rejects_bad_inputs(keys):
    with pytest.raises(SignatureError, match="empty manifest"):
        _sign(keys, manifest=b"")
    with pytest.raises(SignatureError, match="signer_id"):
        sign_manifest(manifest_bytes=MANIFEST, purpose=PURPOSE_EVIDENCE_PACK,
                      signer_id=" ", key_id="k1",
                      private_pem=keys["private_pem"])
    with pytest.raises(SignatureError, match="private key"):
        sign_manifest(manifest_bytes=MANIFEST, purpose=PURPOSE_EVIDENCE_PACK,
                      signer_id="a", key_id="k1", private_pem="junk")
    with pytest.raises(SignatureError, match="scope"):
        sign_manifest(manifest_bytes=MANIFEST, purpose=PURPOSE_EVIDENCE_PACK,
                      signer_id="a", key_id="k1",
                      private_pem=keys["private_pem"],
                      scope={"pack": 42})


def test_keypair_pems_parse_and_agree(keys):
    kp = generate_keypair()
    assert kp["private_pem"].startswith("-----BEGIN PRIVATE KEY-----")
    assert kp["public_pem"].startswith("-----BEGIN PUBLIC KEY-----")
    env = sign_manifest(manifest_bytes=MANIFEST, purpose=PURPOSE_EVIDENCE_PACK,
                        signer_id="a", key_id="k",
                        private_pem=kp["private_pem"])
    verify_envelope(envelope=env, manifest_bytes=MANIFEST,
                    trust={"k": kp["public_pem"]},
                    purpose=PURPOSE_EVIDENCE_PACK)
