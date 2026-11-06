# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 11 Phase B (§9): real-browser negative paths + viewport audit.

Live uvicorn server (tmp artifact store) drives the shipped Studio in
headless Chromium. Unlike the Judge journey, these tests expect HTTP
4xx from the API (invalid IR, bogus image dir, ...): that is correct
API behavior, so the fixture only fails on JS console/page errors and
each test asserts the UI shows an honest message -- never a stale or
false success.

A skipped browser (no Chromium/Chrome/Edge anywhere) skips the file,
like the Judge journey. With a browser present there are no skips.
"""
from __future__ import annotations

import json
import os
import socket
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("playwright", reason="playwright not installed")
pytest.importorskip("uvicorn", reason="uvicorn not installed")
pytest.importorskip("httpx", reason="httpx needed for readiness probe")

import httpx  # noqa: E402
import uvicorn  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from genesis_rt import api as api_mod  # noqa: E402

JOB_TIMEOUT_MS = 180_000

_BROWSER_CANDIDATES = [
    os.environ.get("GENESIS_E2E_BROWSER", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def srv(tmp_path_factory):
    """Fresh live backend per test (one test kills its server)."""
    tmp = tmp_path_factory.mktemp("e2e-neg")
    prev = api_mod.ARTIFACTS
    api_mod.ARTIFACTS = tmp / "artifacts"
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
        server.should_exit = True
        pytest.fail("e2e server never became ready")
    yield SimpleNamespace(base=f"http://127.0.0.1:{port}",
                          server=server, thread=thread)
    server.should_exit = True
    thread.join(timeout=15)
    api_mod.ARTIFACTS = prev


def _launch(p):
    try:
        return p.chromium.launch(headless=True, timeout=60_000)
    except Exception as first_err:  # no bundled browser: try system ones
        for cand in _BROWSER_CANDIDATES:
            if cand and Path(cand).is_file():
                try:
                    return p.chromium.launch(
                        headless=True, executable_path=cand,
                        timeout=60_000)
                except Exception:
                    continue
        pytest.skip(f"no usable browser for e2e ({first_err})")


def _watch(pg, errors: list[str]) -> None:
    # Chromium reports failed fetches (expected 4xx / dead server on
    # these paths) as console errors; the HTTP status is asserted via
    # UI text instead. Genuine JS errors still fail the test.
    pg.on("console", lambda m: errors.append(m.text)
          if (m.type == "error" and "Failed to load resource" not in m.text
              and "net::" not in m.text) else None)
    pg.on("pageerror", lambda e: errors.append(str(e)))


@pytest.fixture()
def page(srv):
    errors: list[str] = []
    with sync_playwright() as p:
        browser = _launch(p)
        pg = browser.new_page(viewport={"width": 1366, "height": 768})
        _watch(pg, errors)
        pg.goto(f"{srv.base}/studio.html")
        pg.wait_for_load_state("networkidle")
        yield pg
        assert errors == [], f"browser errors: {errors[:8]}"
        browser.close()


def _shot(pg, tmp_path, name):
    pg.screenshot(path=str(tmp_path / f"{name}.png"))


def _pick_example(pg, want: str = "") -> str:
    """Pipeline tab: select an example, wait for its scenarios."""
    pg.locator('button[data-tab="pipeline"]').click()
    pg.wait_for_function(
        "() => document.querySelectorAll('#pipe-example option').length > 1",
        timeout=15_000)
    values = pg.locator("#pipe-example option").evaluate_all(
        "els => els.map(e => e.value)")
    value = next((v for v in values[1:] if want in v), values[1])
    pg.locator("#pipe-example").select_option(value=value)
    pg.wait_for_selector("#pipe-scenarios input[data-scen]", timeout=15_000)
    return value


def _job_id(pg) -> str:
    return pg.evaluate(
        "() => (window.Live && Live.jobId) || ''") or ""


def _pick_slowest_example(pg) -> str:
    """Pipeline tab: select the example with the most scenarios.

    Cancel tests race the job to completion; the widest scenario set
    maximizes the cancellation window on fast runners.
    """
    pg.locator('button[data-tab="pipeline"]').click()
    pg.wait_for_function(
        "() => document.querySelectorAll('#pipe-example option').length > 1",
        timeout=15_000)
    values = pg.locator("#pipe-example option").evaluate_all(
        "els => els.map(e => e.value)")
    best, best_n = values[1], -1
    for value in values[1:]:
        pg.locator("#pipe-example").select_option(value=value)
        pg.wait_for_selector("#pipe-scenarios input[data-scen]",
                             timeout=15_000)
        n = pg.locator("#pipe-scenarios input[data-scen]").count()
        if n > best_n:
            best, best_n = value, n
    pg.locator("#pipe-example").select_option(value=best)
    pg.wait_for_selector("#pipe-scenarios input[data-scen]",
                         timeout=15_000)
    return best


# -- Pipeline guidance -------------------------------------------------


def test_pipeline_run_without_source_shows_guidance(page):
    page.locator('button[data-tab="pipeline"]').click()
    page.locator("#pipe-run").click()
    page.wait_for_function(
        "() => document.querySelector('#pipe-out').innerText"
        ".includes('Pick an example or project first')",
        timeout=10_000)


def test_pipeline_run_without_scenarios_shows_guidance(page):
    _pick_example(page)
    page.locator("#pipe-scenarios input[data-scen]").evaluate_all(
        "els => els.forEach(e => { e.checked = false; })")
    page.locator("#pipe-run").click()
    page.wait_for_function(
        "() => document.querySelector('#pipe-out').innerText"
        ".includes('Select at least one scenario')",
        timeout=10_000)


# -- Designer validation -----------------------------------------------


def test_designer_rejects_invalid_json(page):
    page.locator('button[data-tab="designer"]').click()
    page.locator("#designer-text").fill("{not json")
    page.locator("#des-validate").click()
    page.wait_for_function(
        "() => document.querySelector('#designer-err').innerText"
        ".includes('not valid JSON')",
        timeout=10_000)


def test_designer_rejects_invalid_ir(page):
    page.locator('button[data-tab="designer"]').click()
    page.locator("#designer-text").fill('{"schema_version": 1}')
    page.locator("#des-validate").click()
    page.wait_for_function(
        "() => document.querySelector('#designer-err').innerText"
        ".includes('backend validation failed')",
        timeout=15_000)
    assert "Backend validation: OK" not in \
        page.locator("#designer-err").inner_text()


# -- Source provenance pin (JS-reserialization regression) --------------


def test_source_pin_matches_after_validate(page, repo_root):
    """Genuine generated files pin MATCH after example load + validate.

    Regression: Studio hashed reserialized editor text, and
    JSON.stringify spells 1.0 as 1, so the pack's own header showed
    MISMATCH. The pin now uses the backend validated digest.
    """
    header = (repo_root / "evidence" / "qnx8-x86_64-w11-before" /
              "sources" / "genesis_config_gen.h")
    assert header.is_file()
    page.locator('button[data-tab="designer"]').click()
    page.wait_for_function(
        "() => document.querySelectorAll('#des-example option').length > 1",
        timeout=15_000)
    page.locator("#des-example").select_option(
        value="amr-demo|machine-ir.json")
    page.wait_for_function(
        "() => document.querySelector('#designer-err').innerText"
        ".includes('Backend validation: OK')",
        timeout=15_000)
    assert page.evaluate("() => Studio.irSha") == \
        "356dc135f27f4586e1131fe1e43eac0b054dc7f2fb1f1ba7506fd4d5667ce34d"
    page.locator('button[data-tab="source"]').click()
    page.locator("#srcfiles").set_input_files(str(header))
    page.wait_for_function(
        "() => document.querySelector('#source-out').innerText"
        ".includes('matches loaded IR')",
        timeout=15_000)


# -- Job lifecycle: cancel / refresh / navigation -----------------------


def _cancelled_or_completed(page, job_id: str) -> str:
    """Cancel a live job; tolerate it having just finished honestly.

    Fast runners can complete a host job in ~2 s. Either terminal
    state is asserted for identity + no false success; API-level
    cancel tests pin the cancel path deterministically.
    """
    from playwright.sync_api import TimeoutError as PwTimeout

    try:
        page.wait_for_function(
            "() => !document.querySelector('#pipe-cancel').disabled",
            timeout=10_000)
    except PwTimeout:
        text = page.locator("#pipe-out").inner_text()
        assert job_id in text
        assert "succeeded" in text or "failed" in text, text[-400:]
        assert page.locator("#pipe-cancel").is_disabled()
        return "terminal"
    try:
        page.locator("#pipe-cancel").click(timeout=3_000)
    except PwTimeout:
        pass  # job finished between the enabled check and the click
    page.wait_for_function(
        "() => { const t = document.querySelector('#pipe-out').innerText;"
        " return t.includes('cancelled') || t.includes('succeeded') || "
        "t.includes('failed'); }",
        timeout=60_000)
    text = page.locator("#pipe-out").inner_text()
    assert job_id in text  # identity preserved, not swapped
    if "cancelled" in text:
        assert "succeeded" not in text
        assert "verdict PASS" not in text
    assert page.locator("#pipe-run").is_enabled()  # controls recover
    return "cancelled" if "cancelled" in text else "terminal"


def test_cancel_running_job_never_reports_success(page):
    _pick_slowest_example(page)
    page.locator("#pipe-run").click()
    page.wait_for_function(
        "() => (window.Live && Live.jobId) || ''", timeout=30_000)
    job_id = _job_id(page)
    assert job_id.startswith("run-"), job_id
    _cancelled_or_completed(page, job_id)


def test_refresh_mid_run_recovers_honest_state(page, tmp_path):
    _pick_example(page)
    page.locator("#pipe-run").click()
    page.wait_for_function(
        "() => (window.Live && Live.jobId) || ''", timeout=30_000)
    job_id = _job_id(page)
    page.reload()
    page.wait_for_load_state("networkidle")
    page.locator('button[data-tab="pipeline"]').click()
    page.wait_for_function(
        "() => document.querySelector('#pipe-out').innerText"
        f".includes('{job_id}')",
        timeout=30_000)
    page.wait_for_function(
        "() => { const t = document.querySelector('#pipe-out').innerText;"
        f" return t.includes('{job_id}') && "
        "(t.includes('succeeded') || t.includes('failed')); }",
        timeout=JOB_TIMEOUT_MS)
    _shot(page, tmp_path, "neg-refresh-recovered")


def test_navigation_during_run_preserves_job(page):
    _pick_slowest_example(page)
    page.locator("#pipe-run").click()
    page.wait_for_function(
        "() => (window.Live && Live.jobId) || ''", timeout=30_000)
    job_id = _job_id(page)
    for tab in ("designer", "evidence", "judge", "pipeline"):
        page.locator(f'button[data-tab="{tab}"]').click()
    text = page.locator("#pipe-out").inner_text()
    assert job_id in text
    _cancelled_or_completed(page, job_id)  # end the run quickly


# -- Passport trust ------------------------------------------------------


def test_tampered_passport_rejected_in_browser(page, tmp_path, repo_root):
    golden = (repo_root / "artifacts" / "samples" /
              "golden_demo_passport.example.json")
    assert golden.is_file()
    tampered = tmp_path / "tampered.json"
    doc = json.loads(golden.read_text(encoding="utf-8"))
    doc["chain"][1]["body"]["ir_sha256"] = "00" * 32  # break chain
    tampered.write_text(json.dumps(doc), encoding="utf-8")
    page.locator('button[data-tab="passport"]').click()
    page.locator("#ppfile").set_input_files(str(golden))
    page.wait_for_function(
        "() => document.querySelector('#lab-out').innerText.length > 40",
        timeout=15_000)
    assert "Passport invalid" not in page.locator("#pp-out").inner_text()
    page.locator("#ppfile").set_input_files(str(tampered))
    page.wait_for_function(
        "() => document.querySelector('#lab-out').innerText"
        ".includes('Passport invalid')",
        timeout=15_000)
    assert "stay empty" in page.locator("#lab-out").inner_text()
    assert page.evaluate("() => Studio.passport === null")


# -- Target tab guidance -------------------------------------------------


def test_target_run_without_source_shows_guidance(page):
    page.locator('button[data-tab="target"]').click()
    page.locator("#top-run").click()
    page.wait_for_function(
        "() => document.querySelector('#top-out').innerText"
        ".includes('Pick an example or project in the Pipeline tab')",
        timeout=10_000)


def test_target_run_rejects_bogus_image_dir(page):
    _pick_example(page)
    page.locator('button[data-tab="target"]').click()
    page.locator("#top-workflow").select_option(value="full")
    page.locator("#top-image").fill("Z:/no-such-qemu-image")
    page.locator("#top-run").click()
    page.wait_for_function(
        "() => { const t = document.querySelector('#top-out').innerText;"
        " return t.includes('target run failed') || "
        "t.includes('Native target unavailable'); }",
        timeout=30_000)
    if "Native target unavailable" in page.locator("#top-out").inner_text():
        # SDK-less CI: the SDK guard fires before any image check.
        assert "Host verification" in \
            page.locator("#top-out").inner_text()
        return
    assert "not a directory" in page.locator("#top-out").inner_text()
    assert page.locator("#top-run").is_enabled()


def test_compare_empty_state(page):
    page.locator('button[data-tab="target"]').click()
    page.locator("#top-refresh").click()
    page.wait_for_function(
        "() => document.querySelector('#top-history').innerText"
        ".includes('No target ops yet')",
        timeout=15_000)
    page.locator("#top-cmp-run").click()
    assert "Pick two finished ops to compare" in \
        page.locator("#top-compare").inner_text()


def test_target_navigation_back_reattaches_op(page):
    _pick_example(page)
    page.locator('button[data-tab="target"]').click()
    _run_build_only(page)
    page.wait_for_function(
        "() => document.querySelector('#top-out').innerText"
        ".includes('Native target unavailable') || "
        "document.querySelector('#top-history').innerText"
        ".includes('COMPLETED')",
        timeout=120_000)
    if "Native target unavailable" in page.locator("#top-out").inner_text():
        return  # SDK-less path already pinned by the compare test
    op_id = page.evaluate("() => (window.Live && Live.opId) || ''")
    assert op_id.startswith("op-"), op_id
    for tab in ("pipeline", "evidence", "target"):
        page.locator(f'button[data-tab="{tab}"]').click()
    page.wait_for_function(
        "() => document.querySelector('#top-out').innerText"
        f".includes('{op_id}')",
        timeout=30_000)
    assert "COMPLETED" in page.locator("#top-history").inner_text()
    assert page.locator("#top-cancel").is_disabled()  # terminal: no cancel


# -- Flagship: edit limit -> two real ops -> change proof -----------------


def _wait_op_terminal(pg, timeout_ms=120_000) -> str:
    pg.wait_for_function(
        "() => { const t = document.querySelector('#top-history').innerText;"
        " return t.includes('COMPLETED') || t.includes('FAILED'); }",
        timeout=timeout_ms)
    return pg.locator("#top-history").inner_text()


def _run_build_only(pg) -> None:
    pg.locator("#top-workflow").select_option(value="build-only")
    pg.locator("#top-image").fill("")
    pg.locator("#top-run").click()


def test_limit_change_compare_renders_change_proof(page, tmp_path,
                                                   repo_root):
    # Op 1: stock amr example, real qcc build on target service.
    amr_value = _pick_example(page, want="amr-demo|machine-ir.json")
    page.locator('button[data-tab="target"]').click()
    _run_build_only(page)
    page.wait_for_function(
        "() => document.querySelector('#top-out').innerText"
        ".includes('Native target unavailable') || "
        "document.querySelector('#top-history').innerText"
        ".includes('COMPLETED') || "
        "document.querySelector('#top-history').innerText"
        ".includes('FAILED')",
        timeout=120_000)
    if "Native target unavailable" in page.locator("#top-out").inner_text():
        # Honest SDK-less path (CI): no phantom op, host fallback named.
        assert "Host verification" in \
            page.locator("#top-out").inner_text()
        page.locator("#top-refresh").click()
        page.wait_for_function(
            "() => document.querySelector('#top-history').innerText"
            ".includes('No target ops yet')",
            timeout=15_000)
        return
    hist = page.locator("#top-history").inner_text()
    if "COMPLETED" not in hist:
        # NOTE (6 Nov 2026): op1 FAILED here in 2 of 6 loaded runs
        # (full suite + e2e dir); 5 consecutive runs since are green
        # and the op record rotated before diagnosis. Prime suspect
        # is a transient Windows toolchain hiccup under load (qcc/make
        # share %TEMP% with the browser farm), not the product: every
        # assertion below already passed on the same committed code.
        # No retry: a future occurrence must surface with this diag.
        diag = page.evaluate(
            "() => fetch('/target/ops?limit=5').then(r => r.json())"
            ".then(d => { const o = (d.ops || [])[0] || {}; return "
            "fetch('/target/ops/' + o.op_id).then(r => r.json())"
            ".then(rec => JSON.stringify({state: rec.state, "
            "steps: (rec.steps || []).map(s => s.step + '=' + s.state), "
            "error: (rec.error || '').slice(0, 400)})); })"
            ".catch(e => 'diag-failed: ' + e)")
        raise AssertionError(f"op1 not COMPLETED: {hist[-300:]} {diag}")
    # Op 2: same machine with one edited limit, via designer + project.
    page.locator('button[data-tab="designer"]').click()
    page.locator("#des-example").select_option(value=amr_value)
    page.wait_for_function(
        "() => document.querySelector('#designer-text').value"
        '.includes("max_linear_speed_mps")',
        timeout=15_000)
    ir = json.loads(page.locator("#designer-text").input_value())
    assert ir["control"]["max_linear_speed_mps"] == 1.2
    ir["control"]["max_linear_speed_mps"] = 1.3
    page.locator("#designer-text").fill(json.dumps(ir))
    page.locator("#des-savename").fill("e2e-limit-1v3")
    page.locator("#des-saveas").click()
    page.wait_for_function(
        "() => document.querySelector('#designer-err').innerText"
        ".includes('Created project')",
        timeout=15_000)
    page.locator('button[data-tab="pipeline"]').click()
    page.wait_for_function(
        "() => document.querySelectorAll('#pipe-project option').length > 1",
        timeout=15_000)
    page.locator("#pipe-project").select_option(index=1)
    page.wait_for_selector("#pipe-scenarios input[data-scen]",
                           timeout=15_000)
    page.locator('button[data-tab="target"]').click()
    _run_build_only(page)
    # Wait for a genuinely NEW second op (the first COMPLETED would
    # match a naive wait: stale-content race).
    page.wait_for_function(
        "() => (document.querySelector('#top-history').innerText"
        ".match(/op-[0-9a-f]{12}/g) || []).length >= 2",
        timeout=120_000)
    page.wait_for_function(
        "() => document.querySelector('#top-history').innerText"
        ".split('COMPLETED').length >= 3",
        timeout=120_000)
    hist = page.locator("#top-history").inner_text()
    assert hist.count("COMPLETED") >= 2, hist[-600:]
    # Compare: the edited limit must show as changed with proof rows.
    page.wait_for_function(
        "() => document.querySelectorAll('#top-cmp-before option').length"
        " >= 2",
        timeout=15_000)
    page.locator("#top-cmp-before").select_option(index=0)
    page.locator("#top-cmp-after").select_option(index=1)
    page.locator("#top-cmp-run").click()
    page.wait_for_function(
        "() => document.querySelector('#top-compare').innerText"
        ".includes('Contract limit')",
        timeout=30_000)
    cmp = page.locator("#top-compare").inner_text()
    assert "1.2" in cmp and "1.3" in cmp, cmp[-800:]
    assert "(changed)" in cmp
    for row in ("Generated #define", "Guard sha256", "Native 1.5 m/s probe"):
        assert row in cmp, row
    n_dos = page.evaluate(
        "() => [...document.querySelectorAll('#top-compare a')]"
        ".filter(a => a.textContent === 'dossier (.zip)').length")
    assert n_dos == 2, n_dos
    _shot(page, tmp_path, "neg-limit-change-proof")


# -- Backend outage --------------------------------------------------------


def test_backend_outage_surfaces_errors_not_false_data(page, srv):
    page.locator('button[data-tab="pipeline"]').click()
    page.wait_for_selector("#pipe-history", timeout=15_000)
    srv.server.should_exit = True
    srv.thread.join(timeout=15)
    page.locator("#pipe-refresh").click()
    page.wait_for_function(
        "() => document.querySelector('#pipe-history').innerText"
        ".includes('history failed')",
        timeout=30_000)


# -- Viewport audit ----------------------------------------------------------


@pytest.mark.parametrize("width,height", [(1920, 1080), (1366, 768),
                                          (390, 844)])
def test_viewport_audit_no_horizontal_overflow(srv, tmp_path, width,
                                               height):
    tabs = ["judge", "pipeline", "target", "passport", "evidence",
            "designer"]
    with sync_playwright() as p:
        browser = _launch(p)
        pg = browser.new_page(viewport={"width": width, "height": height})
        errs: list[str] = []
        _watch(pg, errs)
        pg.goto(f"{srv.base}/studio.html")
        pg.wait_for_load_state("networkidle")
        for tab in tabs:
            pg.locator(f'button[data-tab="{tab}"]').click()
            pg.wait_for_timeout(600)
            overflow = pg.evaluate(
                "() => document.documentElement.scrollWidth - "
                "document.documentElement.clientWidth")
            assert overflow <= 1, f"{width}x{height} tab={tab} " \
                f"h-overflow={overflow}px"
        pg.locator('button[data-tab="judge"]').click()
        pg.screenshot(path=str(tmp_path / f"audit-{width}x{height}.png"))
        assert errs == [], f"browser errors: {errs[:8]}"
        browser.close()
