"""
End-to-End tests for the Dashboard UI using Playwright.
Tests user interactions, page loads, navigation, and UI functionality.
"""
import os
import time
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


class TestDashboardNavigation:
    """Test navigation and page loading across the dashboard."""
    
    def test_home_page_loads(self, page: Page):
        """Test that the home dashboard page loads successfully."""
        page.goto(BASE_URL)
        
        # Check page title
        expect(page).to_have_title("Dashboard - Document Ingestion")
        
        # Check main heading
        expect(page.locator("h1")).to_contain_text("Dashboard")
        
        # Check navigation bar exists
        expect(page.locator("nav")).to_be_visible()
        expect(page.locator("nav")).to_contain_text("DocIngest")
        
    def test_navigation_links_present(self, page: Page):
        """Test that all navigation links are present."""
        page.goto(BASE_URL)
        
        # Check all nav links
        nav = page.locator("nav")
        expect(nav.locator("text=Dashboard")).to_be_visible()
        expect(nav.locator("text=Documents")).to_be_visible()
        expect(nav.locator("text=Upload")).to_be_visible()
        expect(nav.locator("text=Health")).to_be_visible()
        expect(nav.locator("text=API Docs")).to_be_visible()
        
    def test_navigate_to_documents_page(self, page: Page):
        """Test navigation to documents page."""
        page.goto(BASE_URL)
        
        # Click documents link
        page.click("text=Documents")
        page.wait_for_load_state("networkidle")
        
        # Verify we're on documents page
        expect(page).to_have_url(f"{BASE_URL}/documents")
        expect(page.locator("h1")).to_contain_text("Documents")
        
    def test_navigate_to_upload_page(self, page: Page):
        """Test navigation to upload page."""
        page.goto(BASE_URL)
        
        # Click upload link
        page.click("text=Upload")
        page.wait_for_load_state("networkidle")
        
        # Verify we're on upload page
        expect(page).to_have_url(f"{BASE_URL}/upload")
        expect(page.locator("h1")).to_contain_text("Upload Document")
        
    def test_navigate_to_health_page(self, page: Page):
        """Test navigation to health page."""
        page.goto(BASE_URL)
        
        # Click health link
        page.click("text=Health")
        page.wait_for_load_state("networkidle")
        
        # Verify we're on health page
        expect(page).to_have_url(f"{BASE_URL}/health")
        expect(page.locator("h1")).to_contain_text("System Health")


class TestDashboardHomePage:
    """Test home dashboard functionality."""
    
    def test_stat_cards_present(self, page: Page):
        """Test that all stat cards are displayed."""
        page.goto(BASE_URL)
        page.wait_for_timeout(2000)  # Wait for API data to load
        
        # Check for stat card elements
        expect(page.locator("text=Total Documents")).to_be_visible()
        expect(page.locator("text=Completed")).to_be_visible()
        expect(page.locator("text=Pending")).to_be_visible()
        expect(page.locator("text=Failed")).to_be_visible()
        
    def test_charts_render(self, page: Page):
        """Test that charts are rendered on the page."""
        page.goto(BASE_URL)
        page.wait_for_timeout(2000)
        
        # Check for chart canvases
        expect(page.locator("#statusChart")).to_be_visible()
        expect(page.locator("#typeChart")).to_be_visible()
        
    def test_recent_documents_section(self, page: Page):
        """Test recent documents section."""
        page.goto(BASE_URL)
        page.wait_for_timeout(2000)
        
        # Check recent documents heading
        expect(page.locator("text=Recent Documents")).to_be_visible()
        
        # Check for documents container
        expect(page.locator("#recent-documents")).to_be_visible()
        
    def test_view_all_documents_link(self, page: Page):
        """Test the 'View All' link navigates to documents page."""
        page.goto(BASE_URL)
        
        # Click view all link
        page.click("text=View All")
        page.wait_for_load_state("networkidle")
        
        # Verify navigation
        expect(page).to_have_url(f"{BASE_URL}/documents")


