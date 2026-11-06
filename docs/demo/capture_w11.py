# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 11 demo capture: deterministic Playwright scenes, real data only.

Records 1920x1080 clips of the shipped Studio against the REAL local
artifact store (./artifacts): Wave 11 native ops A/B/C, a live fault
job, the evidence graph. No staged DOM, no mock backend.

Usage (from repo root):
  set PYTHONPATH=host
  python docs/demo/capture_w11.py --out docs/demo/footage-w11
  python docs/demo/capture_w11.py --out docs/demo/footage-w11 --scenes s1,s4

Job runs during capture create new dirs under artifacts/runs/
(git-ignored). Browsing committed ops is read-only.
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "host"))

OP_A = "op-d08d3d3ea346"  # Wave 11 BEFORE (1.2, 16/16 PASS)
OP_B = "op-67a4595a858f"  # Wave 11 AFTER (1.6, 16/16 PASS)
OP_C = "op-ad562b34f8de"  # Wave 11 stale-build negative (FAILED)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_server():
    import httpx
    import uvicorn

    from genesis_rt import api as api_mod

    api_mod.ARTIFACTS = REPO / "artifacts" / "runs"
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(
        api_mod.create_app(), host="127.0.0.1", port=port,
        log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"http://127.0.0.1:{port}/health",
                         timeout=2).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.2)
    else:
        raise RuntimeError("capture server never became ready")
    return server, thread, f"http://127.0.0.1:{port}"


def s1_judge(pg, out):
    pg.locator('button[data-tab="judge"]').click()
    pg.wait_for_function(
        "() => document.querySelector('#judge-out').innerText"
        ".includes('The machine')",
        timeout=15_000)
    pg.wait_for_timeout(10_000)


def s2_designer(pg, out):
    pg.locator('button[data-tab="designer"]').click()
    pg.wait_for_function(
        "() => document.querySelectorAll('#des-example option').length > 1",
        timeout=15_000)
    pg.locator("#des-example").select_option(
        value="amr-demo|machine-ir.json")
    pg.wait_for_function(
        "() => document.querySelector('#designer-text').value"
        '.includes("max_linear_speed_mps")',
        timeout=15_000)
    pg.locator("#des-validate").click()
    pg.wait_for_function(
        "() => document.querySelector('#designer-err').innerText"
        ".includes('Backend validation: OK')",
        timeout=15_000)
    pg.evaluate("() => { const t = document.querySelector("
                "'#designer-text'); t.scrollTop = t.scrollHeight * 0.35; }")
    pg.wait_for_timeout(13_000)


def s3_source(pg, out):
    pg.locator('button[data-tab="designer"]').click()
    pg.wait_for_function(
        "() => document.querySelectorAll('#des-example option').length > 1",
        timeout=15_000)
    pg.locator("#des-example").select_option(
        value="amr-demo|machine-ir.json")
    pg.wait_for_function(
        "() => document.querySelector('#designer-text').value"
        '.includes("max_linear_speed_mps")',
        timeout=15_000)
    pg.locator("#des-validate").click()
    pg.wait_for_function(
        "() => document.querySelector('#designer-err').innerText"
        ".includes('Backend validation: OK')",
        timeout=15_000)
    pg.locator('button[data-tab="source"]').click()
    pg.locator("#srcfiles").set_input_files([
        str(REPO / "evidence" / "qnx8-x86_64-w11-before" / "sources" /
            "genesis_config_gen.h"),
        str(REPO / "evidence" / "qnx8-x86_64-w11-before" / "sources" /
            "genesis_build_gen.mk"),
    ])
    pg.wait_for_function(
        "() => document.querySelector('#source-out').innerText"
        ".includes('genesis_config_gen.h')",
        timeout=15_000)
    pg.evaluate("() => document.querySelector('#source-out')"
                ".scrollIntoView({block: 'end'})")
    pg.wait_for_timeout(14_000)


def _open_op(pg, op_id):
    pg.locator('button[data-tab="target"]').click()
    pg.locator("#top-refresh").click()
    pg.wait_for_function(
        f"() => document.querySelector('#top-history').innerText"
        f".includes('{op_id}')",
        timeout=30_000)
    pg.locator(f'#top-history button[data-op="{op_id}"]').click()


def s4_target(pg, out):
    _open_op(pg, OP_A)
    pg.wait_for_function(
        "() => { const d = document.querySelector('#top-decision');"
        " return d && d.innerText.length > 60; }",
        timeout=30_000)
    pg.wait_for_timeout(16_000)


def s7_compare(pg, out):
    pg.locator('button[data-tab="target"]').click()
    pg.locator("#top-refresh").click()
    pg.wait_for_function(
        "() => document.querySelectorAll('#top-cmp-before option').length"
        " >= 2",
        timeout=30_000)
    pg.locator("#top-cmp-before").select_option(value=OP_A)
    pg.locator("#top-cmp-after").select_option(value=OP_B)
    pg.locator("#top-cmp-run").click()
    pg.wait_for_function(
        "() => document.querySelector('#top-compare').innerText"
        ".includes('Contract limit')",
        timeout=30_000)
    pg.evaluate("() => document.querySelector('#top-compare')"
                ".scrollIntoView()")
    pg.wait_for_timeout(6_000)
    pg.evaluate("() => document.querySelector('#top-compare')"
                ".scrollIntoView({block: 'end'})")
    pg.wait_for_timeout(8_000)


