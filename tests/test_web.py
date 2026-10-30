from importlib.metadata import version

from starlette.testclient import TestClient

from smoked_paprika.web import create_app


def test_healthz_reports_version():
    response = TestClient(create_app()).get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": version("smoked-paprika")}


def test_no_mcp_endpoint_without_auth():
    assert TestClient(create_app()).post("/mcp").status_code == 404
