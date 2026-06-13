from collections.abc import Generator

import pytest
from fastapi import FastAPI

import epc.api as api_module
import epc.traffic as traffic_module
from epc.db import EPCRepository
from main import app as fastapi_app


@pytest.fixture(autouse=True)
def reset_epc_singletons() -> Generator[None, None, None]:
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
    return EPCRepository(str(tmp_path / "epc_test.db"))


@pytest.fixture
def app(repo: EPCRepository) -> Generator[FastAPI, None, None]:
    fastapi_app.dependency_overrides[api_module.get_repo] = lambda: repo
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI):
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client
