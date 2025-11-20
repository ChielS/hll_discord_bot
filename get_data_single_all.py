"""Fetch and store game data from Hell Let Loose servers."""
import requests
from datetime import datetime, timedelta
from database.db import Database
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_total_games(server_url: str):
    """Get the highest game ID from a server.

    Args:
        server_url: Server base URL

    Returns:
        The maximum game ID or None if request fails
    """
    url = f"{server_url}api/get_scoreboard_maps?page=1&limit=10"
    try:
        r = requests.get(url, timeout=10)

        if r.status_code == 200:
            data = r.json()
            ids = [m["id"] for m in data["result"]["maps"]]
            max_id = max(ids) if ids else 0
            total = data['result']['total']
            return max(max_id + 1, total)
        else:
            logger.error(f"Failed to fetch total games: {r.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error getting total games: {e}")
        return None


def get_game_data(server_url: str, game_id: int):
    """Fetch game data from the server API.

    Args:
        server_url: Server base URL
        game_id: Game ID to fetch

    Returns:
        Game data dictionary or None if request fails
    """
    url = f"{server_url}api/get_map_scoreboard?map_id={game_id}"
    try:
        r = requests.get(url, timeout=10)

        if r.status_code == 200:
            return r.json()
        else:
            logger.warning(f"Failed to fetch game {game_id}: {r.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error fetching game {game_id}: {e}")
        return None


def parse_game_start_time(start_time_str: str):
    """Parse game start time string to datetime.

    Args:
        start_time_str: Start time string from API

    Returns:
        datetime object or None if parsing fails
    """
    try:
        # Try different datetime formats
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]:
            try:
                return datetime.strptime(start_time_str, fmt)
            except ValueError:
                continue

        # If none work, try ISO format
        return datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
    except Exception as e:
        logger.error(f"Failed to parse time '{start_time_str}': {e}")
        return None


def extract_player_stats(game_data, server_name: str, game_id: int, db: Database):
    """Extract and store player statistics from game data.

    Args:
        game_data: Game data from API
        server_name: Server name
        game_id: Game ID
        db: Database instance

    Returns:
        Number of players processed
    """
    try:
        result = game_data.get('result', {})

        # Get game start time
        start_time_str = result.get('start')
        if not start_time_str:
            logger.warning(f"No start time for game {game_id}")
            return 0

        # Get players data
        player_stats_data = result.get('player_stats', {})

        if not player_stats_data:
            logger.warning(f"No player stats for game {game_id}")
            return 0

        players_processed = 0

        # Handle both list and dict formats
        if isinstance(player_stats_data, list):
            # If it's a list, process all players directly
            players_list = player_stats_data
        elif isinstance(player_stats_data, dict):
            # If it's a dict with teams, combine both teams
            players_list = []
            for team in ['allied', 'axis']:
                team_data = player_stats_data.get(team, [])
                players_list.extend(team_data)
        else:
            logger.warning(f"Unexpected player_stats_data type for game {game_id}: {type(player_stats_data)}")
            return 0

        # Process all players
        for player in players_list:
            if not isinstance(player, dict):
                logger.warning(f"Player data is not a dict: {type(player)}")
                continue

            try:
                player_id = player.get('player_id', '')
                player_name = player.get('player', '')
                kills = player.get('kills', 0)
                deaths = player.get('deaths', 0)
                kill_death_ratio = player.get('kill_death_ratio', 0.0)
                combat_score = player.get('combat', 0)
                support_score = player.get('support', 0)
                defense_score = player.get('defense', 0)
                kills_per_minute = player.get('kills_per_minute', 0.0)

                # Add to database
                db.add_player_stat(
                    server_name=server_name,
                    game_id=game_id,
                    game_start_time=start_time_str,
                    player_id=player_id,
                    player_name=player_name,
                    kills=kills,
                    deaths=deaths,
                    kill_death_ratio=kill_death_ratio,
                    combat_score=combat_score,
                    support_score=support_score,
                    defense_score=defense_score,
                    kills_per_minute=kills_per_minute
                )

                players_processed += 1

            except Exception as e:
                logger.error(f"Error processing player in game {game_id}: {e}")
                continue

        return players_processed

    except Exception as e:
        logger.error(f"Error extracting player stats from game {game_id}: {e}")
        return 0


