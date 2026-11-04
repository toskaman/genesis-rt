# Codegen templates

Deterministic `string.Template` sources used by `host/genesis_rt/codegen.py`.

- `genesis_config_gen.h.tmpl` — per-machine numeric limits header.
- `genesis_build_gen.mk.tmpl` — per-machine build file (QNX `qcc` + host `cc` check).

Rules: no timestamps in output, no iteration over unordered data, every
rendered file records generator version, template version and IR sha256
so generated output is reproducible and auditable.
