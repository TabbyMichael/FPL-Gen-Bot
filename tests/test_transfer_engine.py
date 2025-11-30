import pytest
from unittest.mock import Mock, patch
from services.transfer_engine import TransferEngine

@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock()

@pytest.fixture
def transfer_engine(mock_db):
    """Transfer engine instance with mocked DB"""
    with patch('services.transfer_engine.MLPredictor') as mock_ml:
        mock_ml_instance = Mock()
        mock_ml_instance.is_trained = False
        mock_ml.return_value = mock_ml_instance
        engine = TransferEngine(mock_db)
        return engine

def test_is_player_available(transfer_engine):
    """Test player availability checking"""
    # Test available player
    available_player = {
        'status': 'a',
        'chance_of_playing_next_round': 100
    }
    assert transfer_engine.is_player_available(available_player) is True
    
    # Test injured player
    injured_player = {
        'status': 'i',
        'chance_of_playing_next_round': 0
    }
    assert transfer_engine.is_player_available(injured_player) is False
    
    # Test player with low chance of playing
    low_chance_player = {
        'status': 'a',
        'chance_of_playing_next_round': 50
    }
    assert transfer_engine.is_player_available(low_chance_player) is False
    
    # Test player with missing status (should default to available)
    missing_status_player = {
        'chance_of_playing_next_round': 100
    }
    assert transfer_engine.is_player_available(missing_status_player) is True
    
    # Test player with None chance of playing (should default to available)
    none_chance_player = {
        'status': 'a',
        'chance_of_playing_next_round': None
    }
    assert transfer_engine.is_player_available(none_chance_player) is True

def test_calculate_player_value(transfer_engine):
    """Test player value calculation"""
    # Test normal player
    player = {
        'now_cost': 50  # £5.0m
    }
    
    with patch.object(transfer_engine, 'calculate_expected_points', return_value=10):
        value = transfer_engine.calculate_player_value(player, 3)
        # Expected points (10) / (price in millions (5.0)) = 2.0
        assert value == 2.0
    
    # Test player with zero cost
    zero_cost_player = {
        'now_cost': 0
    }
    value = transfer_engine.calculate_player_value(zero_cost_player, 3)
    assert value == 0

def test_calculate_expected_points(transfer_engine):
    """Test expected points calculation"""
    # Test with untrained ML model (fallback)
    player_data = {
        'history': [
            {'total_points': 5},
            {'total_points': 7},
            {'total_points': 3}
        ]
    }
    
    # Mock ML predictor to be untrained
    transfer_engine.ml_predictor.is_trained = False
    
    points = transfer_engine.calculate_expected_points(player_data, 3)
    # Average of last 3 games: (5+7+3)/3 = 5
    # With neutral difficulty (3): 5 * 1.2 = 6 (since difficulty multiplier is 1.2 for difficulty 3)
    assert points == 6
    
    # Test with empty history
    empty_history_player = {
        'history': []
    }
    points = transfer_engine.calculate_expected_points(empty_history_player, 3)
    assert points == 0

def test_record_transfer(transfer_engine, mock_db):
    """Test transfer recording"""
    transfer_data = {
        'out': {'id': 1, 'web_name': 'Player A'},
        'in': {'id': 2, 'web_name': 'Player B'},
        'gain': 2.5,
        'gameweek': 13,
        'cost': 0
    }
    
    transfer_engine.record_transfer(transfer_data)
    
    # Verify database operations
    assert mock_db.add.called
    assert mock_db.commit.called

def test_record_transfer_error(transfer_engine, mock_db):
    """Test transfer recording with error"""
    mock_db.add.side_effect = Exception("Database error")
    
    transfer_data = {
        'out': {'id': 1, 'web_name': 'Player A'},
        'in': {'id': 2, 'web_name': 'Player B'},
        'gain': 2.5,
        'gameweek': 13,
        'cost': 0
    }
    
    transfer_engine.record_transfer(transfer_data)
    
    # Verify rollback was called
    assert mock_db.rollback.called