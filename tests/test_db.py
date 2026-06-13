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

def test_list_ues_ordering(repo):
    # Dodajemy w odwróconej kolejności
    repo.attach_ue(5)
    repo.attach_ue(2)
    repo.attach_ue(8)
    
    # list_ues powinno zwracać posortowane po ID
    assert list(repo.list_ues()) == [2, 5, 8]

def test_delete_bearer_removes_stats(repo):
    from epc.models import ThroughputStats
    import time
    
    repo.attach_ue(1)
    repo.add_bearer(1, 4)
    
    # Dodajemy statystyki do bearera
    stats = ThroughputStats(bearer_id=4, ue_id=1, start_ts=time.time(), bytes_tx=500, bytes_rx=500)
    repo.update_stats(1, stats)
    
    # Upewniamy się, że są zapisane
    ue = repo.get_ue(1)
    assert 4 in ue.stats
    
    # Usuwamy bearera
    repo.delete_bearer(1, 4)
    
    # Sprawdzamy, czy usunięto zarówno bearera jak i jego statystyki
    ue_after = repo.get_ue(1)
    assert 4 not in ue_after.bearers
    assert 4 not in ue_after.stats

def test_operations_on_missing_ue(repo):
    from epc.models import BearerConfig, ThroughputStats
    import time
    
    # Akcje modyfikujące konkretnego UE powinny rzucać błąd, gdy UE nie istnieje
    with pytest.raises(ValueError, match="UE not found"):
        repo.add_bearer(99, 1)
        
    with pytest.raises(ValueError, match="UE not found"):
        repo.delete_bearer(99, 1)
        
    with pytest.raises(ValueError, match="UE not found"):
        repo.update_bearer(99, BearerConfig(bearer_id=1))
        
    with pytest.raises(ValueError, match="UE not found"):
        repo.update_stats(99, ThroughputStats(bearer_id=1, ue_id=99, start_ts=time.time()))

def test_persistence(tmp_path):
    from epc.db import EPCRepository
    db_file = tmp_path / "persistent.db"
    
    # 1. Tworzymy repozytorium i zapisujemy stan
    repo1 = EPCRepository(str(db_file))
    repo1.attach_ue(1)
    repo1.add_bearer(1, 5)
    
    # 2. Tworzymy nowe repozytorium z tego samego pliku (symulacja restartu serwera)
    repo2 = EPCRepository(str(db_file))
    ue = repo2.get_ue(1)
    assert ue.ue_id == 1
    assert 5 in ue.bearers

def test_volume_attach(repo):
    # Test obciążeniowy/wolumenowy - dodanie 100 UEs
    for i in range(1, 101):
        repo.attach_ue(i)
    
    ues = list(repo.list_ues())
    assert len(ues) == 100
    assert ues[0] == 1
    assert ues[-1] == 100

def test_ue_isolation(repo):
    # Upewniamy się, że modyfikacje jednego UE nie wyciekają do innego
    repo.attach_ue(1)
    repo.attach_ue(2)
    
    repo.add_bearer(1, 5)
    
    ue1 = repo.get_ue(1)
    ue2 = repo.get_ue(2)
    
    assert 5 in ue1.bearers
    assert 5 not in ue2.bearers

def test_update_bearer_acts_as_upsert(repo):
    from epc.models import BearerConfig
    repo.attach_ue(1)
    
    # Zgodnie z implementacją, update_bearer zachowuje się jak upsert,
    # nawet jeśli bearer wcześniej nie został dodany przez add_bearer.
    # Weryfikujemy to zachowanie, by chronić kontrakt przed niezamierzoną zmianą.
    repo.update_bearer(1, BearerConfig(bearer_id=4, target_bps=5000, protocol="udp"))
    
    ue = repo.get_ue(1)
    assert 4 in ue.bearers
    assert ue.bearers[4].target_bps == 5000

def test_ue_exists_false(repo):
    # Trywialny test metody ue_exists
    assert repo.ue_exists(99) is False

def test_reset_all_on_empty(repo):
    # Wywołanie reset_all na pustej bazie nie powinno crashować
    assert list(repo.list_ues()) == []
    repo.reset_all()
    assert list(repo.list_ues()) == []

def test_delete_bearer_stats_independence(repo):
    from epc.models import ThroughputStats
    import time
    
    repo.attach_ue(1)
    repo.add_bearer(1, 4)
    repo.add_bearer(1, 5)
    
    repo.update_stats(1, ThroughputStats(bearer_id=4, ue_id=1, start_ts=time.time(), bytes_tx=10))
    repo.update_stats(1, ThroughputStats(bearer_id=5, ue_id=1, start_ts=time.time(), bytes_tx=20))
    
    # Usuwamy tylko bearera 4
    repo.delete_bearer(1, 4)
    
    ue = repo.get_ue(1)
    # Bearer 5 i jego statystyki powinny pozostać nienaruszone
    assert 5 in ue.bearers
    assert 5 in ue.stats
    assert ue.stats[5].bytes_tx == 20
    # A bearer 4 usunięty
    assert 4 not in ue.bearers
    assert 4 not in ue.stats
