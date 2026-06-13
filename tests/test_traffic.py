import pytest

from epc.traffic import TrafficGeneratorManager
from epc.models import BearerConfig


@pytest.mark.parametrize("bearer_id", [1, 4, 9])
@pytest.mark.parametrize("protocol", ["tcp", "udp"])
def test_start_creates_task(repo, bearer_id, protocol):
    manager = TrafficGeneratorManager(repo)

    bearer = BearerConfig(
        bearer_id=bearer_id,
        target_bps=8000,
        protocol=protocol,
    )

    manager.start(ue_id=1, bearer=bearer)

    assert (1, bearer_id) in manager.tasks
    assert manager.is_running(1, bearer_id) 

def test_start_duplicate_bearer_raises(repo):
    manager = TrafficGeneratorManager(repo)

    bearer = BearerConfig(
        bearer_id=1,
        target_bps=8000,
        protocol="udp",
    )

    manager.start(ue_id=1, bearer=bearer)

    with pytest.raises(ValueError, match="Traffic already running"):
        manager.start(ue_id=1, bearer=bearer)

def test_start_missing_target_bps_raises(repo):
    manager = TrafficGeneratorManager(repo)

    bearer = BearerConfig(
        bearer_id=1,
        target_bps=None,
        protocol="udp",
    )

    with pytest.raises(ValueError, match="Bearer not configured for traffic"):
        manager.start(ue_id=1, bearer=bearer)

def test_start_missing_protocol_raises(repo):
    manager = TrafficGeneratorManager(repo)

    bearer = BearerConfig(
        bearer_id=1,
        target_bps=8000,
        protocol=None,
    )

    with pytest.raises(ValueError, match="Bearer not configured for traffic"):
        manager.start(ue_id=1, bearer=bearer)
