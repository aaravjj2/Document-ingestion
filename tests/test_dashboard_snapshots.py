"""
Visual snapshot testing for dashboard pages.
Captures screenshots and HTML snapshots for regression testing.
"""
import os
from pathlib import Path

import pytest
from playwright.sync_api import Page


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
SNAPSHOT_DIR = Path("tests/snapshots")
SNAPSHOT_DIR.mkdir(exist_ok=True, parents=True)


class TestPageSnapshots:
    """Capture page snapshots for visual regression testing."""
    
    def test_home_page_screenshot(self, page: Page):
        """Capture home page screenshot."""
        page.goto(BASE_URL)
        page.wait_for_timeout(3000)  # Wait for data to load
        
        # Take full page screenshot
        screenshot_path = SNAPSHOT_DIR / "home_page.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        assert screenshot_path.exists()
        
    def test_documents_page_screenshot(self, page: Page):
        """Capture documents page screenshot."""
        page.goto(f"{BASE_URL}/documents")
        page.wait_for_timeout(3000)
        
        screenshot_path = SNAPSHOT_DIR / "documents_page.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        assert screenshot_path.exists()
        
    def test_upload_page_screenshot(self, page: Page):
        """Capture upload page screenshot."""
        page.goto(f"{BASE_URL}/upload")
        page.wait_for_timeout(1000)
        
        screenshot_path = SNAPSHOT_DIR / "upload_page.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        assert screenshot_path.exists()
        
    def test_health_page_screenshot(self, page: Page):
        """Capture health page screenshot."""
        page.goto(f"{BASE_URL}/health")
        page.wait_for_timeout(3000)
        
        screenshot_path = SNAPSHOT_DIR / "health_page.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        assert screenshot_path.exists()


class TestHTMLSnapshots:
    """Capture HTML snapshots for comparison."""
    
    def test_home_page_html_snapshot(self, page: Page):
        """Capture home page HTML."""
        page.goto(BASE_URL)
        page.wait_for_timeout(3000)
        
        html_path = SNAPSHOT_DIR / "home_page.html"
        html_content = page.content()
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        assert html_path.exists()
        assert len(html_content) > 1000  # Should have substantial content
        
    def test_documents_page_html_snapshot(self, page: Page):
        """Capture documents page HTML."""
        page.goto(f"{BASE_URL}/documents")
        page.wait_for_timeout(3000)
        
        html_path = SNAPSHOT_DIR / "documents_page.html"
        html_content = page.content()
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        assert html_path.exists()
        
    def test_upload_page_html_snapshot(self, page: Page):
        """Capture upload page HTML."""
        page.goto(f"{BASE_URL}/upload")
        
        html_path = SNAPSHOT_DIR / "upload_page.html"
        html_content = page.content()
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        assert html_path.exists()
        
    def test_health_page_html_snapshot(self, page: Page):
        """Capture health page HTML."""
        page.goto(f"{BASE_URL}/health")
        page.wait_for_timeout(3000)
        
        html_path = SNAPSHOT_DIR / "health_page.html"
        html_content = page.content()
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        assert html_path.exists()


class TestMobileSnapshots:
    """Capture mobile viewport snapshots."""
    
    def test_home_page_mobile(self, page: Page):
        """Capture home page on mobile viewport."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(BASE_URL)
        page.wait_for_timeout(3000)
        
        screenshot_path = SNAPSHOT_DIR / "home_page_mobile.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        assert screenshot_path.exists()
        
    def test_documents_page_mobile(self, page: Page):
        """Capture documents page on mobile viewport."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{BASE_URL}/documents")
        page.wait_for_timeout(3000)
        
        screenshot_path = SNAPSHOT_DIR / "documents_page_mobile.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        assert screenshot_path.exists()


class TestComponentSnapshots:
    """Capture snapshots of specific components."""
    
    def test_navigation_bar_snapshot(self, page: Page):
        """Capture navigation bar."""
        page.goto(BASE_URL)
        
        nav = page.locator("nav")
        screenshot_path = SNAPSHOT_DIR / "navigation_bar.png"
        nav.screenshot(path=str(screenshot_path))
        
        assert screenshot_path.exists()
        
    def test_stat_cards_snapshot(self, page: Page):
        """Capture stat cards from dashboard."""
        page.goto(BASE_URL)
        page.wait_for_timeout(3000)
        
        # Find stat cards container
        stats = page.locator(".grid").first
        screenshot_path = SNAPSHOT_DIR / "stat_cards.png"
        stats.screenshot(path=str(screenshot_path))
        
        assert screenshot_path.exists()
        
    def test_documents_table_snapshot(self, page: Page):
        """Capture documents table."""
        page.goto(f"{BASE_URL}/documents")
        page.wait_for_timeout(3000)
        
        table = page.locator("table")
        screenshot_path = SNAPSHOT_DIR / "documents_table.png"
        table.screenshot(path=str(screenshot_path))
        
        assert screenshot_path.exists()
        
    def test_upload_drop_zone_snapshot(self, page: Page):
        """Capture upload drop zone."""
        page.goto(f"{BASE_URL}/upload")
        
        drop_zone = page.locator("#drop-zone")
        screenshot_path = SNAPSHOT_DIR / "upload_drop_zone.png"
        drop_zone.screenshot(path=str(screenshot_path))
        
        assert screenshot_path.exists()


class TestInteractionSnapshots:
    """Capture snapshots during interactions."""
    
    def test_hover_state_navigation(self, page: Page):
        """Capture navigation hover state."""
        page.goto(BASE_URL)
        
        # Hover over documents link
        documents_link = page.locator("nav >> text=Documents")
        documents_link.hover()
        page.wait_for_timeout(500)
        
        nav = page.locator("nav")
        screenshot_path = SNAPSHOT_DIR / "nav_hover_state.png"
        nav.screenshot(path=str(screenshot_path))
        
        assert screenshot_path.exists()
        
    def test_search_input_focus(self, page: Page):
        """Capture search input when focused."""
        page.goto(f"{BASE_URL}/documents")
        page.wait_for_timeout(2000)
        
        # Focus search input
        search_input = page.locator("#search-input")
        search_input.click()
        page.wait_for_timeout(500)
        
        # Capture filter section
        filters = page.locator(".card").first
        screenshot_path = SNAPSHOT_DIR / "search_focused.png"
        filters.screenshot(path=str(screenshot_path))
        
        assert screenshot_path.exists()


@pytest.fixture(scope="session", autouse=True)
def create_snapshot_dir():
    """Create snapshot directory before tests."""
    SNAPSHOT_DIR.mkdir(exist_ok=True, parents=True)
    yield
    
    # Print snapshot summary
    snapshots = list(SNAPSHOT_DIR.glob("*"))
    print(f"\n\n{'='*60}")
    print(f"SNAPSHOT SUMMARY")
    print(f"{'='*60}")
    print(f"Total snapshots created: {len(snapshots)}")
    print(f"Snapshot location: {SNAPSHOT_DIR.absolute()}")
    print(f"{'='*60}\n")
