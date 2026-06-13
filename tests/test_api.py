from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from epc import api
from epc.models import (
    AddBearerRequest,
    AttachUERequest,
    BearerConfig,
    StartTrafficRequest,
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


# ----------- DELETE /ues/{id} - detach_ue ---------------------

class TestDetachUE:
    def test_success(self, mock_repo):
        resp = api.detach_ue(3, mock_repo)

        mock_repo.detach_ue.assert_called_once_with(3)
        assert resp.status == "detached"
        assert resp.ue_id == 3

    def test_unknown_maps_to_400(self, mock_repo):
        mock_repo.detach_ue.side_effect = ValueError("UE not found")

        with pytest.raises(HTTPException) as exc:
            api.detach_ue(3, mock_repo)

        assert exc.value.status_code == 400


# ----------- POST /ues/{id}/bearers - add_bearer ---------------------

class TestAddBearer:
    def test_success(self, mock_repo):
        resp = api.add_bearer(1, AddBearerRequest(bearer_id=3), mock_repo)

        mock_repo.add_bearer.assert_called_once_with(1, 3)
        assert resp.status == "bearer_added"
        assert (resp.ue_id, resp.bearer_id) == (1, 3)

    def test_duplicate_maps_to_400(self, mock_repo):
        mock_repo.add_bearer.side_effect = ValueError("Bearer already exists")

        with pytest.raises(HTTPException) as exc:
            api.add_bearer(1, AddBearerRequest(bearer_id=3), mock_repo)

        assert exc.value.status_code == 400

    def test_unknown_ue_maps_to_400(self, mock_repo):
        mock_repo.add_bearer.side_effect = ValueError("UE not found")

        with pytest.raises(HTTPException) as exc:
            api.add_bearer(99, AddBearerRequest(bearer_id=3), mock_repo)

        assert exc.value.status_code == 400


# ----------- DELETE /ues/{id}/bearers/{bid} - delete_bearer ---------------------

class TestDeleteBearer:
    def test_unknown_ue_maps_to_400(self, mock_repo, tm):
        mock_repo.get_ue.side_effect = ValueError("UE not found")

        with pytest.raises(HTTPException) as exc:
            api.delete_bearer(99, 3, mock_repo)

        assert exc.value.status_code == 400

    def test_bearer_not_present_maps_to_400(self, mock_repo, tm):
        mock_repo.get_ue.return_value = make_ue(1)

        with pytest.raises(HTTPException) as exc:
            api.delete_bearer(1, 4, mock_repo)

        assert exc.value.status_code == 400
        assert "not found" in exc.value.detail.lower()

    def test_running_traffic_is_stopped_first(self, mock_repo, tm):
        mock_repo.get_ue.return_value = make_ue(1, extra_bearers=[4])
        tm.is_running.return_value = True

        resp = api.delete_bearer(1, 4, mock_repo)

        tm.stop.assert_called_once_with(1, 4)
        mock_repo.delete_bearer.assert_called_once_with(1, 4)
        assert resp.status == "bearer_deleted"

    def test_not_running_traffic_not_stopped(self, mock_repo, tm):
        mock_repo.get_ue.return_value = make_ue(1, extra_bearers=[4])
        tm.is_running.return_value = False

        api.delete_bearer(1, 4, mock_repo)

        tm.stop.assert_not_called()
        mock_repo.delete_bearer.assert_called_once_with(1, 4)

    def test_repo_value_error_maps_to_400(self, mock_repo, tm):
        mock_repo.get_ue.return_value = make_ue(1)
        mock_repo.delete_bearer.side_effect = ValueError("Cannot remove default bearer")

        with pytest.raises(HTTPException) as exc:
            api.delete_bearer(1, 9, mock_repo)

        assert exc.value.status_code == 400


# ----------- POST /ues/{id}/bearers/{bid}/traffic - start_traffic ---------------------

class TestStartTraffic:
    def test_success_configures_bearer(self, mock_repo, tm):
        mock_repo.get_ue.return_value = make_ue(1)
        body = StartTrafficRequest(protocol="tcp", Mbps=2)

        resp = api.start_traffic(1, 9, body, mock_repo)

        saved = mock_repo.update_bearer.call_args.args[1]
        assert saved.protocol == "tcp"
        assert saved.target_bps == 2_000_000
        assert saved.active is True

        tm.start.assert_called_once()
        assert resp.status == "traffic_started"
        assert resp.target_bps == 2_000_000

    def test_initial_stats_created_when_absent(self, mock_repo, tm):
        mock_repo.get_ue.return_value = make_ue(1)

        api.start_traffic(
            1,
            9,
            StartTrafficRequest(protocol="tcp", kbps=100),
            mock_repo,
        )

        mock_repo.update_stats.assert_called_once()
        written = mock_repo.update_stats.call_args.args[1]
        assert written.bearer_id == 9
        assert written.ue_id == 1
        assert written.protocol == "tcp"
        assert written.target_bps == 100_000

    def test_no_initial_stats_when_already_present(self, mock_repo, tm):
        ue = make_ue(1, stats=[stats_for(bearer_id=9, ue_id=1)])
        mock_repo.get_ue.return_value = ue

        api.start_traffic(
            1,
            9,
            StartTrafficRequest(protocol="tcp", Mbps=1),
            mock_repo,
        )

        mock_repo.update_stats.assert_not_called()

    def test_unknown_ue_maps_to_400(self, mock_repo, tm):
        mock_repo.get_ue.side_effect = ValueError("UE not found")

        with pytest.raises(HTTPException) as exc:
            api.start_traffic(
                1,
                9,
                StartTrafficRequest(protocol="tcp", Mbps=1),
                mock_repo,
            )

        assert exc.value.status_code == 400

    def test_unknown_bearer_maps_to_400(self, mock_repo, tm):
        mock_repo.get_ue.return_value = make_ue(1)

        with pytest.raises(HTTPException) as exc:
            api.start_traffic(
                1,
                4,
                StartTrafficRequest(protocol="tcp", Mbps=1),
                mock_repo,
            )

        assert exc.value.status_code == 400
        assert "not found" in exc.value.detail.lower()

    def test_manager_value_error_maps_to_400(self, mock_repo, tm):
        mock_repo.get_ue.return_value = make_ue(1)
        tm.start.side_effect = ValueError("Traffic already running")

        with pytest.raises(HTTPException) as exc:
            api.start_traffic(
                1,
                9,
                StartTrafficRequest(protocol="tcp", Mbps=1),
                mock_repo,
            )

        assert exc.value.status_code == 400

    @pytest.mark.parametrize(
        "body, expected_bps",
        [
            (StartTrafficRequest(protocol="tcp", Mbps=5), 5_000_000),
            (StartTrafficRequest(protocol="udp", kbps=250), 250_000),
            (StartTrafficRequest(protocol="tcp", bps=42), 42),
        ],
    )
    def test_target_bps_in_response(self, mock_repo, tm, body, expected_bps):
        mock_repo.get_ue.return_value = make_ue(1)

        resp = api.start_traffic(1, 9, body, mock_repo)

        assert resp.target_bps == expected_bps

# ----------- DELETE /ues/{id}/bearers/{bid}/traffic - stop_traffic ---------------------

class TestStopTraffic:
    def test_success_marks_inactive(self, mock_repo, tm):
        mock_repo.get_ue.return_value = make_ue(1)

        resp = api.stop_traffic(1, 9, mock_repo)

        tm.stop.assert_called_once_with(1, 9)
        saved = mock_repo.update_bearer.call_args.args[1]
        assert saved.active is False
        assert resp.status == "traffic_stopped"

    def test_unknown_ue_maps_to_400(self, mock_repo, tm):
        mock_repo.get_ue.side_effect = ValueError("UE not found")

        with pytest.raises(HTTPException) as exc:
            api.stop_traffic(1, 9, mock_repo)

        assert exc.value.status_code == 400

    def test_unknown_bearer_maps_to_400(self, mock_repo, tm):
        mock_repo.get_ue.return_value = make_ue(1)

        with pytest.raises(HTTPException) as exc:
            api.stop_traffic(1, 4, mock_repo)

        assert exc.value.status_code == 400