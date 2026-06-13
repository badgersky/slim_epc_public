"""Shared pytest fixtures for slim_epc_public tests.

The fixtures keep tests isolated from the real local ``epc.db`` file and from
module-level singletons used by the FastAPI app and traffic manager.
"""

from collections.abc import Generator

import pytest
from fastapi import FastAPI

import epc.api as api_module
import epc.traffic as traffic_module
from epc.db import EPCRepository
from main import app as fastapi_app


@pytest.fixture(autouse=True)
def reset_epc_singletons() -> Generator[None, None, None]:
    """Reset global repo/traffic singletons before and after every test.

    This prevents state leakage between tests, especially because
    ``traffic_manager`` stores background tasks and ``api.get_repo`` uses a
    module-level repository singleton.
    """
    manager = traffic_module.traffic_manager
    if manager is not None:
        manager.stop_all()

    traffic_module.traffic_manager = None
    api_module._repo_singleton = None
    fastapi_app.dependency_overrides.clear()

    yield

    manager = traffic_module.traffic_manager
    if manager is not None:
        manager.stop_all()

    traffic_module.traffic_manager = None
    api_module._repo_singleton = None
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def repo(tmp_path) -> EPCRepository:
    """Return a fresh SQLite repository for a single test."""
    return EPCRepository(str(tmp_path / "epc_test.db"))


@pytest.fixture
def app(repo: EPCRepository) -> Generator[FastAPI, None, None]:
    """Return the FastAPI app configured to use the test repository."""
    fastapi_app.dependency_overrides[api_module.get_repo] = lambda: repo
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI):
    """Return a TestClient for API contract tests.

    Imported lazily so model/repository unit tests do not require TestClient
    unless this fixture is actually used.
    """
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client