def process_server(server_name: str, server_url: str, db: Database):
    """Process all games from a server.

    Args:
        server_name: Server name
        server_url: Server URL
        db: Database instance
    """
    logger.info(f"Processing server: {server_name}")

    # Get the highest game ID
    max_game_id = get_total_games(server_url)
    if not max_game_id:
        logger.error(f"Could not get max game ID for {server_name}")
        return

    logger.info(f"Max game ID for {server_name}: {max_game_id}")

    # Calculate cutoff date (2 weeks ago)
    cutoff_date = datetime.now() - timedelta(weeks=4)

    games_processed = 0
    games_skipped = 0

    # Iterate from highest to lowest game ID
    for game_id in range(max_game_id, 0, -1):
        # Check if already processed
        if db.is_game_processed(server_name, game_id):
            games_skipped += 1
            if games_skipped % 100 == 0:
                logger.info(f"Skipped {games_skipped} already processed games...")
            continue

        # Fetch game data
        game_data = get_game_data(server_url, game_id)
        if not game_data:
            continue

        result = game_data.get('result', {})

        # Get start time
        start_time_str = result.get('start')
        if not start_time_str:
            logger.warning(f"No start time for game {game_id}, marking as processed")
            db.mark_game_processed(server_name, game_id, '', 0)
            continue

        # Parse start time
        start_time = parse_game_start_time(start_time_str)
        if not start_time:
            logger.warning(f"Could not parse start time for game {game_id}")
            db.mark_game_processed(server_name, game_id, start_time_str, 0)
            continue

        # Check if game is older than 2 weeks
        if start_time < cutoff_date:
            logger.info(f"Game {game_id} is older than 2 weeks ({start_time}), stopping...")
            break

        # Count players
        player_stats = result.get('player_stats', {})

        # Handle case where player_stats might be a list or dict
        if isinstance(player_stats, list):
            total_players = len(player_stats)
            allied_players = 0
            axis_players = 0
        elif isinstance(player_stats, dict):
            allied_players = len(player_stats.get('allied', []))
            axis_players = len(player_stats.get('axis', []))
            total_players = allied_players + axis_players
        else:
            logger.warning(f"Unexpected player_stats type for game {game_id}: {type(player_stats)}")
            total_players = 0

        # Skip if 60 or fewer players
        if total_players <= 60:
            logger.debug(f"Game {game_id} has only {total_players} players, skipping...")
            db.mark_game_processed(server_name, game_id, start_time_str, total_players)
            continue

        # Extract and store player stats
        logger.info(f"Processing game {game_id} ({total_players} players, {start_time})")
        players_processed = extract_player_stats(game_data, server_name, game_id, db)

        # Mark game as processed
        db.mark_game_processed(server_name, game_id, start_time_str, total_players)

        games_processed += 1
        logger.info(f"Game {game_id} processed: {players_processed} players stored")

    logger.info(f"Server {server_name} complete: {games_processed} games processed, {games_skipped} skipped")


def main():
    """Main function to process all active servers."""
    logger.info("Starting game data collection...")

    # Initialize database
    db = Database()

    # Get all active servers
    active_servers = db.get_all_servers(status_filter='active')

    if not active_servers:
        logger.warning("No active servers found in database")
        return

    logger.info(f"Found {len(active_servers)} active servers")

    # Process each server
    for server in active_servers:
        server_name = server['name']
        server_url = server['url']

        try:
            process_server(server_name, server_url, db)
        except Exception as e:
            logger.error(f"Error processing server {server_name}: {e}")
            continue

    logger.info("Game data collection complete!")


if __name__ == "__main__":
    main()
