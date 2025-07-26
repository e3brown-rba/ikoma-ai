"""Test plans page functionality."""

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app


class TestPlansPage:
    """Test plans page functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)

    def test_plans_page_loads(self):
        """Test that the plans page loads correctly."""
        response = self.client.get("/plans")
        assert response.status_code == 200
        assert "Agent Plans" in response.text
        assert "No Active Plans" in response.text  # Default state

    def test_plans_page_has_clean_layout(self):
        """Test that the plans page has a clean layout without clutter."""
        response = self.client.get("/plans")
        content = response.text

        # Should not contain any large graphics or clutter
        assert "background-image" not in content
        assert "background: url" not in content

        # Should contain proper dashboard structure
        assert "Ikoma AI" in content
        assert "Navigation" in content
        assert "Plans" in content

    def test_plans_page_redirect(self):
        """Test that /plans-page redirects to /plans."""
        response = self.client.get("/plans-page", follow_redirects=False)
        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == "/plans"

    def test_plans_page_with_plans(self):
        """Test that plans page shows plans when they exist."""
        # This would require setting up test data
        # For now, just verify the page loads
        response = self.client.get("/plans")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__])
