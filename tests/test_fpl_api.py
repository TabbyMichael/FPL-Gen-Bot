import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from services.fpl_api import FPLAPI

@pytest.fixture
def fpl_api():
    """Fixture to create FPLAPI instance"""
    return FPLAPI()

@pytest.mark.asyncio
async def test_fpl_api_initialization():
    """Test FPLAPI initialization"""
    api = FPLAPI()
    assert api.session is None
    assert api.timeout.total == 30

@pytest.mark.asyncio
async def test_fpl_api_context_manager():
    """Test FPLAPI context manager"""
    async with FPLAPI() as api:
        assert api.session is not None
    
    # Session should be closed after context
    # Note: In real test, we'd check if session is closed

@pytest.mark.asyncio
async def test_get_bootstrap_data_success():
    """Test successful bootstrap data retrieval"""
    # Directly test the _make_request_with_retry method
    async with FPLAPI() as api:
        # Mock the session and response
        mock_session = AsyncMock()
        api.session = mock_session
        
        # Mock the _make_request_with_retry method to return our test data
        with patch.object(api, '_make_request_with_retry', return_value={'elements': []}):
            result = await api.get_bootstrap_data()
            assert result == {'elements': []}

@pytest.mark.asyncio
async def test_get_bootstrap_data_failure():
    """Test failed bootstrap data retrieval"""
    async with FPLAPI() as api:
        # Mock the _make_request_with_retry method to return None
        with patch.object(api, '_make_request_with_retry', return_value=None):
            result = await api.get_bootstrap_data()
            assert result is None

@pytest.mark.asyncio
async def test_get_player_data_success():
    """Test successful player data retrieval"""
    async with FPLAPI() as api:
        # Mock the _make_request_with_retry method to return our test data
        with patch.object(api, '_make_request_with_retry', return_value={'history': []}):
            result = await api.get_player_data(1)
            assert result == {'history': []}

@pytest.mark.asyncio
async def test_get_fixture_difficulty():
    """Test fixture difficulty calculation"""
    api = FPLAPI()
    
    # Mock fixtures data
    fixtures = [
        {'event': 1, 'team_h': 1, 'team_h_difficulty': 2, 'team_a': 2, 'team_a_difficulty': 4},
        {'event': 1, 'team_h': 3, 'team_h_difficulty': 3, 'team_a': 4, 'team_a_difficulty': 3}
    ]
    
    # Test home team difficulty
    with patch.object(api, 'get_fixtures', return_value=fixtures):
        difficulty = await api.get_fixture_difficulty(1, 1)
        assert difficulty == 2
    
    # Test away team difficulty
    with patch.object(api, 'get_fixtures', return_value=fixtures):
        difficulty = await api.get_fixture_difficulty(2, 1)
        assert difficulty == 4
    
    # Test default difficulty when no fixture found
    with patch.object(api, 'get_fixtures', return_value=fixtures):
        difficulty = await api.get_fixture_difficulty(5, 1)
        assert difficulty == 3