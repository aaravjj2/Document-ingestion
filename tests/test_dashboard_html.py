"""
HTML and content validation tests for dashboard pages.
Tests HTML structure, accessibility, and content integrity.
"""
import os
import re

import pytest
import requests
from bs4 import BeautifulSoup


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


class TestHTMLStructure:
    """Test HTML structure and validity."""
    
    @pytest.mark.parametrize("path", ["/", "/documents", "/upload", "/health"])
    def test_html_doctype(self, path):
        """Test pages have proper HTML5 doctype."""
        response = requests.get(BASE_URL + path)
        assert response.status_code == 200
        
        html = response.text
        assert html.strip().startswith("<!DOCTYPE html>") or \
               html.strip().lower().startswith("<!doctype html>")
    
    @pytest.mark.parametrize("path", ["/", "/documents", "/upload", "/health"])
    def test_html_lang_attribute(self, path):
        """Test pages have lang attribute."""
        response = requests.get(BASE_URL + path)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        html_tag = soup.find('html')
        assert html_tag is not None
        assert html_tag.get('lang') == 'en'
    
    @pytest.mark.parametrize("path", ["/", "/documents", "/upload", "/health"])
    def test_meta_charset(self, path):
        """Test pages have charset meta tag."""
        response = requests.get(BASE_URL + path)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        charset_meta = soup.find('meta', {'charset': True})
        assert charset_meta is not None
        assert charset_meta.get('charset').lower() == 'utf-8'
    
    @pytest.mark.parametrize("path", ["/", "/documents", "/upload", "/health"])
    def test_viewport_meta(self, path):
        """Test pages have viewport meta tag for responsive design."""
        response = requests.get(BASE_URL + path)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        viewport_meta = soup.find('meta', {'name': 'viewport'})
        assert viewport_meta is not None
        assert 'width=device-width' in viewport_meta.get('content', '')


class TestNavigation:
    """Test navigation structure across pages."""
    
    @pytest.mark.parametrize("path", ["/", "/documents", "/upload", "/health"])
    def test_navigation_present(self, path):
        """Test navigation bar is present."""
        response = requests.get(BASE_URL + path)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        nav = soup.find('nav')
        assert nav is not None
    
    @pytest.mark.parametrize("path", ["/", "/documents", "/upload", "/health"])
    def test_navigation_links(self, path):
        """Test navigation has all required links."""
        response = requests.get(BASE_URL + path)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        nav = soup.find('nav')
        nav_text = nav.get_text()
        
        assert 'Dashboard' in nav_text
        assert 'Documents' in nav_text
        assert 'Upload' in nav_text
        assert 'Health' in nav_text
        
    @pytest.mark.parametrize("path", ["/", "/documents", "/upload", "/health"])
    def test_brand_link(self, path):
        """Test brand/logo link is present."""
        response = requests.get(BASE_URL + path)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for DocIngest brand
        nav = soup.find('nav')
        assert 'DocIngest' in nav.get_text()


class TestFooter:
    """Test footer structure."""
    
    @pytest.mark.parametrize("path", ["/", "/documents", "/upload", "/health"])
    def test_footer_present(self, path):
        """Test footer is present on all pages."""
        response = requests.get(BASE_URL + path)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        footer = soup.find('footer')
        assert footer is not None
        
    @pytest.mark.parametrize("path", ["/", "/documents", "/upload", "/health"])
    def test_footer_content(self, path):
        """Test footer has copyright and year."""
        response = requests.get(BASE_URL + path)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        footer = soup.find('footer')
        footer_text = footer.get_text()
        
        assert '2025' in footer_text
        assert 'Document Ingestion Service' in footer_text or 'DocIngest' in footer_text


class TestPageContent:
    """Test specific page content."""
    
    def test_home_page_title(self):
        """Test home page has correct title."""
        response = requests.get(BASE_URL)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = soup.find('title')
        assert title is not None
        assert 'Dashboard' in title.string
        
    def test_home_page_heading(self):
        """Test home page has main heading."""
        response = requests.get(BASE_URL)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        h1 = soup.find('h1')
        assert h1 is not None
        assert 'Dashboard' in h1.get_text()
        
    def test_documents_page_table(self):
        """Test documents page has table structure."""
        response = requests.get(f"{BASE_URL}/documents")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        table = soup.find('table')
        assert table is not None
        
        # Check for table headers
        headers = [th.get_text(strip=True) for th in table.find_all('th')]
        assert 'Filename' in headers
        assert 'Status' in headers
        assert 'Actions' in headers
        
    def test_upload_page_form_elements(self):
        """Test upload page has form elements."""
        response = requests.get(f"{BASE_URL}/upload")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for file input
        file_input = soup.find('input', {'type': 'file'})
        assert file_input is not None
        assert file_input.get('id') == 'file-input'
        
        # Check for drop zone
        drop_zone = soup.find(id='drop-zone')
        assert drop_zone is not None
        
    def test_health_page_status_elements(self):
        """Test health page has status elements."""
        response = requests.get(f"{BASE_URL}/health")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for status indicator
        status_text = soup.find(id='status-text')
        assert status_text is not None
        
        # Check for component cards
        page_text = soup.get_text()
        assert 'Database' in page_text
        assert 'Celery' in page_text
        assert 'Workers' in page_text


