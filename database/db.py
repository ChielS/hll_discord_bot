"""SQLite database operations for greeting statistics."""
import sqlite3
from datetime import datetime
from pathlib import Path


class Database:
    """Handle SQLite database operations for the Discord bot."""

    def __init__(self, db_path: str = "bot_data.db"):
        """Initialize database connection.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Get a database connection."""
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Initialize the database with required tables."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS greeting_stats (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                greeting_count INTEGER DEFAULT 0,
                last_greeted TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                url TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                clan TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_name TEXT NOT NULL,
                game_id INTEGER NOT NULL,
                start_time TIMESTAMP NOT NULL,
                player_count INTEGER NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(server_name, game_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_name TEXT NOT NULL,
                game_id INTEGER NOT NULL,
                game_start_time TIMESTAMP NOT NULL,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                kills INTEGER,
                deaths INTEGER,
                kill_death_ratio REAL,
                combat_score INTEGER,
                support_score INTEGER,
                defense_score INTEGER,
                kills_per_minute REAL,
                UNIQUE(server_name, game_id, player_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_watchlist (
                player_id TEXT PRIMARY KEY,
                player_name TEXT NOT NULL,
                mean_kd REAL,
                mean_kpm REAL,
                mean_combat REAL,
                number_of_games INTEGER,
                follow INTEGER DEFAULT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create trigger to automatically update watchlist when player_stats are inserted
        cursor.execute("DROP TRIGGER IF EXISTS update_watchlist_on_insert")
        cursor.execute("""
            CREATE TRIGGER update_watchlist_on_insert
            AFTER INSERT ON player_stats
            BEGIN
                INSERT INTO player_watchlist (player_id, player_name, mean_kd, mean_kpm, mean_combat, number_of_games, last_updated)
                SELECT
                    NEW.player_id,
                    NEW.player_name,
                    AVG(kill_death_ratio),
                    AVG(kills_per_minute),
                    AVG(combat_score),
                    COUNT(*),
                    datetime('now')
                FROM player_stats
                WHERE player_id = NEW.player_id
                ON CONFLICT(player_id) DO UPDATE SET
                    player_name = excluded.player_name,
                    mean_kd = excluded.mean_kd,
                    mean_kpm = excluded.mean_kpm,
                    mean_combat = excluded.mean_combat,
                    number_of_games = excluded.number_of_games,
                    last_updated = excluded.last_updated;
            END
        """)

        # Create views for player rankings
        cursor.execute("DROP VIEW IF EXISTS player_ranking_kills_per_minute")
        cursor.execute("""
            CREATE VIEW player_ranking_kills_per_minute AS
            SELECT
                player_id,
                player_name,
                COUNT(*) as games_played,
                SUM(kills) as total_kills,
                SUM(deaths) as total_deaths,
                AVG(kills_per_minute) as avg_kills_per_minute,
                AVG(combat_score) as avg_combat_score,
                AVG(kill_death_ratio) as avg_kd_ratio,
                RANK() OVER (ORDER BY AVG(kills_per_minute) DESC) as rank
            FROM player_stats
            WHERE kills_per_minute > 0
            GROUP BY player_id, player_name
            HAVING games_played >= 3
            ORDER BY avg_kills_per_minute DESC
        """)

        cursor.execute("DROP VIEW IF EXISTS player_ranking_kd_ratio")
        cursor.execute("""
            CREATE VIEW player_ranking_kd_ratio AS
            SELECT
                player_id,
                player_name,
                COUNT(*) as games_played,
                SUM(kills) as total_kills,
                SUM(deaths) as total_deaths,
                CAST(SUM(kills) AS REAL) / NULLIF(SUM(deaths), 0) as overall_kd_ratio,
                AVG(kills_per_minute) as avg_kills_per_minute,
                AVG(combat_score) as avg_combat_score,
                RANK() OVER (ORDER BY CAST(SUM(kills) AS REAL) / NULLIF(SUM(deaths), 0) DESC) as rank
            FROM player_stats
            WHERE deaths > 0
            GROUP BY player_id, player_name
            HAVING games_played >= 3
            ORDER BY overall_kd_ratio DESC
        """)

        cursor.execute("DROP VIEW IF EXISTS player_ranking_combat_score")
        cursor.execute("""
            CREATE VIEW player_ranking_combat_score AS
            SELECT
                player_id,
                player_name,
                COUNT(*) as games_played,
                SUM(kills) as total_kills,
                SUM(deaths) as total_deaths,
                AVG(combat_score) as avg_combat_score,
                MAX(combat_score) as max_combat_score,
                AVG(kills_per_minute) as avg_kills_per_minute,
                AVG(kill_death_ratio) as avg_kd_ratio,
                RANK() OVER (ORDER BY AVG(combat_score) DESC) as rank
            FROM player_stats
            WHERE combat_score > 0
            GROUP BY player_id, player_name
            HAVING games_played >= 3
            ORDER BY avg_combat_score DESC
        """)

        conn.commit()
        conn.close()

    def increment_greeting(self, user_id: int, username: str):
        """Increment the greeting count for a user.

        Args:
            user_id: Discord user ID
            username: Discord username

        Returns:
            The new greeting count for the user
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT greeting_count FROM greeting_stats WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

        if result:
            # Update existing user
            new_count = result[0] + 1
            cursor.execute("""
                UPDATE greeting_stats
                SET greeting_count = ?, last_greeted = ?, username = ?
                WHERE user_id = ?
            """, (new_count, datetime.now(), username, user_id))
        else:
            # Insert new user
            new_count = 1
            cursor.execute("""
                INSERT INTO greeting_stats (user_id, username, greeting_count, last_greeted)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, new_count, datetime.now()))

        conn.commit()
        conn.close()

        return new_count

    def get_user_stats(self, user_id: int):
        """Get greeting statistics for a user.

        Args:
            user_id: Discord user ID

        Returns:
            Dictionary with user stats or None if user not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT username, greeting_count, last_greeted
            FROM greeting_stats
            WHERE user_id = ?
        """, (user_id,))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "username": result[0],
                "greeting_count": result[1],
                "last_greeted": result[2]
            }
        return None

    def get_all_stats(self):
        """Get greeting statistics for all users.

        Returns:
            List of dictionaries with user stats
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, username, greeting_count, last_greeted
            FROM greeting_stats
            ORDER BY greeting_count DESC
        """)

        results = cursor.fetchall()
        conn.close()

        return [
            {
                "user_id": row[0],
                "username": row[1],
                "greeting_count": row[2],
                "last_greeted": row[3]
            }
            for row in results
        ]

    # Server management methods

    def add_server(self, name: str, url: str, description: str, status: str, clan: str):
        """Add a new server to the database.

        Args:
            name: Server name
            url: Server URL
            description: Server description
            status: Server status (active/skip)
            clan: Clan/organization name

        Returns:
            The ID of the inserted server
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO servers (name, url, description, status, clan)
            VALUES (?, ?, ?, ?, ?)
        """, (name, url, description, status, clan))

        server_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return server_id

    def get_server(self, name: str):
        """Get a server by name.

        Args:
            name: Server name

        Returns:
            Dictionary with server data or None if not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, url, description, status, clan
            FROM servers
            WHERE name = ?
        """, (name,))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "id": result[0],
                "name": result[1],
                "url": result[2],
                "description": result[3],
                "status": result[4],
                "clan": result[5]
            }
        return None

    def get_all_servers(self, status_filter: str = None):
        """Get all servers from the database.

        Args:
            status_filter: Optional status filter (e.g., 'active', 'skip')

        Returns:
            List of dictionaries with server data
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        if status_filter:
            cursor.execute("""
                SELECT id, name, url, description, status, clan
                FROM servers
                WHERE status = ?
                ORDER BY name
            """, (status_filter,))
        else:
            cursor.execute("""
                SELECT id, name, url, description, status, clan
                FROM servers
                ORDER BY name
            """)

        results = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "name": row[1],
                "url": row[2],
                "description": row[3],
                "status": row[4],
                "clan": row[5]
            }
            for row in results
        ]

    def update_server_status(self, name: str, status: str):
        """Update server status.

        Args:
            name: Server name
            status: New status value

        Returns:
            True if updated, False if server not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE servers
            SET status = ?
            WHERE name = ?
        """, (status, name))

        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        return rows_affected > 0

    # Processed games management methods

    def is_game_processed(self, server_name: str, game_id: int):
        """Check if a game has already been processed.

        Args:
            server_name: Server name
            game_id: Game ID

        Returns:
            True if already processed, False otherwise
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 1 FROM processed_games
            WHERE server_name = ? AND game_id = ?
        """, (server_name, game_id))

        result = cursor.fetchone()
        conn.close()

        return result is not None

    def mark_game_processed(self, server_name: str, game_id: int, start_time: str, player_count: int):
        """Mark a game as processed.

        Args:
            server_name: Server name
            game_id: Game ID
            start_time: Game start time
            player_count: Number of players in the game

        Returns:
            The ID of the inserted record
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO processed_games (server_name, game_id, start_time, player_count)
            VALUES (?, ?, ?, ?)
        """, (server_name, game_id, start_time, player_count))

        record_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return record_id

    # Player stats management methods

    def add_player_stat(self, server_name: str, game_id: int, game_start_time: str,
                       player_id: str, player_name: str, kills: int, deaths: int,
                       kill_death_ratio: float, combat_score: int, support_score: int,
                       defense_score: int, kills_per_minute: float):
        """Add player statistics for a game.

        Args:
            server_name: Server name
            game_id: Game ID
            game_start_time: Game start time
            player_id: Player ID
            player_name: Player name
            kills: Number of kills
            deaths: Number of deaths
            kill_death_ratio: K/D ratio
            combat_score: Combat score
            support_score: Support score
            defense_score: Defense score
            kills_per_minute: Kills per minute

        Returns:
            The ID of the inserted record
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO player_stats
            (server_name, game_id, game_start_time, player_id, player_name,
             kills, deaths, kill_death_ratio, combat_score, support_score,
             defense_score, kills_per_minute)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (server_name, game_id, game_start_time, player_id, player_name,
              kills, deaths, kill_death_ratio, combat_score, support_score,
              defense_score, kills_per_minute))

        stat_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return stat_id

    def get_player_stats(self, player_id: str = None, server_name: str = None, limit: int = 100):
        """Get player statistics.

        Args:
            player_id: Optional player ID filter
            server_name: Optional server name filter
            limit: Maximum number of records to return

        Returns:
            List of dictionaries with player stats
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT id, server_name, game_id, game_start_time, player_id, player_name,
                   kills, deaths, kill_death_ratio, combat_score, support_score,
                   defense_score, kills_per_minute
            FROM player_stats
            WHERE 1=1
        """
        params = []

        if player_id:
            query += " AND player_id = ?"
            params.append(player_id)

        if server_name:
            query += " AND server_name = ?"
            params.append(server_name)

        query += " ORDER BY game_start_time DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "server_name": row[1],
                "game_id": row[2],
                "game_start_time": row[3],
                "player_id": row[4],
                "player_name": row[5],
                "kills": row[6],
                "deaths": row[7],
                "kill_death_ratio": row[8],
                "combat_score": row[9],
                "support_score": row[10],
                "defense_score": row[11],
                "kills_per_minute": row[12]
            }
            for row in results
        ]

    # Player ranking methods

    def get_top_players_by_kpm(self, limit: int = 50):
        """Get top players ranked by kills per minute.

        Args:
            limit: Maximum number of players to return

        Returns:
            List of dictionaries with player rankings
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT player_id, player_name, games_played, total_kills, total_deaths,
                   avg_kills_per_minute, avg_combat_score, avg_kd_ratio, rank
            FROM player_ranking_kills_per_minute
            LIMIT ?
        """, (limit,))

        results = cursor.fetchall()
        conn.close()

        return [
            {
                "rank": row[8],
                "player_id": row[0],
                "player_name": row[1],
                "games_played": row[2],
                "total_kills": row[3],
                "total_deaths": row[4],
                "avg_kills_per_minute": round(row[5], 3),
                "avg_combat_score": round(row[6], 1),
                "avg_kd_ratio": round(row[7], 2)
            }
            for row in results
        ]

    def get_top_players_by_kd(self, limit: int = 50):
        """Get top players ranked by K/D ratio.

        Args:
            limit: Maximum number of players to return

        Returns:
            List of dictionaries with player rankings
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT player_id, player_name, games_played, total_kills, total_deaths,
                   overall_kd_ratio, avg_kills_per_minute, avg_combat_score, rank
            FROM player_ranking_kd_ratio
            LIMIT ?
        """, (limit,))

        results = cursor.fetchall()
        conn.close()

        return [
            {
                "rank": row[8],
                "player_id": row[0],
                "player_name": row[1],
                "games_played": row[2],
                "total_kills": row[3],
                "total_deaths": row[4],
                "overall_kd_ratio": round(row[5], 2),
                "avg_kills_per_minute": round(row[6], 3),
                "avg_combat_score": round(row[7], 1)
            }
            for row in results
        ]

    def get_top_players_by_combat(self, limit: int = 50):
        """Get top players ranked by combat score.

        Args:
            limit: Maximum number of players to return

        Returns:
            List of dictionaries with player rankings
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT player_id, player_name, games_played, total_kills, total_deaths,
                   avg_combat_score, max_combat_score, avg_kills_per_minute, avg_kd_ratio, rank
            FROM player_ranking_combat_score
            LIMIT ?
        """, (limit,))

        results = cursor.fetchall()
        conn.close()

        return [
            {
                "rank": row[9],
                "player_id": row[0],
                "player_name": row[1],
                "games_played": row[2],
                "total_kills": row[3],
                "total_deaths": row[4],
                "avg_combat_score": round(row[5], 1),
                "max_combat_score": row[6],
                "avg_kills_per_minute": round(row[7], 3),
                "avg_kd_ratio": round(row[8], 2)
            }
            for row in results
        ]

    # Player watchlist methods

    def get_watchlist(self, follow_only: bool = False):
        """Get all players in the watchlist.

        Args:
            follow_only: If True, only return players with follow=1

        Returns:
            List of dictionaries with player watchlist data
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        if follow_only:
            query = """
                SELECT player_id, player_name, mean_kd, mean_kpm, mean_combat,
                       number_of_games, follow, last_updated
                FROM player_watchlist
                WHERE follow = 1
                ORDER BY mean_combat DESC
            """
        else:
            query = """
                SELECT player_id, player_name, mean_kd, mean_kpm, mean_combat,
                       number_of_games, follow, last_updated
                FROM player_watchlist
                ORDER BY mean_combat DESC
            """

        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()

        return [
            {
                "player_id": row[0],
                "player_name": row[1],
                "mean_kd": round(row[2], 2) if row[2] else None,
                "mean_kpm": round(row[3], 3) if row[3] else None,
                "mean_combat": round(row[4], 1) if row[4] else None,
                "number_of_games": row[5],
                "follow": row[6],
                "last_updated": row[7]
            }
            for row in results
        ]

    def set_player_follow(self, player_id: str, follow: bool):
        """Set the follow status for a player.

        Args:
            player_id: Player ID
            follow: True to follow, False to unfollow, None to clear

        Returns:
            True if successful, False if player not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        follow_value = 1 if follow else 0

        cursor.execute("""
            UPDATE player_watchlist
            SET follow = ?
            WHERE player_id = ?
        """, (follow_value, player_id))

        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        return rows_affected > 0

    def clear_player_follow(self, player_id: str):
        """Clear the follow status for a player (set to NULL).

        Args:
            player_id: Player ID

        Returns:
            True if successful, False if player not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE player_watchlist
            SET follow = NULL
            WHERE player_id = ?
        """, (player_id,))

        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        return rows_affected > 0

    def get_player_watchlist_info(self, player_id: str):
        """Get watchlist info for a specific player.

        Args:
            player_id: Player ID

        Returns:
            Dictionary with player watchlist data or None if not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT player_id, player_name, mean_kd, mean_kpm, mean_combat,
                   number_of_games, follow, last_updated
            FROM player_watchlist
            WHERE player_id = ?
        """, (player_id,))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "player_id": result[0],
                "player_name": result[1],
                "mean_kd": round(result[2], 2) if result[2] else None,
                "mean_kpm": round(result[3], 3) if result[3] else None,
                "mean_combat": round(result[4], 1) if result[4] else None,
                "number_of_games": result[5],
                "follow": result[6],
                "last_updated": result[7]
            }
        return None

    def refresh_watchlist(self):
        """Refresh the entire watchlist from player_stats.

        This recalculates all statistics for all players.
        Preserves existing follow status.

        Returns:
            Number of players updated
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO player_watchlist (player_id, player_name, mean_kd, mean_kpm, mean_combat, number_of_games, last_updated)
            SELECT
                player_id,
                player_name,
                AVG(kill_death_ratio) as mean_kd,
                AVG(kills_per_minute) as mean_kpm,
                AVG(combat_score) as mean_combat,
                COUNT(*) as number_of_games,
                datetime('now') as last_updated
            FROM player_stats
            GROUP BY player_id, player_name
            ON CONFLICT(player_id) DO UPDATE SET
                player_name = excluded.player_name,
                mean_kd = excluded.mean_kd,
                mean_kpm = excluded.mean_kpm,
                mean_combat = excluded.mean_combat,
                number_of_games = excluded.number_of_games,
                last_updated = excluded.last_updated
        """)

        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        return rows_affected