class TestDocumentsPage:
    """Test documents list page functionality."""
    
    def test_documents_page_loads(self, page: Page):
        """Test documents page loads correctly."""
        page.goto(f"{BASE_URL}/documents")
        page.wait_for_timeout(2000)
        
        # Check page title and heading
        expect(page).to_have_title("Documents - Document Ingestion")
        expect(page.locator("h1")).to_contain_text("Documents")
        
    def test_upload_button_present(self, page: Page):
        """Test upload button is present on documents page."""
        page.goto(f"{BASE_URL}/documents")
        
        # Check for upload button
        upload_btn = page.locator("text=Upload Document")
        expect(upload_btn).to_be_visible()
        
    def test_filter_controls_present(self, page: Page):
        """Test filter controls are present."""
        page.goto(f"{BASE_URL}/documents")
        
        # Check for filter elements
        expect(page.locator("#search-input")).to_be_visible()
        expect(page.locator("#status-filter")).to_be_visible()
        expect(page.locator("#type-filter")).to_be_visible()
        expect(page.locator("text=Apply Filters")).to_be_visible()
        
    def test_documents_table_present(self, page: Page):
        """Test documents table is rendered."""
        page.goto(f"{BASE_URL}/documents")
        page.wait_for_timeout(2000)
        
        # Check for table
        table = page.locator("table")
        expect(table).to_be_visible()
        
        # Check for table headers
        expect(page.locator("th >> text=Filename")).to_be_visible()
        expect(page.locator("th >> text=Type")).to_be_visible()
        expect(page.locator("th >> text=Status")).to_be_visible()
        expect(page.locator("th >> text=Uploaded")).to_be_visible()
        expect(page.locator("th >> text=Confidence")).to_be_visible()
        expect(page.locator("th >> text=Actions")).to_be_visible()
        
    def test_search_input_works(self, page: Page):
        """Test search input functionality."""
        page.goto(f"{BASE_URL}/documents")
        page.wait_for_timeout(2000)
        
        # Type in search box
        search_input = page.locator("#search-input")
        search_input.fill("invoice")
        
        # Verify input has value
        expect(search_input).to_have_value("invoice")
        
    def test_status_filter_options(self, page: Page):
        """Test status filter has correct options."""
        page.goto(f"{BASE_URL}/documents")
        
        # Check status filter options
        status_filter = page.locator("#status-filter")
        expect(status_filter).to_be_visible()
        
        # Get options
        options = page.locator("#status-filter option").all_text_contents()
        assert "All Statuses" in options
        assert "Pending" in options
        assert "Processing" in options
        assert "Completed" in options
        assert "Failed" in options


class TestUploadPage:
    """Test upload page functionality."""
    
    def test_upload_page_loads(self, page: Page):
        """Test upload page loads correctly."""
        page.goto(f"{BASE_URL}/upload")
        
        # Check page title and heading
        expect(page).to_have_title("Upload Document - Document Ingestion")
        expect(page.locator("h1")).to_contain_text("Upload Document")
        
    def test_drop_zone_present(self, page: Page):
        """Test drag and drop zone is present."""
        page.goto(f"{BASE_URL}/upload")
        
        # Check drop zone
        drop_zone = page.locator("#drop-zone")
        expect(drop_zone).to_be_visible()
        expect(page.locator("text=Drag & Drop your document here")).to_be_visible()
        
    def test_file_input_present(self, page: Page):
        """Test file input is present."""
        page.goto(f"{BASE_URL}/upload")
        
        # Check file input (hidden but exists)
        file_input = page.locator("#file-input")
        assert file_input.count() > 0
        
    def test_upload_tips_present(self, page: Page):
        """Test upload tips section is present."""
        page.goto(f"{BASE_URL}/upload")
        
        # Check tips section
        expect(page.locator("text=Tips for Best Results")).to_be_visible()
        expect(page.locator("text=Ensure documents are clear")).to_be_visible()
        
    def test_supported_formats_displayed(self, page: Page):
        """Test supported formats are displayed."""
        page.goto(f"{BASE_URL}/upload")
        
        # Check for supported formats text
        expect(page.locator("text=PNG, JPEG, PDF, TIFF")).to_be_visible()
        
    def test_upload_button_initially_disabled(self, page: Page):
        """Test upload button is disabled until file is selected."""
        page.goto(f"{BASE_URL}/upload")
        
        # Check button is disabled
        upload_btn = page.locator("#upload-btn")
        expect(upload_btn).to_be_disabled()


