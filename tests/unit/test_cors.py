"""CORS: this API has no auth, so its allowlist *is* the access control.
Covers the two trusted origin shapes (local dev server, the project's
GitHub Pages deployment) and confirms the Private Network Access preflight
header is answered -- without it, a public HTTPS origin's request to this
loopback API hangs rather than failing visibly (see api/app.py)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from structnode.api import app

client = TestClient(app)


def _preflight(origin: str, *, private_network: bool = False) -> object:
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
    }
    if private_network:
        headers["Access-Control-Request-Private-Network"] = "true"
    return client.options("/capabilities", headers=headers)


def test_localhost_origin_allowed() -> None:
    resp = _preflight("http://localhost:5174")
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5174"


def test_127_0_0_1_origin_allowed() -> None:
    resp = _preflight("http://127.0.0.1:5174")
    assert resp.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"


def test_github_pages_origin_allowed() -> None:
    resp = _preflight("https://yj-chen0830.github.io")
    assert resp.headers["access-control-allow-origin"] == "https://yj-chen0830.github.io"


def test_private_network_preflight_is_answered() -> None:
    resp = _preflight("https://yj-chen0830.github.io", private_network=True)
    assert resp.headers.get("access-control-allow-private-network") == "true"


def test_untrusted_origin_rejected() -> None:
    resp = _preflight("https://evil.example.com")
    assert "access-control-allow-origin" not in resp.headers
