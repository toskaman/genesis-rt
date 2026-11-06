# GENESIS RT — Evidence trust model (Wave 12 §9)

Status: current. Implementation: `host/genesis_rt/signing.py`,
CLI `sign-pack` / `verify-pack`, tests `tests/unit/test_signing.py`
+ `tests/integration/test_signing_cli.py`.

## 1. What each layer proves

| Layer | Proves | Does NOT prove |
|---|---|---|
| Hash-linked passport + pack `manifest.json` | Internal consistency: files match pinned sha256, chain links verify, replay reproduces | Who produced the bundle |
| Ed25519 `manifest.sig.json` | Origin: only the holder of the private key could have bound *these exact bytes* to *this signer id*; integrity at rest | That the content is true, safe, or ran on real hardware |
| Independent replay (`verify.py`) | The verdict follows deterministically from the bundled inputs | That the inputs themselves are authentic |

Signatures upgrade "this bundle is self-consistent" to
"this bundle is self-consistent **and** Alice vouches for these
exact bytes". Nothing more.

## 2. Audit answers (§9 questions)

**Who created the evidence?** The `signer_id` string in the
envelope (e.g. an operator or CI runner identity). It is a claim
bound by the signature, not an independently authenticated login.

**How is its origin established?** The verifier pins a trust
store `{"keys": {key_id: public_pem}}`. A bundle verifies only
if its `key_id` is pinned and the Ed25519 signature over the
canonical envelope body is valid.

**Can the operator rewrite evidence and recompute all hashes?**
Yes — hashes alone never stop the machine owner. What the
operator *cannot* do without the private key is produce a
signature that verifies against someone else's pinned public
key. Detection, not prevention: ship the trust store out of band
and re-verify on receipt.

**Which external reference anchors the evidence?** The trust
store (public keys) plus the pinned `manifest_sha256`. There is
no blockchain, no transparency log, no trusted timestamping in
this release — `signed_utc` is informational.

**How are build and target identities bound?** Transitively:
the signed manifest pins `binaries.json`, `build-set.json`,
`qnx-build-record.json`, `target-op.json` and every transcript
by sha256. Alter any of them and the manifest digest — hence
the signature — no longer matches.

**What happens when the signing key is compromised?** Remove
its `key_id` from every trust store: all bundles signed by it
immediately verify as INVALID ("not trusted"). Re-sign current
bundles with the replacement key (use `--supersedes` to record
the rotation). There is no revocation list; the trust store *is*
the revocation mechanism. Past bundles cannot be "unseen" —
assume the attacker could have signed anything during the
exposure window.

**Can the verifier run without the production server?** Yes.
`verify-pack` needs only the pack directory, a trust store file,
Python and `cryptography`. The historical `verify.py` needs only
the standard library and keeps working on unsigned packs.

**What remains untrusted?** The signer is trusted to describe
what they ran honestly; timestamps; anything outside the
manifest's file list (e.g. `manifest.sig.json` itself and the
trust store file, which must arrive by a trusted channel); the
machine that ran the campaign; the QEMU-vs-hardware distinction
(signatures say nothing about where bytes were produced).

## 3. Key management policy

- Generate with `python -c "from genesis_rt.signing import
  generate_keypair"` (or any Ed25519 tool emitting PKCS8 /
  SubjectPublicKeyInfo PEM). One key per role
  (e.g. `genesis-pack-ci-2026-11-a`); never reuse a personal key.
- Private keys live in file permissions / a secret store, never
  in git, never in CI logs, never on public runners (see §8
  runner policy: untrusted PR code must not reach signing keys).
- Public keys ship in a versioned trust store distributed out
  of band (release asset, pinned commit, internal PKI).
- Rotation: mint `...-b`, sign new bundles with it
  (`--supersedes ...-a`), publish the new public key, migrate
  verifiers, then drop `...-a`. Rotation is tested in
  `test_rotation_old_key_removed_rejected_new_accepted`.

## 4. Verdict semantics

`verify-pack` exits `0` SIGNED_VALID, `2` UNSIGNED (hash-only,
no signer — legitimate for local dev), `1` INVALID (tampered,
wrong key, wrong purpose/scope, malformed). Callers and the
review brief must render all three distinctly; UNSIGNED is
never shown as trusted.

## 5. What is deliberately NOT claimed

No hardware attestation, no trusted timestamps, no identity
proof beyond the pinned key, no safety certification. A valid
signature on a bundle that describes a QEMU run is still a
QEMU run.
