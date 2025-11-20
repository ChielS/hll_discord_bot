"""Manage the player watchlist."""
from database.db import Database


def show_watchlist(db: Database, follow_only: bool = False):
    """Display the player watchlist.

    Args:
        db: Database instance
        follow_only: If True, only show followed players
    """
    players = db.get_watchlist(follow_only=follow_only)

    if not players:
        print("No players in watchlist.")
        return

    title = "FOLLOWED PLAYERS" if follow_only else "PLAYER WATCHLIST"
    print("\n" + "="*100)
    print(title)
    print("="*100)
    print(f"{'Player Name':<30} {'Games':<7} {'Mean K/D':<10} {'Mean KPM':<10} {'Mean Combat':<12} {'Follow':<8}")
    print("-"*100)

    for player in players:
        follow_str = "✓" if player['follow'] == 1 else "✗" if player['follow'] == 0 else "-"
        print(f"{player['player_name'][:30]:<30} "
              f"{player['number_of_games']:<7} "
              f"{player['mean_kd'] if player['mean_kd'] else 'N/A':<10} "
              f"{player['mean_kpm'] if player['mean_kpm'] else 'N/A':<10} "
              f"{player['mean_combat'] if player['mean_combat'] else 'N/A':<12} "
              f"{follow_str:<8}")

    print("-"*100)
    print(f"Total players: {len(players)}")
    print("="*100 + "\n")


def refresh_watchlist(db: Database):
    """Refresh the watchlist from player_stats."""
    print("Refreshing watchlist from player_stats...")
    count = db.refresh_watchlist()
    print(f"Updated {count} players in watchlist.")


def follow_player(db: Database, player_id: str):
    """Mark a player as followed.

    Args:
        db: Database instance
        player_id: Player ID to follow
    """
    if db.set_player_follow(player_id, True):
        player = db.get_player_watchlist_info(player_id)
        print(f"✓ Now following: {player['player_name']}")
    else:
        print(f"✗ Player not found: {player_id}")


def unfollow_player(db: Database, player_id: str):
    """Unfollow a player.

    Args:
        db: Database instance
        player_id: Player ID to unfollow
    """
    if db.set_player_follow(player_id, False):
        player = db.get_player_watchlist_info(player_id)
        print(f"✗ Unfollowed: {player['player_name']}")
    else:
        print(f"✗ Player not found: {player_id}")


def show_player_info(db: Database, player_id: str):
    """Show detailed info for a player.

    Args:
        db: Database instance
        player_id: Player ID to lookup
    """
    player = db.get_player_watchlist_info(player_id)

    if not player:
        print(f"Player not found: {player_id}")
        return

    print("\n" + "="*60)
    print("PLAYER INFO")
    print("="*60)
    print(f"Name:         {player['player_name']}")
    print(f"Player ID:    {player['player_id']}")
    print(f"Games:        {player['number_of_games']}")
    print(f"Mean K/D:     {player['mean_kd']}")
    print(f"Mean KPM:     {player['mean_kpm']}")
    print(f"Mean Combat:  {player['mean_combat']}")
    follow_str = "Yes" if player['follow'] == 1 else "No" if player['follow'] == 0 else "Not set"
    print(f"Following:    {follow_str}")
    print(f"Updated:      {player['last_updated']}")
    print("="*60 + "\n")


def main():
    """Main function."""
    db = Database()

    # Refresh watchlist from existing data
    print("\n" + "="*100)
    print("WATCHLIST MANAGEMENT")
    print("="*100)

    refresh_watchlist(db)

    # Show all players
    show_watchlist(db, follow_only=False)

    # Example: Follow top 5 players by combat score
    print("\nFollowing top 5 players by combat score...")
    top_players = db.get_top_players_by_combat(5)
    for player in top_players:
        follow_player(db, player['player_id'])

    # Show followed players
    print("\n")
    show_watchlist(db, follow_only=True)


if __name__ == "__main__":
    main()
