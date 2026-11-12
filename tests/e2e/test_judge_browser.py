# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 10 Sprint B (F3): real-browser Judge Mode journey.

A live uvicorn server (tmp artifact store) drives the actual shipped
Studio in headless Chromium: Judge stages A->G with two REAL host jobs
(fault run + verification rerun), release banner, and a target-tab
check. Console/page errors fail the test.

Needs a browser: Playwright-bundled Chromium, $GENESIS_E2E_BROWSER,
or a system Chrome/Edge. CI installs Chromium explicitly.
"""
from __future__ import annotations

import os
import re
import socket
import threading
import time
from pathlib import Path

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


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("e2e")
    # No monkeypatch (function-scoped): patch + restore manually.
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
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=15)
    api_mod.ARTIFACTS = prev


@pytest.fixture()
def page(base_url, tmp_path):
    errors: list[str] = []
    with sync_playwright() as p:
        browser = None
        last_err: Exception | None = None
        try:
            browser = p.chromium.launch(headless=True, timeout=60_000)
        except Exception as exc:  # no bundled browser: try system ones
            last_err = exc
            for cand in _BROWSER_CANDIDATES:
                if cand and Path(cand).is_file():
                    try:
                        browser = p.chromium.launch(
                            headless=True, executable_path=cand,
                            timeout=60_000)
                        break
                    except Exception as exc2:
                        last_err = exc2
        if browser is None:
            pytest.skip(f"no usable browser for e2e ({last_err})")
        pg = browser.new_page(viewport={"width": 1366, "height": 768})
        pg.on("console",
              lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("response", lambda r: errors.append(
            f"HTTP {r.status} {r.url}") if r.status >= 400 else None)
        pg.goto(f"{base_url}/studio.html")
        pg.wait_for_load_state("networkidle")
        yield pg
        assert errors == [], f"browser errors: {errors[:8]}"
        browser.close()


def _shot(pg, tmp_path, name):
    pg.screenshot(path=str(tmp_path / f"{name}.png"))


def _judge_text(pg) -> str:
    return pg.locator("#judge-out").inner_text()


def _judge_job_id(pg) -> str:
    return pg.evaluate(
        "() => (window.Live && Live.judge && Live.judge.jobId) || ''") or ""


def _wait_judge_job_done(pg, old_id: str) -> None:
    """Wait for the CURRENT judge job to succeed.

    First waits for Live.judge.jobId to change (the POST resolves
    async after the click), then requires that id plus 'succeeded' in
    the panel: without both guards, the wait can match the previous
    stage's settled output (stale-content race).
    """
    import re

    pg.wait_for_function(
        "() => { const j = (window.Live && Live.judge && "
        f"Live.judge.jobId) || ''; return j !== '' && j !== '{old_id}'; }}",
        timeout=30_000)
    job_id = _judge_job_id(pg)
    assert re.fullmatch(r"run-[0-9a-f]{12}", job_id), job_id
    pg.wait_for_function(
        "() => { const t = document.querySelector('#pipe-out').innerText;"
        f" return t.includes('{job_id}') && t.includes('succeeded'); }}",
        timeout=JOB_TIMEOUT_MS)


def test_judge_host_journey_stages_a_to_g(page, tmp_path):
    pg = page
    pg.locator('button[data-tab="judge"]').click()
    pg.wait_for_selector("#judge-out")
    assert "The machine" in _judge_text(pg)
    assert "[LIVE]" in _judge_text(pg)
    _shot(pg, tmp_path, "a-machine")

    pg.locator('#judge-out button[data-jnav="next"]').click()
    assert "The generated QNX software" in _judge_text(pg)
    pg.locator('#judge-out button[data-jaction="judge-open-source"]').click()
    assert pg.locator('button[data-tab="source"][aria-selected="true"]'
                      ).count() == 1
    # The action navigates away: a persistent return button must offer
    # the way back to the guided step (OMEGA9 judge-flow fix).
    back = pg.locator("#judge-back")
    assert back.is_visible()
    assert "step software" in back.inner_text()
    back.click()
    assert pg.locator('button[data-tab="judge"][aria-selected="true"]'
                      ).count() == 1
    assert not back.is_visible()

    pg.locator('#judge-out button[data-jnav="next"]').click()
    assert "The failure" in _judge_text(pg)
    old = _judge_job_id(pg)
    pg.locator('#judge-out button[data-jaction="judge-run-fault"]').click()
    pg.locator("#pipe-out").wait_for()
    _wait_judge_job_done(pg, old)
    assert "verdict" in pg.locator("#pipe-out").inner_text()
    _shot(pg, tmp_path, "c-fault-run")

    pg.locator('button[data-tab="judge"]').click()
    pg.locator('#judge-out button[data-jnav="next"]').click()
    assert "The diagnosis" in _judge_text(pg)
    pg.locator('#judge-out button[data-jaction="judge-open-evidence"]'
               ).click()
    assert pg.locator('button[data-tab="evidence"][aria-selected="true"]'
                      ).count() == 1

    pg.locator('button[data-tab="judge"]').click()
    pg.locator('#judge-out button[data-jnav="next"]').click()
    assert "The correction" in _judge_text(pg)
    pg.locator('#judge-out button[data-jaction="judge-open-designer"]'
               ).click()
    assert pg.locator('button[data-tab="designer"][aria-selected="true"]'
                      ).count() == 1

    pg.locator('button[data-tab="judge"]').click()
    pg.locator('#judge-out button[data-jnav="next"]').click()
    assert "The verification" in _judge_text(pg)
    old = _judge_job_id(pg)
    pg.locator('#judge-out button[data-jaction="judge-run-verify"]').click()
    _wait_judge_job_done(pg, old)
    assert "verdict" in pg.locator("#pipe-out").inner_text()
    _shot(pg, tmp_path, "f-verify-run")

    pg.locator('button[data-tab="judge"]').click()
    pg.locator('#judge-out button[data-jnav="next"]').click()
    assert "The value" in _judge_text(pg)
    pg.locator('#judge-out button[data-jaction="judge-open-dossier"]').click()
    assert pg.locator('button[data-tab="passport"][aria-selected="true"]'
                      ).count() == 1
    pg.locator('button[data-tab="judge"]').click()
    # The dossier fetch resolves async: wait for its note, whatever it
    # says, then assert on the settled content.
    pg.wait_for_function(
        "() => document.querySelector('#judge-out').innerText"
        ".includes('Release state')",
        timeout=15_000)
    banner = _judge_text(pg)
    assert "unreadable" not in banner, banner[-800:]
    assert ("release_eligible:" in banner  # full-coverage verdict
            or "NOT release eligible" in banner  # targeted run
            or "No gate record" in banner), banner[-800:]
    _shot(pg, tmp_path, "g-release")


def test_judge_stage_h_causal_full_run_shows_proof_timing(page):
    # Full archived run: six hypotheses execute, the winner renders with
    # the measured incident-to-proof time (OMEGA9 winner-lesson #11).
    pg = page
    pg.locator('button[data-tab="judge"]').click()
    pg.wait_for_selector("#judge-out")
    for _ in range(7):
        pg.locator('#judge-out button[data-jnav="next"]').click()
    assert "The causal proof" in _judge_text(pg)
    action = pg.locator(
        '#judge-out button[data-jaction="judge-run-causal"]')
    assert action.count() == 1
    action.click()
    pg.wait_for_selector('#judge-out :text("H-estop: SUPPORTED")',
                         timeout=120_000)
    assert re.search(r"in \d+(\.\d+)?s", _judge_text(pg)), _judge_text(pg)
    # T10: the stage names the committed live-QNX grounding of the same
    # incident (archived record, labeled as such — never faked live).
    assert "t10-causal-live-dossier" in _judge_text(pg)


def test_target_tab_empty_state(page):
    pg = page
    pg.locator('button[data-tab="target"]').click()
    pg.locator("#top-refresh").click()
    pg.wait_for_function(
        "() => document.querySelector('#top-history').innerText"
        ".includes('No target ops yet')",
        timeout=15_000)
    # Rendered history only (page.content includes the inline JS source).
    assert "top-dossier" not in pg.locator("#top-history").inner_html()


def test_overview_current_source_and_stage_a_copy(page):
    """Omega3 P1b: the overview surfaces the current-source Omega2
    packs next to the W11 flagship cards, and Judge stage A names
    the AMR example it actually opens (not an industrial cell)."""
    pg = page
    ov = pg.locator("#tab-overview").inner_text()
    assert "One requirement change, verified natively twice" in ov
    assert "evidence/qnx8-x86_64-omega2-before" in ov
    assert "evidence/qnx8-x86_64-omega2-after/verify.py" in ov
    pg.locator('button[data-tab="judge"]').click()
    judge = pg.locator("#tab-judge").inner_text()
    assert "The virtual AMR" in judge
    assert "industrial cell" not in judge
