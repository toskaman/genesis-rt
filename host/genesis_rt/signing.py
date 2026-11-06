# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Optional Ed25519 signing for evidence-pack manifests (Wave 12 §9).

Trust model (short version; full audit in docs/evidence-trust.md):

* The hash-linked passport proves *internal consistency* of a bundle.
  A signature additionally binds the bundle to a *signer identity*:
  only someone holding the private key could have produced a valid
  ``manifest.sig.json`` for these exact manifest bytes.
* Signatures do NOT prove the signed content is true, safe, or
  produced on real hardware. They prove origin + integrity at rest.
* ``signed_utc`` is informational. There is no trusted timestamping.
* Unsigned packs keep working everywhere; verifiers must report
  UNSIGNED explicitly instead of treating it as valid.

Envelope ``manifest.sig.json`` (sibling of ``manifest.json``;
the manifest itself is never modified, so historical packs and
their ``verify.py`` keep working byte-for-byte)::

    {"sig_version": 1, "purpose": "genesis-evidence-pack/1",
     "signer_id": "alice@example.com", "key_id": "...",
     "signed_utc": "...", "manifest_sha256": "<sha256 of the
     manifest.json BYTES as stored>",
     "scope": {"pack": "<pack name>"}, "signature": "<base64>"}

The signature covers the canonical JSON of the envelope body
(everything except ``"signature"``). Verification fails closed:
any error raises :class:`SignatureError`.

Key rotation: verifiers pin a trust store
``{"keys": {key_id: public_pem}}``. To rotate, sign with the new
key (optionally naming the old one in ``"supersedes"``), publish
the new public key, then remove the old key_id from the trust
store once every consumer has migrated.
"""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_pem_private_key,
    load_pem_public_key,
)

from .ir import canonical_json

SIG_VERSION = 1
PURPOSE_EVIDENCE_PACK = "genesis-evidence-pack/1"
PURPOSE_PROOFOS_PLAN = "genesis-proofos-plan/1"


class SignatureError(Exception):
    """Raised for every signature problem (fail-closed)."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_keypair() -> dict[str, str]:
    """Generate an Ed25519 keypair; returns PEM strings.

    The private key is unencrypted: protect it with file
    permissions or a secret store (see docs/evidence-trust.md).
    """
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    return {
        "private_pem": priv.private_bytes(
            Encoding.PEM, PrivateFormat.PKCS8,
            NoEncryption()).decode("ascii"),
        "public_pem": pub.public_bytes(
            Encoding.PEM,
            PublicFormat.SubjectPublicKeyInfo).decode("ascii"),
    }


def _load_private(pem: str) -> Ed25519PrivateKey:
    try:
        key = load_pem_private_key(pem.encode("ascii"), password=None)
    except (ValueError, TypeError) as exc:
        raise SignatureError(f"unusable private key: {exc}") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise SignatureError("private key is not Ed25519")
    return key


def _load_public(pem: str) -> Ed25519PublicKey:
    try:
        key = load_pem_public_key(pem.encode("ascii"))
    except (ValueError, TypeError) as exc:
        raise SignatureError(f"unusable public key: {exc}") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise SignatureError("public key is not Ed25519")
    return key


def _body_of(envelope: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in envelope.items() if k != "signature"}


def sign_manifest(*, manifest_bytes: bytes, purpose: str,
                  signer_id: str, key_id: str, private_pem: str,
                  scope: dict[str, str] | None = None,
                  supersedes: str | None = None) -> dict[str, Any]:
    """Sign exact manifest bytes; returns the envelope (without
    writing anything). Raises SignatureError on bad inputs."""
    if not manifest_bytes:
        raise SignatureError("cannot sign empty manifest")
    for name, val in (("purpose", purpose), ("signer_id", signer_id),
                      ("key_id", key_id)):
        if not isinstance(val, str) or not val.strip():
            raise SignatureError(f"{name} must be a non-empty string")
        if len(val) > 256:
            raise SignatureError(f"{name} too long")
    if scope is not None and (
            not isinstance(scope, dict) or not all(
                isinstance(k, str) and isinstance(v, str)
                for k, v in scope.items())):
        raise SignatureError("scope must be a {str: str} mapping")
    body: dict[str, Any] = {
        "sig_version": SIG_VERSION,
        "purpose": purpose,
        "signer_id": signer_id,
        "key_id": key_id,
        "signed_utc": _utcnow(),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }
    if scope:
        body["scope"] = dict(scope)
    if supersedes:
        body["supersedes"] = supersedes
    key = _load_private(private_pem)
    sig = key.sign(canonical_json(body).encode("utf-8"))
    return {**body, "signature": base64.b64encode(sig).decode("ascii")}


def verify_envelope(*, envelope: Any, manifest_bytes: bytes,
                    trust: dict[str, str], purpose: str,
                    scope: dict[str, str] | None = None) -> dict[str, Any]:
    """Verify an envelope against exact manifest bytes.

    ``trust`` maps key_id -> public PEM. ``scope``, when given,
    must equal the envelope scope exactly (replay resistance
    across packs/plans). Returns the verified envelope body.
    Raises SignatureError for every failure (fail-closed).
    """
    if not isinstance(envelope, dict):
        raise SignatureError("envelope must be a JSON object")
    if envelope.get("sig_version") != SIG_VERSION:
        raise SignatureError(
            f"unsupported sig_version: {envelope.get('sig_version')!r}")
    if envelope.get("purpose") != purpose:
        raise SignatureError(
            f"purpose mismatch: envelope says "
            f"{envelope.get('purpose')!r}, expected {purpose!r}")
    if (scope is not None) != ("scope" in envelope):
        raise SignatureError("scope binding mismatch")
    if scope is not None and envelope.get("scope") != scope:
        raise SignatureError("scope mismatch: envelope is bound to a "
                             "different pack/plan")
    want = hashlib.sha256(manifest_bytes).hexdigest()
    if envelope.get("manifest_sha256") != want:
        raise SignatureError("manifest bytes differ from signed digest")
    key_id = envelope.get("key_id")
    if not isinstance(key_id, str) or key_id not in trust:
        raise SignatureError(f"key_id {key_id!r} is not trusted")
    try:
        raw = base64.b64decode(envelope.get("signature") or "", validate=True)
    except (ValueError, TypeError) as exc:
        raise SignatureError(f"malformed signature: {exc}") from exc
    if len(raw) != 64:
        raise SignatureError("malformed signature: not 64 bytes")
    pub = _load_public(trust[key_id])
    try:
        pub.verify(raw, canonical_json(_body_of(envelope)).encode("utf-8"))
    except InvalidSignature as exc:
        raise SignatureError("signature does not verify") from exc
    return _body_of(envelope)


def is_signed(pack_dir: Any) -> bool:
    """True when ``pack_dir/manifest.sig.json`` exists (unsigned
    packs are legitimate; callers must say so explicitly)."""
    from pathlib import Path

    return (Path(pack_dir) / "manifest.sig.json").is_file()
