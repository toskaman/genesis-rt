# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""W1: Break-it button acceptance in a real browser.

Click #break-run -> refusal card naming the mutated binary; dead
backend -> honest error state. Live uvicorn server, headless Chromium
(or system Chrome/Edge); skipped only when no browser exists at all.
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

_BREAK_TIMEOUT_MS = 60_000

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


def _start(tmp):
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
    return server, thread, port, prev


@pytest.fixture(scope="module")
def srv(tmp_path_factory):
    server, thread, port, prev = _start(tmp_path_factory.mktemp("e2e-break"))
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


def _watch(pg, errors: list[str]) -> None:
    pg.on("console", lambda m: errors.append(m.text)
          if (m.type == "error" and "Failed to load resource" not in m.text
              and "net::" not in m.text) else None)
    pg.on("pageerror", lambda e: errors.append(str(e)))


def _goto_diff(pg):
    toggle = pg.locator("#menu-toggle")
    if (toggle.count() and toggle.is_visible()
            and not pg.locator('button[data-tab="diff"]').is_visible()):
        toggle.click()
    pg.locator('button[data-tab="diff"]').click()
    pg.wait_for_selector("#break-run")


def test_break_click_renders_refusal_card(srv):
    """The REAL Break-it click: note -> breaking -> refusal card."""
    with sync_playwright() as p:
        browser = _launch(p)
        errs: list[str] = []
        pg = browser.new_page(viewport={"width": 1366, "height": 768})
        _watch(pg, errs)
        try:
            pg.goto(f"{srv.base}/studio.html")
            pg.wait_for_load_state("networkidle")
            _goto_diff(pg)
            assert "Nothing broken yet" in pg.locator("#break-out").inner_text()
            pg.locator("#break-run").click()
            pg.wait_for_selector("#break-out .proof-card",
                                 timeout=_BREAK_TIMEOUT_MS)
            text = pg.locator("#break-out").inner_text()
            assert "STALE" in text
            assert "genesis_guard" in text
            assert "cannot pass" in text
            assert "archived" in text
            assert errs == [], errs
        finally:
            browser.close()


def test_break_click_dead_backend_shows_error(tmp_path):
    """Dead backend: honest error state, no fake card, no JS errors."""
    server, thread, port, prev = _start(tmp_path / "dead")
    with sync_playwright() as p:
        browser = _launch(p)
        errs: list[str] = []
        pg = browser.new_page(viewport={"width": 1366, "height": 768})
        _watch(pg, errs)
        try:
            pg.goto(f"http://127.0.0.1:{port}/studio.html")
            pg.wait_for_load_state("networkidle")
            _goto_diff(pg)
            server.should_exit = True
            thread.join(timeout=15)
            pg.locator("#break-run").click()
            pg.wait_for_selector("#break-out .fail",
                                 timeout=_BREAK_TIMEOUT_MS)
            assert "Break-it failed" in pg.locator("#break-out").inner_text()
            assert "proof-card" not in pg.locator("#break-out").inner_html()
            assert errs == [], errs
        finally:
            browser.close()
            api_mod.ARTIFACTS = prev
