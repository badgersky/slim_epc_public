import pytest

from epc.traffic import TrafficGeneratorManager
from epc.models import BearerConfig


@pytest.mark.parametrize("ue_id", [1, 10, 15])
@pytest.mark.parametrize("bearer_id", [1, 4, 9])
@pytest.mark.parametrize("protocol", ["tcp", "udp"])
def test_start_creates_task(repo, ue_id, bearer_id, protocol):
    manager = TrafficGeneratorManager(repo)

    bearer = BearerConfig(
        bearer_id=bearer_id,
        target_bps=8000,
        protocol=protocol,
    )

    manager.start(ue_id=ue_id, bearer=bearer)

    assert (ue_id, bearer_id) in manager.tasks
    assert manager.is_running(ue_id, bearer_id) 

@pytest.mark.parametrize("ue_id", [1, 10, 15])
@pytest.mark.parametrize("bearer_id", [1, 4, 9])
@pytest.mark.parametrize("protocol", ["tcp", "udp"])
def test_start_duplicate_bearer_raises(repo, ue_id, bearer_id, protocol):
    manager = TrafficGeneratorManager(repo)

    bearer = BearerConfig(
        bearer_id=bearer_id,
        target_bps=8000,
        protocol=protocol,
    )

    manager.start(ue_id=ue_id, bearer=bearer)

    with pytest.raises(ValueError, match="Traffic already running"):
        manager.start(ue_id=ue_id, bearer=bearer)

@pytest.mark.parametrize("ue_id", [1, 10, 15])
@pytest.mark.parametrize("bearer_id", [1, 4, 9])
@pytest.mark.parametrize("protocol", ["tcp", "udp"])
def test_start_missing_target_bps_raises(repo, ue_id, bearer_id, protocol):
    manager = TrafficGeneratorManager(repo)

    bearer = BearerConfig(
        bearer_id=bearer_id,
        target_bps=None,
        protocol=protocol,
    )

    with pytest.raises(ValueError, match="Bearer not configured for traffic"):
        manager.start(ue_id=ue_id, bearer=bearer)

@pytest.mark.parametrize("ue_id", [1, 10, 15])
@pytest.mark.parametrize("bearer_id", [1, 4, 9])
def test_start_missing_protocol_raises(repo, ue_id, bearer_id):
    manager = TrafficGeneratorManager(repo)

    bearer = BearerConfig(
        bearer_id=bearer_id,
        target_bps=8000,
        protocol=None,
    )

    with pytest.raises(ValueError, match="Bearer not configured for traffic"):
        manager.start(ue_id=ue_id, bearer=bearer)

@pytest.mark.parametrize("ue_id", [1, 10, 15])
@pytest.mark.parametrize("bearer_id", [1, 4, 9])
@pytest.mark.parametrize("protocol", ["tcp", "udp"])
def test_stop_removes_task(repo, ue_id, bearer_id, protocol):
    manager = TrafficGeneratorManager(repo)

    bearer = BearerConfig(
        bearer_id=bearer_id,
        target_bps=8000,
        protocol=protocol,
    )

    manager.start(ue_id, bearer)

    assert (ue_id, bearer_id) in manager.tasks

    manager.stop(ue_id, bearer_id)

    assert (ue_id, bearer_id) not in manager.tasks
    assert manager.is_running(ue_id, bearer_id) is False

@pytest.mark.parametrize("ue_id", [1, 10, 15])
@pytest.mark.parametrize("bearer_id", [1, 4, 9])
@pytest.mark.parametrize("protocol", ["tcp", "udp"])
def test_stop_cancels_future(repo, ue_id, bearer_id, protocol):
    manager = TrafficGeneratorManager(repo)

    bearer = BearerConfig(
        bearer_id=bearer_id,
        target_bps=8000,
        protocol=protocol,
    )

    manager.start(ue_id, bearer)

    future = manager.tasks[(ue_id, bearer_id)]
    manager.stop(ue_id, bearer_id)

    assert future.cancelled() is True
