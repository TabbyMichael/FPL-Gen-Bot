import aiohttp
import asyncio
import logging
from config.settings import FPL_BASE_URL, FPL_USERNAME, FPL_PASSWORD, TEAM_ID, SESSION_ID, CSRF_TOKEN

logger = logging.getLogger(__name__)

class FPLAPI:
    """Handles communication with the FPL API"""
    
    def __init__(self):
        self.session = None
        self.authenticated_session = None
        # Set default timeout
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def __aenter__(self):
        # Create session with timeout and retry settings
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, ttl_dns_cache=300)
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            connector=connector,
            headers={'User-Agent': 'FPL-Bot/1.0'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        if self.authenticated_session:
            await self.authenticated_session.close()
    
    async def _make_request_with_retry(self, url, method='GET', **kwargs):
        """Make HTTP request with retry logic"""
        max_retries = 3
        retry_delay = 1  # seconds
        
        # Check if session exists
        if not self.session:
            logger.error("No active session")
            return None
        
        for attempt in range(max_retries):
            try:
                if method.upper() == 'GET':
                    async with self.session.get(url, **kwargs) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:  # Rate limited
                            logger.warning(f"Rate limited, waiting {retry_delay * 2} seconds...")
                            await asyncio.sleep(retry_delay * 2)
                            retry_delay *= 2
                            continue
                        else:
                            logger.error(f"HTTP {response.status} for {url}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 2
                                continue
                            return None
                elif method.upper() == 'POST':
                    # Use authenticated session for POST requests if available
                    session_to_use = self.authenticated_session if self.authenticated_session else self.session
                    async with session_to_use.post(url, **kwargs) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 401:  # Unauthorized
                            logger.warning("Unauthorized access, trying to re-authenticate...")
                            if await self._authenticate():
                                # Retry the request with authenticated session
                                if self.authenticated_session:
                                    async with self.authenticated_session.post(url, **kwargs) as retry_response:
                                        if retry_response.status == 200:
                                            return await retry_response.json()
                            return None
                        elif response.status == 429:  # Rate limited
                            logger.warning(f"Rate limited, waiting {retry_delay * 2} seconds...")
                            await asyncio.sleep(retry_delay * 2)
                            retry_delay *= 2
                            continue
                        else:
                            logger.error(f"HTTP {response.status} for {url}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 2
                                continue
                            return None
                else:
                    logger.error(f"Unsupported HTTP method: {method}")
                    return None
                    
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return None
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1} for {url}: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return None
        
        return None
    
    async def _authenticate(self):
        """Authenticate with FPL using either traditional login or session cookies"""
        try:
            # Close existing authenticated session if it exists
            if self.authenticated_session:
                await self.authenticated_session.close()
            
            # Prefer session-based authentication if available (for Google Sign-In)
            if SESSION_ID and CSRF_TOKEN:
                logger.info("Using session-based authentication")
                connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, ttl_dns_cache=300)
                self.authenticated_session = aiohttp.ClientSession(
                    timeout=self.timeout,
                    connector=connector,
                    headers={
                        'User-Agent': 'FPL-Bot/1.0',
                        'Cookie': f'sessionid={SESSION_ID}; csrftoken={CSRF_TOKEN}',
                        'X-CSRFToken': CSRF_TOKEN,
                        'Referer': 'https://fantasy.premierleague.com/'
                    }
                )
                return True
            
            # Fallback to traditional username/password authentication
            elif FPL_USERNAME and FPL_PASSWORD:
                logger.info("Using traditional authentication")
                # Note: This is a simplified implementation
                # Real implementation would need to handle the full login flow
                connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, ttl_dns_cache=300)
                self.authenticated_session = aiohttp.ClientSession(
                    timeout=self.timeout,
                    connector=connector,
                    headers={'User-Agent': 'FPL-Bot/1.0'}
                )
                # In a real implementation, we would perform the login here
                return True
            
            logger.warning("No authentication credentials provided")
            return False
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False
    
    async def get_bootstrap_data(self):
        """Get static bootstrap data from FPL"""
        try:
            url = f"{FPL_BASE_URL}/bootstrap-static/"
            return await self._make_request_with_retry(url)
        except Exception as e:
            logger.error(f"Error fetching bootstrap data: {str(e)}")
            return None
    
    async def get_player_data(self, player_id):
        """Get detailed data for a specific player"""
        try:
            url = f"{FPL_BASE_URL}/element-summary/{player_id}/"
            return await self._make_request_with_retry(url)
        except Exception as e:
            logger.error(f"Error fetching player data for ID {player_id}: {str(e)}")
            return None
    
    async def get_fixtures(self):
        """Get upcoming fixtures"""
        try:
            url = f"{FPL_BASE_URL}/fixtures/"
            return await self._make_request_with_retry(url)
        except Exception as e:
            logger.error(f"Error fetching fixtures: {str(e)}")
            return None
    
    async def get_team_data(self):
        """Get team data for the configured team ID"""
        if not TEAM_ID:
            logger.error("No TEAM_ID configured")
            return None
            
        try:
            url = f"{FPL_BASE_URL}/entry/{TEAM_ID}/"
            return await self._make_request_with_retry(url)
        except Exception as e:
            logger.error(f"Error fetching team data for ID {TEAM_ID}: {str(e)}")
            return None
    
    async def get_team_picks(self, gameweek=None):
        """Get team picks for a specific gameweek (defaults to current)"""
        if not TEAM_ID:
            logger.error("No TEAM_ID configured")
            return None
            
        try:
            # If no gameweek specified, try to get current gameweek
            if gameweek is None:
                bootstrap_data = await self.get_bootstrap_data()
                if bootstrap_data:
                    events = bootstrap_data.get('events', [])
                    for event in events:
                        if event.get('is_current'):
                            gameweek = event.get('id')
                            break
                        elif event.get('is_next'):
                            gameweek = event.get('id')
                            break
            
            if gameweek is None:
                logger.error("Could not determine current gameweek")
                return None
                
            url = f"{FPL_BASE_URL}/entry/{TEAM_ID}/event/{gameweek}/picks/"
            return await self._make_request_with_retry(url)
        except Exception as e:
            logger.error(f"Error fetching team picks for ID {TEAM_ID}, GW {gameweek}: {str(e)}")
            return None
    
    async def get_player_info(self, player_id):
        """Get detailed player information"""
        try:
            bootstrap_data = await self.get_bootstrap_data()
            if not bootstrap_data:
                return None
                
            players = bootstrap_data.get('elements', [])
            for player in players:
                if player.get('id') == player_id:
                    return player
            return None
        except Exception as e:
            logger.error(f"Error fetching player info for ID {player_id}: {str(e)}")
            return None
    
    async def get_fixture_difficulty(self, team_id, gameweek):
        """Get fixture difficulty for a team in a specific gameweek"""
        try:
            fixtures = await self.get_fixtures()
            if not fixtures:
                return 3  # Default medium difficulty
            
            for fixture in fixtures:
                if fixture.get('event') == gameweek:
                    if fixture.get('team_h') == team_id:
                        return fixture.get('team_h_difficulty', 3)
                    elif fixture.get('team_a') == team_id:
                        return fixture.get('team_a_difficulty', 3)
            
            return 3  # Default medium difficulty
        except Exception as e:
            logger.error(f"Error fetching fixture difficulty for team {team_id}, GW {gameweek}: {str(e)}")
            return 3
    
    async def get_player_injury_status(self, player_id):
        """Get injury/suspension status for a player"""
        try:
            player_info = await self.get_player_info(player_id)
            if not player_info:
                return {'status': 'a', 'news': '', 'chance_of_playing_next_round': 100, 'chance_of_playing_this_round': 100}
            
            status = player_info.get('status', 'a')
            news = player_info.get('news', '')
            
            # Handle None values for chance of playing
            chance_next = player_info.get('chance_of_playing_next_round')
            chance_this = player_info.get('chance_of_playing_this_round')
            
            # Convert None to default values
            chance_next = chance_next if chance_next is not None else 100
            chance_this = chance_this if chance_this is not None else 100
            
            return {
                'status': status,
                'news': news,
                'chance_of_playing_next_round': chance_next,
                'chance_of_playing_this_round': chance_this
            }
        except Exception as e:
            logger.error(f"Error fetching injury status for player {player_id}: {str(e)}")
            return {'status': 'a', 'news': '', 'chance_of_playing_next_round': 100, 'chance_of_playing_this_round': 100}
    
    async def execute_transfers(self, transfers):
        """Execute transfers in FPL"""
        if not TEAM_ID:
            logger.error("No TEAM_ID configured")
            return False
            
        try:
            # Ensure we're authenticated
            if not self.authenticated_session:
                if not await self._authenticate():
                    logger.error("Failed to authenticate for transfer execution")
                    return False
            
            # Prepare transfer payload
            transfer_payload = {
                'confirmed': True,
                'entry': int(TEAM_ID),
                'wildcard': False,
                'freehit': False,
                'benchboost': False,
                'triple_captain': False,
                'transfers': transfers
            }
            
            url = f"{FPL_BASE_URL}/transfers/"
            headers = {
                'Content-Type': 'application/json',
                'Referer': 'https://fantasy.premierleague.com/transfers'
            }
            
            # Try to execute transfers with authenticated session
            if self.authenticated_session:
                async with self.authenticated_session.post(url, json=transfer_payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Transfers executed successfully: {result}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to execute transfers. Status: {response.status}, Error: {error_text}")
                        return False
            else:
                logger.error("No authenticated session available for transfer execution")
                return False
                
        except Exception as e:
            logger.error(f"Error executing transfers: {str(e)}")
            return False