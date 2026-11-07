# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""TITAN: automated WCAG 2.2 A/AA scan of every Studio tab with axe-core,
in both themes, plus 320 px reflow. Automated only: it does NOT replace a
manual screen-reader audit (see docs/design/ACCESSIBILITY_AUDIT.md).

axe-core is located via $GENESIS_AXE_JS or node_modules/axe-core (CI runs
`npm install --no-save axe-core@4.10.2`). Without it the test SKIPS
visibly; it never passes silently.
"""
from __future__ import annotations

import os
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

ROOT = Path(__file__).resolve().parents[2]
TABS = ["overview", "judge", "projects", "designer", "source", "pipeline", "target",
        "lab", "run", "passport", "diff", "evidence", "twin"]
AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]


_BROWSER_CANDIDATES = [
    os.environ.get("GENESIS_E2E_BROWSER", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
]


def _launch(p):
    """Bundled Chromium, else a system Chrome/Edge (same policy as the
    other E2E files), else a visible skip."""
    try:
        return p.chromium.launch(headless=True, timeout=60_000)
    except Exception as exc:  # noqa: BLE001 - fall back to system browsers
        last = exc
    for cand in _BROWSER_CANDIDATES:
        if cand and Path(cand).is_file():
            try:
                return p.chromium.launch(headless=True, executable_path=cand,
                                         timeout=60_000)
            except Exception as exc:  # noqa: BLE001
                last = exc
    pytest.skip(f"no usable browser for e2e ({last})")


def _axe_source() -> str | None:
    for cand in (os.environ.get("GENESIS_AXE_JS", ""),
                 str(ROOT / "node_modules" / "axe-core" / "axe.min.js")):
        if cand and Path(cand).is_file():
            return Path(cand).read_text(encoding="utf-8")
    return None


@pytest.fixture(scope="module")
def studio_url(tmp_path_factory):
    prev = api_mod.ARTIFACTS
    api_mod.ARTIFACTS = tmp_path_factory.mktemp("a11y") / "artifacts"
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(
        api_mod.create_app(), host="127.0.0.1", port=port, log_level="error"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
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
        pytest.fail("a11y server never became ready")
    yield f"http://127.0.0.1:{port}/studio.html"
    server.should_exit = True
    th.join(timeout=15)
    api_mod.ARTIFACTS = prev


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_axe_wcag22_no_serious_violations(studio_url, theme):
    axe = _axe_source()
    if axe is None:
        pytest.skip("axe-core not installed (npm install --no-save "
                    "axe-core@4.10.2) — automated a11y scan NOT executed")
    with sync_playwright() as p:
        browser = _launch(p)
        pg = browser.new_page(viewport={"width": 1366, "height": 900})
        pg.add_init_script(
            f"try{{localStorage.setItem('studio.theme','{theme}')}}catch(e){{}}")
        pg.goto(studio_url)
        pg.wait_for_load_state("networkidle")
        pg.add_script_tag(content=axe)
        problems = []
        for tab in TABS:
            pg.locator(f'button[data-tab="{tab}"]').click()
            pg.wait_for_timeout(150)
            res = pg.evaluate(
                """async (tags) => {
                  const r = await axe.run(document,
                    {runOnly: {type: 'tag', values: tags}});
                  return r.violations
                    .filter(v => v.impact === 'serious' || v.impact === 'critical')
                    .map(v => v.id + ' x' + v.nodes.length + ' ' +
                         (v.nodes[0] ? v.nodes[0].target.join(' ') : ''));
                }""", AXE_TAGS)
            problems += [f"{tab}: {v}" for v in res]
        browser.close()
    assert problems == [], "\n".join(sorted(set(problems))[:40])


def test_reflow_320px_every_tab(studio_url):
    """WCAG 1.4.10: no page-level horizontal scroll at 320 CSS px."""
    with sync_playwright() as p:
        browser = _launch(p)
        pg = browser.new_page(viewport={"width": 320, "height": 640})
        pg.goto(studio_url)
        pg.wait_for_load_state("networkidle")
        bad = []
        for tab in TABS:
            pg.locator(f'button[data-tab="{tab}"]').click()
            pg.wait_for_timeout(100)
            over = pg.evaluate("document.documentElement.scrollWidth - "
                               "document.documentElement.clientWidth")
            if over > 1:
                bad.append(f"{tab}: +{over}px")
        browser.close()
    assert bad == [], bad
