# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""OMEGA6 B2: K1 Prove-button acceptance in a real browser.

The first REAL click of the Studio Prove button (previously only
grepped): file inputs -> Prove -> verdict card, plus empty/error
states, 320/390/1366 widths, a keyboard-only path, and 200/400%
zoom. Live uvicorn server over a tmp artifact store, headless
Chromium (or system Chrome/Edge); skipped only when no browser
exists at all.
"""
from __future__ import annotations

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

PROVE_TIMEOUT_MS = 180_000

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
def srv(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("e2e-prove")
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
    yield SimpleNamespace(base=f"http://127.0.0.1:{port}")
    server.should_exit = True
    thread.join(timeout=15)
    api_mod.ARTIFACTS = prev


def _launch(p):
    try:
        return p.chromium.launch(headless=True, timeout=60_000)
    except Exception as first_err:
        for cand in _BROWSER_CANDIDATES:
            if cand and Path(cand).is_file():
                try:
                    return p.chromium.launch(
                        headless=True, executable_path=cand,
                        timeout=60_000)
                except Exception:
                    continue
        pytest.skip(f"no usable browser for e2e ({first_err})")


@pytest.fixture()
def own_srv(tmp_path):
    """Private backend for the test that kills its server."""
    prev = api_mod.ARTIFACTS
    api_mod.ARTIFACTS = tmp_path / "artifacts"
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


def _watch(pg, errors: list[str]) -> None:
    # Expected 4xx fetches (bad-IR error state) surface as failed
    # resources; the test asserts UI text instead. Genuine JS
    # errors still fail.
    pg.on("console", lambda m: errors.append(m.text)
          if (m.type == "error" and "Failed to load resource" not in m.text
              and "net::" not in m.text) else None)
    pg.on("pageerror", lambda e: errors.append(str(e)))


def _prove_page(p, srv, width=1366, height=768):
    browser = _launch(p)
    errs: list[str] = []
    pg = browser.new_page(viewport={"width": width, "height": height})
    _watch(pg, errs)
    pg.goto(f"{srv.base}/studio.html")
    pg.wait_for_load_state("networkidle")
    return browser, pg, errs


def _goto_diff(pg):
    toggle = pg.locator("#menu-toggle")
    if (toggle.count() and toggle.is_visible()
            and not pg.locator('button[data-tab="diff"]').is_visible()):
        toggle.click()
    pg.locator('button[data-tab="diff"]').click()
    pg.wait_for_selector("#change-prove")


def _cell_pair(repo_root):
    cell = Path(str(repo_root)) / "examples" / "cell-demo"
    return cell / "cell-ir-broken.json", cell / "cell-ir.json"


def test_prove_click_renders_verdict_card(srv, repo_root):
    """The REAL Prove click: empty state -> loading -> verdict card."""
    with sync_playwright() as p:
        browser, pg, errs = _prove_page(p, srv)
        try:
            _goto_diff(pg)
            assert "No change proof yet." in \
                pg.locator("#change-out").inner_text()
            before_ir, after_ir = _cell_pair(repo_root)
            pg.locator("#chgfile-a").set_input_files(str(before_ir))
            pg.locator("#chgfile-b").set_input_files(str(after_ir))
            pg.locator("#change-prove").click()
            pg.wait_for_function(
                "() => document.querySelector('#change-out').innerText"
                ".includes('verdict:') || "
                "document.querySelector('#change-out').innerText"
                ".includes('Contract knobs')",
                timeout=PROVE_TIMEOUT_MS)
            card = pg.locator("#change-out").inner_text()
            assert "max_linear_speed_mps" in card
            assert "cell_nominal_transfer" in card
            assert "ran where: before=host after=host" in card
            assert "chains: before=valid after=valid" in card
            assert "PASS" in card
            assert errs == [], f"browser errors: {errs[:8]}"
        finally:
            browser.close()


def test_prove_error_states_are_honest(srv, repo_root, tmp_path):
    with sync_playwright() as p:
        browser, pg, errs = _prove_page(p, srv)
        try:
            _goto_diff(pg)
            pg.locator("#change-prove").click()
            pg.wait_for_function(
                "() => document.querySelector('#change-out').innerText"
                ".includes('Load both IR files first.')",
                timeout=10_000)
            bad_json = tmp_path / "not-json.txt"
            bad_json.write_text("{oops", encoding="utf-8")
            pg.locator("#chgfile-a").set_input_files(str(bad_json))
            pg.wait_for_function(
                "() => document.querySelector('#change-out').innerText"
                ".includes('IR A is not valid JSON.')",
                timeout=10_000)
            bad_ir = tmp_path / "bad-ir.json"
            bad_ir.write_text('{"schema_version": 99}', encoding="utf-8")
            _, after_ir = _cell_pair(repo_root)
            pg.locator("#chgfile-a").set_input_files(str(bad_ir))
            pg.locator("#chgfile-b").set_input_files(str(after_ir))
            pg.locator("#change-prove").click()
            pg.wait_for_function(
                "() => document.querySelector('#change-out').innerText"
                ".includes('Prove failed')",
                timeout=PROVE_TIMEOUT_MS)
            assert errs == [], f"browser errors: {errs[:8]}"
        finally:
            browser.close()


@pytest.mark.parametrize("width,height", [(320, 568), (390, 844),
                                         (1366, 768)])
def test_prove_card_widths_no_overflow(srv, repo_root, width, height):
    with sync_playwright() as p:
        browser, pg, errs = _prove_page(p, srv, width, height)
        try:
            _goto_diff(pg)
            before_ir, after_ir = _cell_pair(repo_root)
            pg.locator("#chgfile-a").set_input_files(str(before_ir))
            pg.locator("#chgfile-b").set_input_files(str(after_ir))
            pg.locator("#change-prove").click()
            pg.wait_for_function(
                "() => document.querySelector('#change-out').innerText"
                ".includes('Contract knobs')",
                timeout=PROVE_TIMEOUT_MS)
            overflow = pg.evaluate(
                "() => document.documentElement.scrollWidth - "
                "document.documentElement.clientWidth")
            assert overflow <= 1, \
                f"{width}x{height} h-overflow={overflow}px"
            card = pg.locator("#change-out").inner_text()
            assert "max_linear_speed_mps" in card and "PASS" in card
            assert errs == [], f"browser errors: {errs[:8]}"
        finally:
            browser.close()


@pytest.mark.parametrize("zoom", ["200%", "400%"])
def test_prove_card_usable_at_zoom(srv, repo_root, zoom):
    with sync_playwright() as p:
        browser, pg, errs = _prove_page(p, srv)
        try:
            _goto_diff(pg)
            before_ir, after_ir = _cell_pair(repo_root)
            pg.locator("#chgfile-a").set_input_files(str(before_ir))
            pg.locator("#chgfile-b").set_input_files(str(after_ir))
            pg.locator("#change-prove").click()
            pg.wait_for_function(
                "() => document.querySelector('#change-out').innerText"
                ".includes('Contract knobs')",
                timeout=PROVE_TIMEOUT_MS)
            pg.evaluate(f"() => {{ document.body.style.zoom = '{zoom}'; }}")
            pg.wait_for_timeout(500)
            card = pg.locator("#change-out").inner_text()
            assert "max_linear_speed_mps" in card
            assert "PASS" in card
            pg.locator("#change-prove").scroll_into_view_if_needed(
                timeout=10_000)
            assert pg.locator("#change-prove").is_visible()
            assert errs == [], f"browser errors: {errs[:8]}"
        finally:
            browser.close()


def test_prove_backend_dead_fails_honest(own_srv, repo_root):
    """F1 degraded path: the backend dies after the IRs load —
    Prove must say it failed, never render a stale card."""
    with sync_playwright() as p:
        browser, pg, errs = _prove_page(p, own_srv)
        try:
            _goto_diff(pg)
            before_ir, after_ir = _cell_pair(repo_root)
            pg.locator("#chgfile-a").set_input_files(str(before_ir))
            pg.locator("#chgfile-b").set_input_files(str(after_ir))
            own_srv.server.should_exit = True
            own_srv.thread.join(timeout=15)
            pg.locator("#change-prove").click()
            pg.wait_for_function(
                "() => document.querySelector('#change-out').innerText"
                ".includes('Prove failed')",
                timeout=60_000)
            card = pg.locator("#change-out").inner_text()
            assert "Contract knobs" not in card
            assert errs == [], f"browser errors: {errs[:8]}"
        finally:
            browser.close()


def test_prove_keyboard_only_path(srv):
    """Tab to the diff tab, Tab through the Prove panel, activate
    with the keyboard: the no-files error proves the keyboard path
    reaches the button and its handler end to end."""
    with sync_playwright() as p:
        browser, pg, errs = _prove_page(p, srv)
        try:
            pg.keyboard.press("Tab")
            for _ in range(40):
                focused = pg.evaluate(
                    "() => { const el = document.activeElement; "
                    "return (el && el.dataset.tab) || ''; }")
                if focused:
                    break
                pg.keyboard.press("Tab")
            else:
                raise AssertionError("never tabbed into the tab list")
            # Roving tabindex (WAI-ARIA tabs pattern): arrows move
            # between tabs, Tab leaves the list.
            for _ in range(20):
                if focused == "diff":
                    break
                pg.keyboard.press("ArrowRight")
                focused = pg.evaluate(
                    "() => { const el = document.activeElement; "
                    "return (el && el.dataset.tab) || ''; }")
            assert focused == "diff", \
                f"never arrowed to the diff tab (stuck on {focused!r})"
            pg.keyboard.press("Enter")
            pg.wait_for_selector("#change-prove")
            for _ in range(20):
                focused = pg.evaluate(
                    "() => (document.activeElement && "
                    "document.activeElement.id) || ''")
                if focused == "change-prove":
                    break
                pg.keyboard.press("Tab")
            else:
                raise AssertionError("never tabbed to the Prove button")
            pg.keyboard.press("Enter")
            pg.wait_for_function(
                "() => document.querySelector('#change-out').innerText"
                ".includes('Load both IR files first.')",
                timeout=10_000)
            assert errs == [], f"browser errors: {errs[:8]}"
        finally:
            browser.close()