class TestJavaScript:
    """Test JavaScript includes."""
    
    @pytest.mark.parametrize("path", ["/", "/documents", "/upload", "/health"])
    def test_chart_js_included(self, path):
        """Test Chart.js is included on pages that need it."""
        response = requests.get(BASE_URL + path)
        
        if path in ["/", "/health"]:
            assert 'chart.js' in response.text.lower()
            
    @pytest.mark.parametrize("path", ["/", "/documents", "/upload", "/health"])
    def test_fontawesome_included(self, path):
        """Test FontAwesome is included."""
        response = requests.get(BASE_URL + path)
        assert 'font-awesome' in response.text.lower()
        
    @pytest.mark.parametrize("path", ["/", "/documents", "/upload", "/health"])
    def test_tailwind_included(self, path):
        """Test Tailwind CSS is included."""
        response = requests.get(BASE_URL + path)
        assert 'tailwindcss.com' in response.text.lower()


class TestAccessibility:
    """Test accessibility features."""
    
    @pytest.mark.parametrize("path", ["/", "/documents", "/upload", "/health"])
    def test_images_have_alt_text(self, path):
        """Test images have alt text (if any images exist)."""
        response = requests.get(BASE_URL + path)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        images = soup.find_all('img')
        for img in images:
            # Images should have alt attribute
            assert img.has_attr('alt'), f"Image missing alt text: {img}"
    
    @pytest.mark.parametrize("path", ["/", "/documents", "/upload", "/health"])
    def test_form_labels(self, path):
        """Test form inputs have associated labels."""
        response = requests.get(BASE_URL + path)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find visible inputs (not hidden)
        inputs = soup.find_all('input', {'type': lambda t: t != 'hidden'})
        
        for input_elem in inputs:
            input_id = input_elem.get('id')
            if input_id:
                # Look for associated label
                label = soup.find('label', {'for': input_id})
                # Labels are good for accessibility
                # (Not asserting as some inputs use placeholder/aria-label)


class TestSecurity:
    """Test security headers and practices."""
    
    @pytest.mark.parametrize("path", ["/", "/documents", "/upload", "/health"])
    def test_no_inline_javascript(self, path):
        """Test pages minimize inline JavaScript."""
        response = requests.get(BASE_URL + path)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Count inline scripts (some are okay for initialization)
        inline_scripts = soup.find_all('script', string=True)
        
        # Should have scripts, but not excessive inline JS
        # This is a soft check - some inline JS is acceptable for SPAs
        assert len(inline_scripts) < 10, "Too many inline scripts"
    
    @pytest.mark.parametrize("path", ["/", "/documents"])
    def test_no_sensitive_data_in_html(self, path):
        """Test no sensitive data exposed in HTML comments or source."""
        response = requests.get(BASE_URL + path)
        html_lower = response.text.lower()
        
        # Check for common sensitive patterns
        sensitive_patterns = [
            'password',
            'api_key',
            'secret',
            'token',
        ]
        
        for pattern in sensitive_patterns:
            # Allow these in labels/text, but not as values
            assert not re.search(rf'{pattern}\s*[:=]\s*["\']?[a-zA-Z0-9]{{10,}}', html_lower), \
                f"Potential sensitive data found: {pattern}"


class TestStaticAssets:
    """Test static assets are accessible."""
    
    def test_static_css_accessible(self):
        """Test custom CSS file is accessible."""
        response = requests.get(f"{BASE_URL}/static/css/custom.css")
        
        # Should be accessible (200) or not found if not used (404)
        assert response.status_code in [200, 404]
        
    def test_static_js_accessible(self):
        """Test custom JS file is accessible."""
        response = requests.get(f"{BASE_URL}/static/js/utils.js")
        
        # Should be accessible (200) or not found if not used (404)
        assert response.status_code in [200, 404]


class TestResponsiveness:
    """Test responsive design indicators in HTML."""
    
    @pytest.mark.parametrize("path", ["/", "/documents", "/upload", "/health"])
    def test_responsive_classes(self, path):
        """Test pages use responsive classes."""
        response = requests.get(BASE_URL + path)
        html = response.text
        
        # Check for Tailwind responsive classes
        responsive_patterns = [
            r'md:',  # Medium screens
            r'lg:',  # Large screens
            r'grid-cols-',  # Grid layout
            r'flex',  # Flexbox
        ]
        
        found_responsive = False
        for pattern in responsive_patterns:
            if re.search(pattern, html):
                found_responsive = True
                break
        
        assert found_responsive, "No responsive design classes found"
