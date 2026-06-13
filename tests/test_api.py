from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from epc import api
from epc.models import (
    AttachUERequest,
    BearerConfig,
    ThroughputStats,
    UEState,
)


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def tm(monkeypatch):
    manager = MagicMock()
    manager.is_running.return_value = False
    monkeypatch.setattr(api, "get_traffic_manager", lambda r: manager)
    return manager


def make_ue(ue_id=1, extra_bearers=(), stats=()):
    """UEState z domyślnym bearerem 9 (jak po realnym attach)."""
    state = UEState(ue_id=ue_id)
    state.bearers[9] = BearerConfig(bearer_id=9)

    for b in extra_bearers:
        state.bearers[b] = BearerConfig(bearer_id=b)

    for s in stats:
        state.stats[s.bearer_id] = s

    return state


def stats_for(
    bearer_id=9,
    ue_id=1,
    tx=0,
    rx=0,
    start_ts=None,
    last_ts=None,
    protocol=None,
    target_bps=None,
):
    return ThroughputStats(
        bearer_id=bearer_id,
        ue_id=ue_id,
        bytes_tx=tx,
        bytes_rx=rx,
        start_ts=start_ts,
        last_update_ts=last_ts,
        protocol=protocol,
        target_bps=target_bps,
    )


# ----------- GET /ues - list_ues ---------------------

class TestListUEs:
    def test_returns_ids_from_repo(self, mock_repo):
        mock_repo.list_ues.return_value = [1, 2, 3]

        resp = api.list_ues(mock_repo)

        assert resp.ues == [1, 2, 3]

    def test_empty(self, mock_repo):
        mock_repo.list_ues.return_value = []

        resp = api.list_ues(mock_repo)

        assert resp.ues == []


# ----------- POST /ues - attach_ue ---------------------

class TestAttachUE:
    def test_success(self, mock_repo):
        resp = api.attach_ue(AttachUERequest(ue_id=5), mock_repo)

        mock_repo.attach_ue.assert_called_once_with(5)
        assert resp.status == "attached"
        assert resp.ue_id == 5

    def test_value_error_maps_to_400(self, mock_repo):
        mock_repo.attach_ue.side_effect = ValueError("UE already attached")

        with pytest.raises(HTTPException) as exc:
            api.attach_ue(AttachUERequest(ue_id=5), mock_repo)

        assert exc.value.status_code == 400
        assert exc.value.detail == "UE already attached"


# ----------- GET /ues/{id} - get_ue ---------------------

class TestGetUE:
    def test_success_returns_state(self, mock_repo):
        mock_repo.get_ue.return_value = make_ue(5)

        resp = api.get_ue(5, mock_repo)

        assert resp.ue_id == 5
        assert 9 in resp.bearers

    def test_unknown_maps_to_400(self, mock_repo):
        mock_repo.get_ue.side_effect = ValueError("UE not found")

        with pytest.raises(HTTPException) as exc:
            api.get_ue(5, mock_repo)

        assert exc.value.status_code == 400