def s7c_negative(pg, out):
    _open_op(pg, OP_C)
    pg.wait_for_function(
        "() => document.querySelector('#top-out').innerText"
        ".includes('FAILED')",
        timeout=30_000)
    pg.wait_for_timeout(6_000)


def s9_value(pg, out):
    pg.locator('button[data-tab="judge"]').click()
    for _ in range(6):
        pg.locator('#judge-out button[data-jnav="next"]').click()
        pg.wait_for_timeout(400)
    pg.wait_for_function(
        "() => document.querySelector('#judge-out').innerText"
        ".includes('The value')",
        timeout=15_000)
    pg.wait_for_timeout(7_000)


def s5_fault(pg, out):
    pg.locator('button[data-tab="judge"]').click()
    for _ in range(2):
        pg.locator('#judge-out button[data-jnav="next"]').click()
        pg.wait_for_timeout(400)
    pg.wait_for_function(
        "() => document.querySelector('#judge-out').innerText"
        ".includes('The failure')",
        timeout=15_000)
    old = pg.evaluate("() => (window.Live && Live.judge && "
                      "Live.judge.jobId) || ''")
    pg.locator('#judge-out button[data-jaction="judge-run-fault"]').click()
    pg.locator("#pipe-out").wait_for(timeout=30_000)
    pg.wait_for_function(
        "() => { const j = (window.Live && Live.judge && "
        f"Live.judge.jobId) || ''; return j !== '' && j !== '{old}'; }}",
        timeout=30_000)
    job_id = pg.evaluate("() => window.Live.judge.jobId")
    (out / "fault-job.txt").write_text(job_id, encoding="utf-8")
    pg.wait_for_function(
        "() => { const t = document.querySelector('#pipe-out').innerText;"
        f" return t.includes('{job_id}') && "
        "(t.includes('succeeded') || t.includes('failed')); }",
        timeout=240_000)
    pg.wait_for_timeout(9_000)


def s6_diagnose(pg, out):
    job_id = (out / "fault-job.txt").read_text(encoding="utf-8").strip()
    assert job_id.startswith("run-"), job_id
    pg.locator('button[data-tab="evidence"]').click()
    pg.wait_for_function(
        "() => document.querySelectorAll('#graph-run option').length > 1",
        timeout=15_000)
    pg.locator("#graph-run").select_option(value=job_id)
    pg.locator("#graph-loadrun").click()
    pg.wait_for_function(
        "() => typeof Studio !== 'undefined' && !!Studio.graphPassportText",
        timeout=30_000)
    pg.locator("#graph-ir").select_option(value="amr-demo|machine-ir.json")
    pg.locator("#graph-render").click()
    pg.wait_for_selector("#graph-out tr.pick", timeout=30_000)
    pg.wait_for_timeout(3_000)
    pg.locator("#graph-out tr.pick").first.click()
    pg.wait_for_function(
        "() => document.querySelector('#graph-detail').innerText.length"
        " > 40",
        timeout=15_000)
    pg.wait_for_timeout(11_000)


SCENES = {"s1": s1_judge, "s2": s2_designer, "s3": s3_source,
          "s4": s4_target, "s5": s5_fault, "s6": s6_diagnose,
          "s7": s7_compare, "s7c": s7c_negative, "s9": s9_value}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--scenes", default=",".join(SCENES))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright

    server, thread, base = start_server()
    print("server:", base, flush=True)
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True, timeout=60_000,
                                            args=["--lang=en-US"])
            except Exception:
                cands = [os.environ.get("GENESIS_E2E_BROWSER", ""),
                         r"C:\Program Files\Google\Chrome\Application"
                         r"\chrome.exe",
                         r"C:\Program Files (x86)\Microsoft\Edge\Application"
                         r"\msedge.exe"]
                cands = [c for c in cands if c and Path(c).is_file()]
                if not cands:
                    raise RuntimeError("no usable browser for capture")
                print("fallback browser:", cands[0], flush=True)
                browser = p.chromium.launch(
                    headless=True, executable_path=cands[0],
                    timeout=60_000, args=["--lang=en-US"])
            for name in args.scenes.split(","):
                fn = SCENES[name.strip()]
                ctx = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                    record_video_dir=str(out),
                    record_video_size={"width": 1920, "height": 1080})
                pg = ctx.new_page()
                pg.goto(f"{base}/studio.html")
                pg.wait_for_load_state("networkidle")
                print(f"scene {name} ...", flush=True)
                fn(pg, out)
                video = pg.video
                assert video is not None
                ctx.close()
                Path(video.path()).replace(out / f"{name}.webm")
                print(f"scene {name} done", flush=True)
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=15)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
