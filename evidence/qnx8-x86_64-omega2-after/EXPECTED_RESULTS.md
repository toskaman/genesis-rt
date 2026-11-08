# Expected results (op-6840da0e9f69)

Observed values at pack build time. `python verify.py` reprints the
observed claims; compare them with this file.

- op state: COMPLETED
- gate verdict: PASS
- qnx_verified: True
- matrix: 16/16 checks passed
- fault scenarios sealed: 8 (nominal_navigation, speed_command_over_limit, stale_proximity_150ms, planner_process_crash...)
- passport chain links: 15
- performance samples: 1000 ({'clock': 'CLOCK_MONOTONIC on target (nanoseconds)', 'percentile': 'nearest-rank on sorted samples', 'probe': 'genesis_faultinject bench (sequential nominal MsgSend round trips, fresh seq each)', 'target': 'QNX 8.0 QEMU x86_64 (TCG); reproducibility only, not a hardware timing guarantee'})
- provenance: v2 err=None
- replay (in-op): {'verdict': 'PASS', 'qnx_verified': True}
- target identity: QNX qnxqemu 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64
- toolchain: qcc 12.2.0 (gcc_ntox86_64, default target)
- IR digest: 5639d986d258062fcad450260723a04d9de2b4c5432ddef516e81bffefdbe70f
- passport anchor (sha256): c9c73a137196fe9eb22676932edb140a060238a5742babd6c95c6331a9202a25
