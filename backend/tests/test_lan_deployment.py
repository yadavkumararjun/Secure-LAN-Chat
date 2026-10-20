import os
import sys
import logging
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.websocket.manager import ws_manager

# Ensure root dir is available to import run_server helpers
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from run_server import get_local_lan_ips


def test_spa_index_served_on_html_accept():
    """Verify that browser clients requesting HTML at GET / receive the single-origin SPA index.html."""
    with TestClient(app) as client:
        res = client.get("/", headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
        assert res.status_code == 200
        assert "text/html" in res.headers.get("content-type", "")
        # Verify compiled root container is present
        assert '<div id="root">' in res.text
        # Verify no external CDN fonts are linked
        assert "fonts.googleapis.com" not in res.text


def test_api_root_json_served_on_api_clients():
    """Verify that non-HTML API test clients requesting GET / receive operational JSON."""
    with TestClient(app) as client:
        res = client.get("/", headers={"Accept": "application/json"})
        assert res.status_code == 200
        assert "application/json" in res.headers.get("content-type", "")
        data = res.json()
        assert data["message"] == "Secure LAN Chat API is operational"
        assert data["health_check"] == "/api/health"


def test_static_assets_served_with_correct_mime():
    """Verify that bundled JS/CSS assets in /assets are served with proper MIME types."""
    dist_dir = settings.get_absolute_frontend_dist()
    assets_dir = dist_dir / "assets"
    assert assets_dir.is_dir(), "frontend/dist/assets must exist for single-origin deployment"

    css_files = list(assets_dir.glob("*.css"))
    js_files = list(assets_dir.glob("*.js"))
    assert len(css_files) > 0, "At least one CSS bundle must exist"
    assert len(js_files) > 0, "At least one JS bundle must exist"

    with TestClient(app) as client:
        # Check CSS
        css_name = css_files[0].name
        css_res = client.get(f"/assets/{css_name}")
        assert css_res.status_code == 200
        assert "text/css" in css_res.headers.get("content-type", "")

        # Check JS
        js_name = js_files[0].name
        js_res = client.get(f"/assets/{js_name}")
        assert js_res.status_code == 200
        assert "javascript" in js_res.headers.get("content-type", "")


def test_spa_client_side_routing_fallback():
    """Verify that deep paths (e.g. /chat, /login) fall back to index.html for client-side routing."""
    with TestClient(app) as client:
        res = client.get("/chat", headers={"Accept": "text/html"})
        assert res.status_code == 200
        assert "text/html" in res.headers.get("content-type", "")
        assert '<div id="root">' in res.text


def test_nonexistent_api_route_returns_404_json():
    """Verify that invalid /api/ routes return a 404 JSON error instead of falling back to SPA HTML."""
    with TestClient(app) as client:
        res = client.get("/api/nonexistent_endpoint")
        assert res.status_code == 404
        assert "application/json" in res.headers.get("content-type", "")
        data = res.json()
        assert "error" in data or "detail" in data


def test_websocket_lan_ip_origins_allowed():
    """Verify that ws_manager allows private LAN IP origins across RFC 1918 subnets and rejects public origins."""
    # 1. Private LAN subnets (must be permitted)
    assert ws_manager.is_origin_allowed("http://192.168.1.100:8000") is True
    assert ws_manager.is_origin_allowed("http://192.168.0.25:8000") is True
    assert ws_manager.is_origin_allowed("http://10.0.1.5:8000") is True
    assert ws_manager.is_origin_allowed("http://172.16.235.234:8000") is True
    assert ws_manager.is_origin_allowed("https://192.168.1.50:8443") is True
    assert ws_manager.is_origin_allowed("http://localhost:5173") is True

    # 2. Public / Untrusted origins (must be rejected to prevent CSWSH)
    assert ws_manager.is_origin_allowed("http://evil-attacker.com") is False
    assert ws_manager.is_origin_allowed("https://phishing-site.org:8000") is False
    assert ws_manager.is_origin_allowed("http://8.8.8.8:8000") is False


def test_local_lan_ip_detection():
    """Verify that get_local_lan_ips correctly detects valid non-empty IPv4 addresses."""
    ips = get_local_lan_ips()
    assert isinstance(ips, list)
    assert len(ips) >= 1
    for ip in ips:
        parts = ip.split(".")
        assert len(parts) == 4
        assert all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def test_server_logs_do_not_leak_passwords_or_tokens(caplog):
    """Verify that registration and authentication events do not log plaintext passwords or session tokens."""
    import uuid
    caplog.set_level(logging.DEBUG)
    with TestClient(app) as client:
        secret_password = "SuperSecretPassword123!"
        username = f"log_safe_{uuid.uuid4().hex[:8]}"
        res = client.post(
            "/api/auth/register",
            json={"username": username, "password": secret_password, "display_name": "Log Safe User"},
        )
        assert res.status_code == 201

        login_res = client.post(
            "/api/auth/login",
            json={"username": username, "password": secret_password},
        )
        assert login_res.status_code == 200

        # Check all captured log records
        full_logs = "\n".join(record.message for record in caplog.records)
        assert secret_password not in full_logs, "Plaintext password must NEVER appear in server logs!"
