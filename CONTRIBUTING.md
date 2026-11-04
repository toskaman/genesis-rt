# Contributing

Short rules for the hackathon sprint; a fuller guide follows if the project grows.

1. **Original work only.** Do not copy third-party code, SDK headers, images or
   binaries into this repo. QNX tooling is referenced by official links, never
   redistributed.
2. **Evidence over claims.** Every behavior change ships with a test and, where
   relevant, a passport/oracle update. `no-test => no-pass` applies to PRs too.
3. **Determinism.** No timestamps, randomness without seeds, or unordered
   iteration in codegen, simulator or evidence paths.
4. **Fail closed.** Unknown inputs deny; new states/transitions default to
   SAFE_STOP until specified and tested.
5. **Keep the C/Python policy mirror in sync.** Change `guard_policy.c` and
   `guard_policy.py` together and extend `test_c_conformance.py` vectors.
6. Run `python -m pytest tests/ -q` before pushing; host CI must stay green.

License: by contributing you agree your contribution is under Apache-2.0.
