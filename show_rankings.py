"""Display player rankings from the database."""
from database.db import Database


def display_top_players_kpm(db: Database, limit: int = 10):
    """Display top players by kills per minute."""
    print("\n" + "="*80)
    print("TOP PLAYERS - KILLS PER MINUTE")
    print("="*80)
    print(f"{'Rank':<6} {'Player Name':<30} {'Games':<7} {'Kills':<7} {'Deaths':<7} {'KPM':<8} {'K/D':<7}")
    print("-"*80)

    players = db.get_top_players_by_kpm(limit)
    for player in players:
        print(f"{player['rank']:<6} "
              f"{player['player_name'][:30]:<30} "
              f"{player['games_played']:<7} "
              f"{player['total_kills']:<7} "
              f"{player['total_deaths']:<7} "
              f"{player['avg_kills_per_minute']:<8.3f} "
              f"{player['avg_kd_ratio']:<7.2f}")


def display_top_players_kd(db: Database, limit: int = 10):
    """Display top players by K/D ratio."""
    print("\n" + "="*80)
    print("TOP PLAYERS - K/D RATIO")
    print("="*80)
    print(f"{'Rank':<6} {'Player Name':<30} {'Games':<7} {'Kills':<7} {'Deaths':<7} {'K/D':<7} {'KPM':<8}")
    print("-"*80)

    players = db.get_top_players_by_kd(limit)
    for player in players:
        print(f"{player['rank']:<6} "
              f"{player['player_name'][:30]:<30} "
              f"{player['games_played']:<7} "
              f"{player['total_kills']:<7} "
              f"{player['total_deaths']:<7} "
              f"{player['overall_kd_ratio']:<7.2f} "
              f"{player['avg_kills_per_minute']:<8.3f}")


def display_top_players_combat(db: Database, limit: int = 10):
    """Display top players by combat score."""
    print("\n" + "="*80)
    print("TOP PLAYERS - COMBAT SCORE")
    print("="*80)
    print(f"{'Rank':<6} {'Player Name':<30} {'Games':<7} {'Avg Combat':<12} {'Max Combat':<12} {'K/D':<7}")
    print("-"*80)

    players = db.get_top_players_by_combat(limit)
    for player in players:
        print(f"{player['rank']:<6} "
              f"{player['player_name'][:30]:<30} "
              f"{player['games_played']:<7} "
              f"{player['avg_combat_score']:<12.1f} "
              f"{player['max_combat_score']:<12} "
              f"{player['avg_kd_ratio']:<7.2f}")


def main():
    """Display all rankings."""
    db = Database()

    print("\nGenerating player rankings...")
    print("(Only showing players with 3+ games)")

    display_top_players_kpm(db, limit=10)
    display_top_players_kd(db, limit=10)
    display_top_players_combat(db, limit=10)

    print("\n" + "="*80)
    print("Rankings complete!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
