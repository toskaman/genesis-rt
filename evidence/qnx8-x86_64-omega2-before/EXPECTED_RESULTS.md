# Expected results (op-d91bd4133590)

Observed values at pack build time. `python verify.py` reprints the
observed claims; compare them with this file.

- op state: COMPLETED
- gate verdict: PASS
- qnx_verified: True
- matrix: 16/16 checks passed
- fault scenarios sealed: 8 (corrupted_message, delayed_command, dropped_message, nominal_navigation...)
- passport chain links: 15
- performance samples: 1000 ({'clock': 'CLOCK_MONOTONIC on target (nanoseconds)', 'percentile': 'nearest-rank on sorted samples', 'probe': 'genesis_faultinject bench (sequential nominal MsgSend round trips, fresh seq each)', 'target': 'QNX 8.0 QEMU x86_64 (TCG); reproducibility only, not a hardware timing guarantee'})
- provenance: v2 err=None
- replay (in-op): {'verdict': 'PASS', 'qnx_verified': True}
- target identity: QNX qnxqemu 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64
- toolchain: qcc 12.2.0 (gcc_ntox86_64, default target)
- IR digest: 356dc135f27f4586e1131fe1e43eac0b054dc7f2fb1f1ba7506fd4d5667ce34d
- passport anchor (sha256): 3d64fc1c124d56e2b25153758292abfe05179164cba4906ea13a5f8f5c91e1e0
