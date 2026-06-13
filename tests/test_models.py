import pytest
from pydantic import ValidationError

from epc.models import (
    AddBearerRequest,
    AttachUERequest,
    BearerConfig,
    StartTrafficRequest,
    ThroughputStats,
    UEState,
)


@pytest.mark.parametrize("ue_id", [1, 50, 100])
def test_attach_ue_request_accepts_valid_ue_range(ue_id):
    request = AttachUERequest(ue_id=ue_id)

    assert request.ue_id == ue_id


@pytest.mark.parametrize("ue_id", [-1, 0, 101])
def test_attach_ue_request_rejects_ue_id_outside_allowed_range(ue_id):
    with pytest.raises(ValidationError):
        AttachUERequest(ue_id=ue_id)


@pytest.mark.parametrize("bearer_id", [1, 5, 9])
def test_add_bearer_request_accepts_valid_bearer_range(bearer_id):
    request = AddBearerRequest(bearer_id=bearer_id)

    assert request.bearer_id == bearer_id


@pytest.mark.parametrize("bearer_id", [-1, 0, 10])
def test_add_bearer_request_rejects_bearer_id_outside_allowed_range(bearer_id):
    with pytest.raises(ValidationError):
        AddBearerRequest(bearer_id=bearer_id)


def test_bearer_config_has_safe_default_state():
    bearer = BearerConfig(bearer_id=9)

    assert bearer.bearer_id == 9
    assert bearer.protocol is None
    assert bearer.target_bps is None
    assert bearer.active is False


@pytest.mark.parametrize("protocol", ["tcp", "udp"])
def test_bearer_config_accepts_supported_protocols(protocol):
    bearer = BearerConfig(bearer_id=1, protocol=protocol)

    assert bearer.protocol == protocol


@pytest.mark.parametrize("protocol", ["icmp", "http", "TCP", "UDP", ""])
def test_bearer_config_rejects_unsupported_protocols(protocol):
    with pytest.raises(ValidationError):
        BearerConfig(bearer_id=1, protocol=protocol)


@pytest.mark.parametrize("protocol", ["tcp", "udp"])
def test_start_traffic_request_accepts_supported_protocols(protocol):
    request = StartTrafficRequest(protocol=protocol, kbps=1)

    assert request.protocol == protocol


@pytest.mark.parametrize("protocol", ["icmp", "http", "TCP", "UDP", ""])
def test_start_traffic_request_rejects_unsupported_protocols(protocol):
    with pytest.raises(ValidationError):
        StartTrafficRequest(protocol=protocol, kbps=1)


@pytest.mark.parametrize(
    "kwargs,expected_bps",
    [
        ({"Mbps": 1}, 1_000_000),
        ({"Mbps": 100}, 100_000_000),
        ({"kbps": 1}, 1_000),
        ({"kbps": 100_000}, 100_000_000),
        ({"bps": 1}, 1),
        ({"bps": 100_000_000}, 100_000_000),
    ],
)
def test_start_traffic_request_converts_throughput_to_target_bps(kwargs, expected_bps):
    request = StartTrafficRequest(protocol="udp", **kwargs)

    assert request.target_bps() == expected_bps


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"Mbps": 1, "kbps": 1},
        {"Mbps": 1, "bps": 1},
        {"kbps": 1, "bps": 1},
        {"Mbps": 1, "kbps": 1, "bps": 1},
    ],
)
def test_start_traffic_request_requires_exactly_one_throughput_unit(kwargs):
    with pytest.raises(ValidationError):
        StartTrafficRequest(protocol="udp", **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"Mbps": 101},
        {"kbps": 100_001},
        {"bps": 100_000_001},
    ],
)
def test_start_traffic_request_rejects_throughput_above_100_mbps(kwargs):
    with pytest.raises(ValidationError):
        StartTrafficRequest(protocol="udp", **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"Mbps": -1},
        {"kbps": -0.001},
        {"kbps": -5_000},
        {"bps": -1},
    ],
)
def test_start_traffic_request_rejects_negative_throughput(kwargs):
    with pytest.raises(ValidationError):
        StartTrafficRequest(protocol="udp", **kwargs)