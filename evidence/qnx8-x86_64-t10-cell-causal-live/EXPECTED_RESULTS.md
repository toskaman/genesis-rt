# Expected results (op-33c56ec417a4)

Observed values at pack build time. `python verify.py` reprints the
observed claims; compare them with this file.

- op state: COMPLETED
- gate verdict: PASS
- qnx_verified: True
- matrix: 16/16 checks passed
- fault scenarios sealed: 4 (cell_estop_during_transfer, cell_nominal_transfer, cell_stale_presence, cell_transfer_jam...)
- passport chain links: 11
- performance samples: 1000 ({'clock': 'CLOCK_MONOTONIC on target (nanoseconds)', 'percentile': 'nearest-rank on sorted samples', 'probe': 'genesis_faultinject bench (sequential nominal MsgSend round trips, fresh seq each)', 'target': 'QNX 8.0 QEMU x86_64 (TCG); reproducibility only, not a hardware timing guarantee'})
- provenance: v2 err=None
- replay (in-op): {'verdict': 'PASS', 'qnx_verified': True}
- target identity: QNX qnxqemu 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64
- toolchain: qcc 12.2.0 (gcc_ntox86_64, default target)
- IR digest: 73e52055d0173770bf904470f2fa565d95a198495ea386ad526366976776ff9b
- passport anchor (sha256): d180d878e48a2ef9e27be96ed87d9ecc25f1c981d610624313e0aadc5f6dc51e
