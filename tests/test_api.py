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

# ----------- GET /ues/{id}/bearers/{bid}/traffic - get_traffic_stats ---------------------

class TestGetTrafficStats:
    def test_unknown_ue_maps_to_400(self, mock_repo, tm):
        mock_repo.get_ue.side_effect = ValueError("UE not found")

        with pytest.raises(HTTPException) as exc:
            api.get_traffic_stats(1, 9, mock_repo)

        assert exc.value.status_code == 400

    def test_no_stats_returns_zeros(self, mock_repo, tm):
        mock_repo.get_ue.return_value = make_ue(1)

        resp = api.get_traffic_stats(1, 9, mock_repo)

        assert (resp.tx_bps, resp.rx_bps, resp.duration) == (0, 0, 0)
        assert resp.protocol is None
        assert resp.target_bps is None

    def test_computes_bps_when_not_running(self, mock_repo, tm):
        s = stats_for(
            tx=1000,
            rx=500,
            start_ts=100.0,
            last_ts=102.0,
            protocol="tcp",
            target_bps=4000,
        )
        mock_repo.get_ue.return_value = make_ue(1, stats=[s])
        tm.is_running.return_value = False

        resp = api.get_traffic_stats(1, 9, mock_repo)

        assert resp.tx_bps == 4000
        assert resp.rx_bps == 2000
        assert resp.duration == pytest.approx(2.0)
        assert resp.protocol == "tcp"
        assert resp.target_bps == 4000

    def test_running_uses_now_as_window_end(self, mock_repo, tm, monkeypatch):
        s = stats_for(tx=1000, rx=0, start_ts=100.0, last_ts=100.0)
        mock_repo.get_ue.return_value = make_ue(1, stats=[s])
        tm.is_running.return_value = True
        monkeypatch.setattr(api.time, "time", lambda: 104.0)

        resp = api.get_traffic_stats(1, 9, mock_repo)

        assert resp.duration == pytest.approx(4.0)
        assert resp.tx_bps == 2000

    def test_zero_duration_returns_zero_bps(self, mock_repo, tm):
        s = stats_for(tx=1000, rx=1000, start_ts=100.0, last_ts=100.0)
        mock_repo.get_ue.return_value = make_ue(1, stats=[s])
        tm.is_running.return_value = False

        resp = api.get_traffic_stats(1, 9, mock_repo)

        assert (resp.tx_bps, resp.rx_bps) == (0, 0)
        assert resp.duration == 0

# ----------- GET /ues/stats - get_ues_stats ---------------------

class TestAggregatedStats:
    def test_scope_all_sums_across_ues(self, mock_repo, tm):
        s1 = stats_for(
            bearer_id=9,
            ue_id=1,
            tx=1000,
            rx=0,
            start_ts=100.0,
            last_ts=101.0,
        )
        s2 = stats_for(
            bearer_id=9,
            ue_id=2,
            tx=0,
            rx=2000,
            start_ts=100.0,
            last_ts=101.0,
        )
        mock_repo.list_ues.return_value = [1, 2]
        mock_repo.get_ue.side_effect = lambda uid: (
            make_ue(1, stats=[s1]) if uid == 1 else make_ue(2, stats=[s2])
        )

        resp = api.get_ues_stats(mock_repo, ue_id=None)

        assert resp.scope == "all"
        assert resp.ue_count == 2
        assert resp.bearer_count == 2
        assert resp.total_tx_bps == 8000
        assert resp.total_rx_bps == 16000
        assert resp.details is None

    def test_scope_single_ue(self, mock_repo, tm):
        s = stats_for(
            bearer_id=9,
            ue_id=1,
            tx=1000,
            rx=0,
            start_ts=100.0,
            last_ts=101.0,
        )
        mock_repo.ue_exists.return_value = True
        mock_repo.get_ue.return_value = make_ue(1, stats=[s])

        resp = api.get_ues_stats(mock_repo, ue_id=1)

        assert resp.scope == "ue:1"
        assert resp.ue_count == 1
        assert resp.total_tx_bps == 8000

    def test_unknown_ue_maps_to_400(self, mock_repo, tm):
        mock_repo.ue_exists.return_value = False

        with pytest.raises(HTTPException) as exc:
            api.get_ues_stats(mock_repo, ue_id=5)

        assert exc.value.status_code == 400

    def test_include_details_breakdown(self, mock_repo, tm):
        s = stats_for(
            bearer_id=9,
            ue_id=1,
            tx=1000,
            rx=0,
            start_ts=100.0,
            last_ts=101.0,
        )
        mock_repo.ue_exists.return_value = True
        mock_repo.get_ue.return_value = make_ue(1, stats=[s])

        resp = api.get_ues_stats(mock_repo, ue_id=1, include_details=True)

        assert resp.details == {"1": {"9": 8000}}

    def test_missing_ue_in_all_scope_is_skipped(self, mock_repo, tm):
        mock_repo.list_ues.return_value = [1, 2]
        s1 = stats_for(
            bearer_id=9,
            ue_id=1,
            tx=1000,
            rx=0,
            start_ts=100.0,
            last_ts=101.0,
        )

        def fake_get(uid):
            if uid == 1:
                return make_ue(1, stats=[s1])
            raise ValueError("UE not found")

        mock_repo.get_ue.side_effect = fake_get

        resp = api.get_ues_stats(mock_repo, ue_id=None)

        assert resp.ue_count == 2
        assert resp.bearer_count == 1
        assert resp.total_tx_bps == 8000

    def test_bearer_without_start_ts_contributes_zero(self, mock_repo, tm):
        s = stats_for(
            bearer_id=9,
            ue_id=1,
            tx=5000,
            rx=5000,
            start_ts=None,
            last_ts=None,
        )
        mock_repo.ue_exists.return_value = True
        mock_repo.get_ue.return_value = make_ue(1, stats=[s])

        resp = api.get_ues_stats(mock_repo, ue_id=1)

        assert resp.bearer_count == 1
        assert resp.total_tx_bps == 0
        assert resp.total_rx_bps == 0

    def test_single_ue_disappearing_in_loop_maps_to_400(self, mock_repo, tm):
        mock_repo.ue_exists.return_value = True
        mock_repo.get_ue.side_effect = ValueError("UE not found")

        with pytest.raises(HTTPException) as exc:
            api.get_ues_stats(mock_repo, ue_id=1)

        assert exc.value.status_code == 400