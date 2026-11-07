# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Ascension: application shell — breadcrumbs, deep links, history,
vertical keyboard navigation, and real browser-zoom reflow."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright", reason="playwright not installed")
pytest.importorskip("uvicorn", reason="uvicorn not installed")

from playwright.sync_api import sync_playwright  # noqa: E402

from test_a11y_axe import _launch, studio_url  # noqa: E402,F401


def _open(p, url, **kw):
    b = _launch(p)
    pg = b.new_page(**kw)
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(url)
    pg.wait_for_load_state("networkidle")
    return b, pg, errors


def test_first_visit_lands_on_overview_with_breadcrumb(studio_url):
    with sync_playwright() as p:
        b, pg, errors = _open(p, studio_url)
        assert pg.get_attribute("#tabbtn-overview", "aria-selected") == "true"
        assert pg.inner_text("#crumbs").replace("\n", "") == "Start / Overview"
        assert pg.is_visible("text=One requirement change, verified natively twice")
        b.close()
    assert errors == []


def test_deep_link_and_back_forward(studio_url):
    with sync_playwright() as p:
        b, pg, errors = _open(p, studio_url + "#/diff")
        assert pg.get_attribute("#tabbtn-diff", "aria-selected") == "true"
        assert "Evidence" in pg.inner_text("#crumb-sec")
        pg.click("#tabbtn-target")
        assert pg.url.endswith("#/target")
        pg.go_back()
        pg.wait_for_function("location.hash === '#/diff'")
        assert pg.get_attribute("#tabbtn-diff", "aria-selected") == "true"
        pg.go_forward()
        pg.wait_for_function("location.hash === '#/target'")
        assert pg.get_attribute("#tabbtn-target", "aria-selected") == "true"
        b.close()
    assert errors == []


def test_unknown_deep_link_falls_back_to_overview(studio_url):
    with sync_playwright() as p:
        b, pg, errors = _open(p, studio_url + "#/does-not-exist")
        assert pg.get_attribute("#tabbtn-overview", "aria-selected") == "true"
        b.close()
    assert errors == []


def test_vertical_arrow_keys_move_between_sections(studio_url):
    with sync_playwright() as p:
        b, pg, errors = _open(p, studio_url)
        pg.focus("#tabbtn-overview")
        pg.keyboard.press("ArrowDown")
        assert pg.evaluate("document.activeElement.id") == "tabbtn-judge"
        pg.keyboard.press("ArrowUp")
        assert pg.evaluate("document.activeElement.id") == "tabbtn-overview"
        pg.keyboard.press("End")
        assert pg.get_attribute("#tabbtn-run", "aria-selected") == "true"
        b.close()
    assert errors == []


@pytest.mark.parametrize("zoom", [2, 4])
def test_browser_zoom_reflow(studio_url, zoom):
    """WCAG 1.4.4 / 1.4.10: 200 % and 400 % zoom of a 1280 px window is
    emulated with deviceScaleFactor-free CSS pixels (1280/zoom wide)."""
    with sync_playwright() as p:
        b, pg, errors = _open(p, studio_url,
                              viewport={"width": 1280 // zoom, "height": 800 // zoom})
        bad = []
        for tab in ("overview", "judge", "designer", "target", "diff", "evidence"):
            pg.click(f"#tabbtn-{tab}")
            pg.wait_for_timeout(100)
            over = pg.evaluate("document.documentElement.scrollWidth - "
                               "document.documentElement.clientWidth")
            if over > 1:
                bad.append(f"{tab}:+{over}px")
        b.close()
    assert bad == [] and errors == [], (bad, errors)
