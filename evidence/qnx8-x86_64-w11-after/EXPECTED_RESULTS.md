# Expected results (op-67a4595a858f)

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
- target identity: QNX qnxqemu 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64 | --- | name                                                                             | usr/lib/ssh/ssh
- toolchain: cc: targets available in E:/qnx800/host/win64/x86_64/etc/qcc: 12.2.0,gcc_ntoaarch64le 12.2.0,gcc_ntoaarch64le_cxx 12.2.0,gcc_ntoaarch64le_gpp 12.2.0,gcc_ntox86_
- IR digest: fb2dbb3de8a19546d29be71b55e9f89bc37241627339430d11fea40c319e4d5c
- passport anchor (sha256): 3c6401934e9efb72cd030e9bc8d9dc0f66543664c1de8e7b5076ce41e21e7f96
