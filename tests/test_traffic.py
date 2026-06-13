import pytest

from epc.traffic import TrafficGeneratorManager
from epc.models import BearerConfig


def test_start_traffic_bearer1_bps8000_udp(repo):
    manager = TrafficGeneratorManager(repo)
    bearer = BearerConfig(
        bearer_id=1,
        target_bps=8000,
        protocol="udp",
    )

    manager.start(ue_id=1, bearer=bearer)

    assert (1, 1) in manager.tasks
    assert manager.is_running(1, 1) is True

def test_start_traffic_bearer1_bps8000_tcp(repo):
    manager = TrafficGeneratorManager(repo)
    bearer = BearerConfig(
        bearer_id=1,
        target_bps=8000,
        protocol="tcp",
    )

    manager.start(ue_id=1, bearer=bearer)

    assert (1, 1) in manager.tasks
    assert manager.is_running(1, 1) is True

def test_start_traffic_bearer9_bps8000_udp(repo):
    manager = TrafficGeneratorManager(repo)
    bearer = BearerConfig(
        bearer_id=9,
        target_bps=8000,
        protocol="udp",
    )

    manager.start(ue_id=1, bearer=bearer)

    assert (1, 9) in manager.tasks
    assert manager.is_running(1, 9) is True

def test_start_traffic_bearer9_bps8000_tcp(repo):
    manager = TrafficGeneratorManager(repo)
    bearer = BearerConfig(
        bearer_id=9,
        target_bps=8000,
        protocol="tcp",
    )

    manager.start(ue_id=1, bearer=bearer)

    assert (1, 9) in manager.tasks
    assert manager.is_running(1, 9) is True

def test_start_traffic_bearer4_bps8000_udp(repo):
    manager = TrafficGeneratorManager(repo)
    bearer = BearerConfig(
        bearer_id=4,
        target_bps=8000,
        protocol="udp",
    )

    manager.start(ue_id=1, bearer=bearer)

    assert (1, 4) in manager.tasks
    assert manager.is_running(1, 4) is True

def test_start_traffic_bearer4_bps8000_tcp(repo):
    manager = TrafficGeneratorManager(repo)
    bearer = BearerConfig(
        bearer_id=4,
        target_bps=8000,
        protocol="tcp",
    )

    manager.start(ue_id=1, bearer=bearer)

    assert (1, 4) in manager.tasks
    assert manager.is_running(1, 4) is True   

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