class TestHealthPage:
    """Test health monitoring page functionality."""
    
    def test_health_page_loads(self, page: Page):
        """Test health page loads correctly."""
        page.goto(f"{BASE_URL}/health")
        page.wait_for_timeout(2000)
        
        # Check page title and heading
        expect(page).to_have_title("System Health - Document Ingestion")
        expect(page.locator("h1")).to_contain_text("System Health")
        
    def test_overall_status_displayed(self, page: Page):
        """Test overall system status is displayed."""
        page.goto(f"{BASE_URL}/health")
        page.wait_for_timeout(2000)
        
        # Check for status display
        expect(page.locator("#overall-status")).to_be_visible()
        expect(page.locator("#status-text")).to_be_visible()
        
    def test_component_cards_present(self, page: Page):
        """Test component status cards are present."""
        page.goto(f"{BASE_URL}/health")
        page.wait_for_timeout(2000)
        
        # Check for component cards
        expect(page.locator("text=Database")).to_be_visible()
        expect(page.locator("text=Celery")).to_be_visible()
        expect(page.locator("text=Workers")).to_be_visible()
        
    def test_refresh_button_present(self, page: Page):
        """Test refresh button is present."""
        page.goto(f"{BASE_URL}/health")
        
        # Check refresh button
        refresh_btn = page.locator("text=Refresh")
        expect(refresh_btn).to_be_visible()
        
    def test_service_information_displayed(self, page: Page):
        """Test service information section is displayed."""
        page.goto(f"{BASE_URL}/health")
        
        # Check service info
        expect(page.locator("text=Service Information")).to_be_visible()
        expect(page.locator("text=API Version")).to_be_visible()
        expect(page.locator("text=PaddleOCR")).to_be_visible()
        expect(page.locator("text=PostgreSQL")).to_be_visible()
        expect(page.locator("text=Redis")).to_be_visible()


class TestResponsiveDesign:
    """Test responsive design at different viewport sizes."""
    
    @pytest.mark.parametrize("viewport", [
        {"width": 375, "height": 667},   # Mobile
        {"width": 768, "height": 1024},  # Tablet
        {"width": 1920, "height": 1080}, # Desktop
    ])
    def test_home_page_responsive(self, page: Page, viewport):
        """Test home page is responsive at different sizes."""
        page.set_viewport_size(viewport)
        page.goto(BASE_URL)
        page.wait_for_timeout(1000)
        
        # Check page loads and key elements visible
        expect(page.locator("h1")).to_be_visible()
        expect(page.locator("nav")).to_be_visible()
        
    @pytest.mark.parametrize("viewport", [
        {"width": 375, "height": 667},   # Mobile
        {"width": 1920, "height": 1080}, # Desktop
    ])
    def test_documents_page_responsive(self, page: Page, viewport):
        """Test documents page is responsive."""
        page.set_viewport_size(viewport)
        page.goto(f"{BASE_URL}/documents")
        page.wait_for_timeout(1000)
        
        # Check key elements
        expect(page.locator("h1")).to_be_visible()
        expect(page.locator("table")).to_be_visible()


class TestUIInteractions:
    """Test user interactions and click events."""
    
    def test_click_brand_logo_returns_home(self, page: Page):
        """Test clicking brand logo returns to home."""
        page.goto(f"{BASE_URL}/documents")
        
        # Click logo
        page.click("text=DocIngest")
        page.wait_for_load_state("networkidle")
        
        # Verify we're on home page
        expect(page).to_have_url(BASE_URL + "/")
        
    def test_footer_present(self, page: Page):
        """Test footer is present on all pages."""
        pages = ["/", "/documents", "/upload", "/health"]
        
        for path in pages:
            page.goto(BASE_URL + path)
            expect(page.locator("footer")).to_be_visible()
            expect(page.locator("footer >> text=2025")).to_be_visible()


class TestDataLoading:
    """Test that data loads correctly from API."""
    
    def test_dashboard_loads_document_count(self, page: Page):
        """Test dashboard loads and displays document count."""
        page.goto(BASE_URL)
        page.wait_for_timeout(3000)  # Wait for API call
        
        # Check that stat cards have numbers (not just dashes)
        total_docs = page.locator("#total-docs").text_content()
        assert total_docs != "-", "Total docs should load from API"
        
    def test_documents_table_loads_data(self, page: Page):
        """Test documents table loads data or shows empty state."""
        page.goto(f"{BASE_URL}/documents")
        page.wait_for_timeout(3000)
        
        # Table body should exist and have content
        tbody = page.locator("#documents-table")
        expect(tbody).to_be_visible()
        
        # Check for either data or empty state
        has_data = tbody.locator("tr").count() > 0
        assert has_data, "Documents table should have rows"
        
    def test_health_page_shows_status(self, page: Page):
        """Test health page loads and shows system status."""
        page.goto(f"{BASE_URL}/health")
        page.wait_for_timeout(3000)
        
        # Status text should be populated
        status_text = page.locator("#status-text").text_content()
        assert status_text != "Checking...", "Health status should load"
        assert "System" in status_text or "Operational" in status_text or "Issues" in status_text


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_document_id_shows_error(self, page: Page):
        """Test accessing invalid document ID shows error."""
        page.goto(f"{BASE_URL}/documents/invalid-id-12345")
        page.wait_for_load_state("networkidle")
        
        # Should show error page or error message
        # Check for either 404 text or error indicator
        page_content = page.content()
        assert "404" in page_content or "not found" in page_content.lower() or "Error" in page_content


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for tests."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }
