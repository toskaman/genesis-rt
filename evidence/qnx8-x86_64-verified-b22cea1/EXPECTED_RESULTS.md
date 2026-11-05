# Expected results (op-0350e9bd4818)

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
- IR digest: 356dc135f27f4586e1131fe1e43eac0b054dc7f2fb1f1ba7506fd4d5667ce34d
- passport anchor (sha256): 421efd3acc0927fd0ed603b28dfd6626457a6ea5aeca6972e974abb2fa4ac0b0
