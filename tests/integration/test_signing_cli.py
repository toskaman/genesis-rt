# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: sign-pack / verify-pack CLI on scratch packs.

Uses the real Wave 11 AFTER manifest bytes (copied to tmp) so the
round trip covers a production-shaped manifest without touching the
committed pack.
"""
import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("cryptography", reason="cryptography not installed")

from genesis_rt.cli import main  # noqa: E402
from genesis_rt.signing import generate_keypair  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AFTER_MANIFEST = (REPO_ROOT / "evidence" / "qnx8-x86_64-w11-after"
                  / "manifest.json")


@pytest.fixture()
def pack(tmp_path):
    d = tmp_path / "pack"
    d.mkdir()
    shutil.copy(AFTER_MANIFEST, d / "manifest.json")
    return d


@pytest.fixture()
def keypair(tmp_path):
    kp = generate_keypair()
    priv = tmp_path / "sign.key"
    priv.write_text(kp["private_pem"], encoding="utf-8")
    trust = tmp_path / "trust.json"
    trust.write_text(json.dumps({"keys": {"k1": kp["public_pem"]}}),
                     encoding="utf-8")
    return {"priv": priv, "trust": trust}


def test_sign_then_verify_round_trip(pack, keypair, capsys):
    rc = main(["sign-pack", str(pack), "--key", str(keypair["priv"]),
               "--signer-id", "ci@example.com", "--key-id", "k1"])
    assert rc == 0, capsys.readouterr().err
    assert (pack / "manifest.sig.json").is_file()
    # The manifest itself is untouched: historical verifiers keep working.
    assert (pack / "manifest.json").read_bytes() == AFTER_MANIFEST.read_bytes()
    capsys.readouterr()
    rc = main(["verify-pack", str(pack), "--trust", str(keypair["trust"])])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "SIGNED_VALID" in out and "k1" in out


def test_verify_unsigned_pack_reports_unsigned(pack, keypair, capsys):
    rc = main(["verify-pack", str(pack), "--trust", str(keypair["trust"])])
    out = capsys.readouterr().out
    assert rc == 2, out
    assert "UNSIGNED" in out


def test_verify_tampered_manifest_fails(pack, keypair, capsys):
    assert main(["sign-pack", str(pack), "--key", str(keypair["priv"]),
                 "--signer-id", "ci@example.com", "--key-id", "k1"]) == 0
    capsys.readouterr()
    with open(pack / "manifest.json", "ab") as fh:
        fh.write(b" ")
    rc = main(["verify-pack", str(pack), "--trust", str(keypair["trust"])])
    out = capsys.readouterr().out
    assert rc == 1, out
    assert "INVALID" in out


def test_verify_wrong_trust_store_fails(pack, keypair, tmp_path, capsys):
    assert main(["sign-pack", str(pack), "--key", str(keypair["priv"]),
                 "--signer-id", "ci@example.com", "--key-id", "k1"]) == 0
    capsys.readouterr()
    other = generate_keypair()
    wrong = tmp_path / "wrong-trust.json"
    wrong.write_text(json.dumps({"keys": {"k1": other["public_pem"]}}),
                     encoding="utf-8")
    rc = main(["verify-pack", str(pack), "--trust", str(wrong), "--json"])
    out = capsys.readouterr().out
    assert rc == 1, out
    assert json.loads(out)["status"] == "INVALID"


def test_verify_json_shape(pack, keypair, capsys):
    assert main(["sign-pack", str(pack), "--key", str(keypair["priv"]),
                 "--signer-id", "ci@example.com", "--key-id", "k1"]) == 0
    capsys.readouterr()
    rc = main(["verify-pack", str(pack), "--trust", str(keypair["trust"]),
               "--json"])
    out = capsys.readouterr().out
    assert rc == 0, out
    body = json.loads(out)
    assert body["status"] == "SIGNED_VALID"
    assert body["pack"] == "qnx8-x86_64-w11-after"
    assert body["signer_id"] == "ci@example.com"


def test_sign_missing_manifest_is_usage_error(tmp_path, keypair, capsys):
    rc = main(["sign-pack", str(tmp_path), "--key", str(keypair["priv"]),
               "--signer-id", "ci@example.com", "--key-id", "k1"])
    assert rc == 2
