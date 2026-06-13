import pytest
from epc.models import BearerConfig

def test_attach_and_get_ue(repo):
    # Podłączamy UE
    repo.attach_ue(5)
    
    # Sprawdzamy czy istnieje
    ue = repo.get_ue(5)
    assert ue.ue_id == 5
    
    # Inwariant 1: Domyślnie musi tworzyć się bearer 9
    assert 9 in ue.bearers
    assert ue.bearers[9].bearer_id == 9

def test_attach_duplicate_ue_raises_error(repo):
    repo.attach_ue(1)
    # Próba podłączenia jeszcze raz tego samego powinna rzucić ValueError
    with pytest.raises(ValueError, match="UE already attached"):
        repo.attach_ue(1)

def test_delete_default_bearer_raises_error(repo):
    repo.attach_ue(1)
    # Inwariant 2: Nie można usunąć bearera o ID 9
    with pytest.raises(ValueError, match="Cannot remove default bearer"):
        repo.delete_bearer(1, 9)

def test_add_and_delete_bearer(repo):
    repo.attach_ue(1)
    
    # Dodanie poprawnego bearera
    repo.add_bearer(1, 5)
    
    ue = repo.get_ue(1)
    assert 5 in ue.bearers
    
    # Usunięcie bearera
    repo.delete_bearer(1, 5)
    ue = repo.get_ue(1)
    assert 5 not in ue.bearers

def test_reset_all(repo):
    repo.attach_ue(1)
    repo.attach_ue(2)
    assert len(list(repo.list_ues())) == 2
    
    # Funkcja usuwająca wszystkie stany
    repo.reset_all()
    
    assert list(repo.list_ues()) == []

def test_detach_ue(repo):
    repo.attach_ue(1)
    repo.detach_ue(1)
    assert not repo.ue_exists(1)
    
    # Detach nieistniejącego UE
    with pytest.raises(ValueError, match="UE not found"):
        repo.detach_ue(99)

def test_get_ue_not_found(repo):
    with pytest.raises(ValueError, match="UE not found"):
        repo.get_ue(99)

def test_add_duplicate_bearer(repo):
    repo.attach_ue(1)
    repo.add_bearer(1, 5)
    with pytest.raises(ValueError, match="Bearer already exists"):
        repo.add_bearer(1, 5)

def test_delete_missing_bearer(repo):
    repo.attach_ue(1)
    with pytest.raises(ValueError, match="Bearer not found"):
        repo.delete_bearer(1, 5)

def test_update_bearer_and_stats(repo):
    from epc.models import ThroughputStats
    import time
    
    repo.attach_ue(1)
    repo.add_bearer(1, 5)
    
    ue = repo.get_ue(1)
    bearer = ue.bearers[5]
    bearer.target_bps = 1000
    bearer.protocol = "tcp"
    repo.update_bearer(1, bearer)
    
    stats = ThroughputStats(bearer_id=5, ue_id=1, start_ts=time.time(), bytes_tx=100, bytes_rx=200, protocol="tcp", target_bps=1000)
    repo.update_stats(1, stats)
    
    updated_ue = repo.get_ue(1)
    assert updated_ue.bearers[5].target_bps == 1000
    assert updated_ue.bearers[5].protocol == "tcp"
    assert updated_ue.stats[5].bytes_tx == 100
    assert updated_ue.stats[5].bytes_rx == 200
