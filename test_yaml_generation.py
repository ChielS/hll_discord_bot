"""Test script to generate sample YAML for watchlist."""
import yaml
from database.db import Database


def generate_sample_yaml(kpi: str = "combat", limit: int = 10, min_games: int = 3):
    """Generate sample YAML file for testing.

    Args:
        kpi: The KPI to rank by (kpm, kd, combat)
        limit: Number of players to include
        min_games: Minimum number of games played
    """
    db = Database()

    # Get watchlist (only follow=NULL or follow=1)
    all_players = db.get_watchlist(follow_only=False)

    # Filter to only include follow=NULL or follow=1, and minimum games
    filtered_players = [
        p for p in all_players
        if (p['follow'] is None or p['follow'] == 1) and p['number_of_games'] >= min_games
    ]

    # Sort by the requested KPI
    if kpi == "kpm":
        sorted_players = sorted(filtered_players, key=lambda x: x['mean_kpm'] or 0, reverse=True)
        kpi_name = "Kills Per Minute"
    elif kpi == "kd":
        sorted_players = sorted(filtered_players, key=lambda x: x['mean_kd'] or 0, reverse=True)
        kpi_name = "Kill/Death Ratio"
    else:  # combat
        sorted_players = sorted(filtered_players, key=lambda x: x['mean_combat'] or 0, reverse=True)
        kpi_name = "Combat Score"

    # Take top N
    top_n = sorted_players[:limit]

    # Create YAML data
    yaml_data = {
        "ranking_type": kpi_name,
        "total_players": len(top_n),
        "min_games_filter": min_games,
        "instructions": "Edit the 'follow' field for any player (true/false/null), then upload this file using /update_watchlist",
        "players": []
    }

    for idx, player in enumerate(top_n, 1):
        player_data = {
            "rank": idx,
            "player_id": player['player_id'],
            "player_name": player['player_name'],
            "number_of_games": player['number_of_games'],
            "mean_kpm": float(player['mean_kpm']) if player['mean_kpm'] else None,
            "mean_kd": float(player['mean_kd']) if player['mean_kd'] else None,
            "mean_combat": float(player['mean_combat']) if player['mean_combat'] else None,
            "follow": True if player['follow'] == 1 else False if player['follow'] == 0 else None
        }
        yaml_data['players'].append(player_data)

    # Convert to YAML and save
    filename = f"sample_top_{limit}_{kpi}_players.yaml"
    with open(filename, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"✅ Generated {filename}")
    print(f"📊 Contains top {len(top_n)} players by {kpi_name}")
    print(f"📈 Minimum games: {min_games}")

    # Print first 3 players as preview
    print("\nPreview:")
    print("-" * 80)
    for player in yaml_data['players'][:3]:
        print(f"Rank {player['rank']}: {player['player_name']}")
        print(f"  Player ID: {player['player_id']}")
        print(f"  Games: {player['number_of_games']}")
        print(f"  KPM: {player['mean_kpm']}, K/D: {player['mean_kd']}, Combat: {player['mean_combat']}")
        print(f"  Follow: {player['follow']}")
        print()


def main():
    """Generate sample YAML files."""
    print("Generating sample YAML files...\n")

    # Generate samples for each KPI with default min_games=3
    generate_sample_yaml("combat", 10, min_games=3)
    print()
    generate_sample_yaml("kpm", 10, min_games=5)
    print()
    generate_sample_yaml("kd", 10, min_games=3)


if __name__ == "__main__":
    main()
