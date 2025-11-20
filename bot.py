"""Discord bot for Hell Let Loose - Main entry point."""
import os
import io
import yaml
import discord
from discord import app_commands
from dotenv import load_dotenv
from database.db import Database

# Load environment variables from .env file
load_dotenv()

# Get Discord token from environment
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables. Please create a .env file.")


class HLLBot(discord.Client):
    """Hell Let Loose Discord Bot."""

    def __init__(self):
        """Initialize the bot with required intents."""
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        self.db = Database()

    async def setup_hook(self):
        """Setup hook to sync slash commands."""
        await self.tree.sync()
        print("Slash commands synced!")

    async def on_ready(self):
        """Event handler for when the bot is ready."""
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")


# Initialize bot
bot = HLLBot()


@bot.tree.command(name="hello", description="Greet the bot and get a friendly response!")
async def hello(interaction: discord.Interaction):
    """Slash command to greet the bot.

    Args:
        interaction: Discord interaction object
    """
    user = interaction.user
    user_id = user.id
    username = user.name

    # Increment greeting count in database
    greeting_count = bot.db.increment_greeting(user_id, username)

    # Create response message
    if greeting_count == 1:
        response = f"Hello {username}! Nice to meet you for the first time! 👋"
    else:
        response = f"Hello {username}! This is greeting number {greeting_count} from you! 👋"

    await interaction.response.send_message(response)


@bot.tree.command(name="stats", description="View your greeting statistics")
async def stats(interaction: discord.Interaction):
    """Slash command to view greeting statistics.

    Args:
        interaction: Discord interaction object
    """
    user_id = interaction.user.id
    user_stats = bot.db.get_user_stats(user_id)

    if user_stats:
        response = (
            f"📊 **Your Greeting Stats**\n"
            f"Total greetings: {user_stats['greeting_count']}\n"
            f"Last greeted: {user_stats['last_greeted']}"
        )
    else:
        response = "You haven't greeted me yet! Use `/hello` to say hi! 👋"

    await interaction.response.send_message(response, ephemeral=True)


@bot.tree.command(name="top_players", description="Get top N players by KPI (returns YAML file)")
@app_commands.describe(
    kpi="Select ranking metric: kpm (kills per minute), kd (kill/death ratio), or combat (combat score)",
    limit="Number of top players to return (default: 50)",
    min_games="Minimum number of games played (default: 3)"
)
@app_commands.choices(kpi=[
    app_commands.Choice(name="Kills Per Minute (KPM)", value="kpm"),
    app_commands.Choice(name="Kill/Death Ratio (K/D)", value="kd"),
    app_commands.Choice(name="Combat Score", value="combat")
])
async def top_players(interaction: discord.Interaction, kpi: str, limit: int = 50, min_games: int = 3):
    """Get top N players by KPI as YAML file.

    Args:
        interaction: Discord interaction object
        kpi: The KPI to rank by (kpm, kd, combat)
        limit: Number of players to return
        min_games: Minimum number of games played
    """
    await interaction.response.defer(ephemeral=True)

    try:
        # Get watchlist (only follow=NULL or follow=1)
        all_players = bot.db.get_watchlist(follow_only=False)

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

        if not top_n:
            await interaction.followup.send("No players found in watchlist.", ephemeral=True)
            return

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

        # Convert to YAML
        yaml_str = yaml.dump(yaml_data, default_flow_style=False, sort_keys=False, allow_unicode=True)

        # Create file
        file_content = io.BytesIO(yaml_str.encode('utf-8'))
        file_content.seek(0)

        filename = f"top_{limit}_{kpi}_players.yaml"
        file = discord.File(file_content, filename=filename)

        await interaction.followup.send(
            f"📊 Top {len(top_n)} players by {kpi_name}\n"
            f"📈 Minimum games: {min_games}",
            file=file,
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(f"Error generating player list: {e}", ephemeral=True)


@bot.tree.command(name="update_watchlist", description="Update player follow status from YAML file")
@app_commands.describe(
    file="The YAML file with updated follow status"
)
async def update_watchlist(interaction: discord.Interaction, file: discord.Attachment):
    """Update watchlist from uploaded YAML file.

    Args:
        interaction: Discord interaction object
        file: The uploaded YAML file
    """
    await interaction.response.defer(ephemeral=True)

    try:
        # Check file extension
        if not file.filename.endswith(('.yaml', '.yml')):
            await interaction.followup.send("❌ Please upload a YAML file (.yaml or .yml)", ephemeral=True)
            return

        # Download and parse YAML
        file_content = await file.read()
        yaml_data = yaml.safe_load(file_content.decode('utf-8'))

        if 'players' not in yaml_data:
            await interaction.followup.send("❌ Invalid YAML format: 'players' key not found", ephemeral=True)
            return

        # Update database
        updated_count = 0
        errors = []

        for player in yaml_data['players']:
            player_id = player.get('player_id')
            follow_value = player.get('follow')

            if not player_id:
                continue

            try:
                if follow_value is None:
                    # Clear follow status
                    if bot.db.clear_player_follow(player_id):
                        updated_count += 1
                else:
                    # Set follow status (True or False)
                    if bot.db.set_player_follow(player_id, follow_value):
                        updated_count += 1
            except Exception as e:
                errors.append(f"Error updating {player_id}: {e}")

        # Send response
        response = f"✅ Updated {updated_count} players in watchlist"
        if errors:
            error_msg = "\n".join(errors[:5])  # Show first 5 errors
            response += f"\n\n⚠️ Errors:\n{error_msg}"
            if len(errors) > 5:
                response += f"\n... and {len(errors) - 5} more errors"

        await interaction.followup.send(response, ephemeral=True)

    except yaml.YAMLError as e:
        await interaction.followup.send(f"❌ Invalid YAML file: {e}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error updating watchlist: {e}", ephemeral=True)


@bot.tree.command(name="get_servers", description="Get all servers as YAML file")
async def get_servers(interaction: discord.Interaction):
    """Get all servers as YAML file for editing.

    Args:
        interaction: Discord interaction object
    """
    await interaction.response.defer(ephemeral=True)

    try:
        # Get all servers
        servers = bot.db.get_all_servers()

        if not servers:
            await interaction.followup.send("No servers found in database.", ephemeral=True)
            return

        # Create YAML data
        yaml_data = {
            "total_servers": len(servers),
            "instructions": "Edit the 'status' field for any server (active/skip), then upload this file using /update_servers",
            "status_options": ["active", "skip"],
            "servers": []
        }

        for server in servers:
            server_data = {
                "name": server['name'],
                "url": server['url'],
                "description": server['description'],
                "status": server['status'],
                "clan": server['clan']
            }
            yaml_data['servers'].append(server_data)

        # Convert to YAML
        yaml_str = yaml.dump(yaml_data, default_flow_style=False, sort_keys=False, allow_unicode=True)

        # Create file
        file_content = io.BytesIO(yaml_str.encode('utf-8'))
        file_content.seek(0)

        filename = "servers.yaml"
        file = discord.File(file_content, filename=filename)

        await interaction.followup.send(
            f"🖥️ All {len(servers)} servers\n\nEdit the `status` field (active/skip) and upload using `/update_servers`",
            file=file,
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(f"Error generating server list: {e}", ephemeral=True)


@bot.tree.command(name="update_servers", description="Update server status from YAML file")
@app_commands.describe(
    file="The YAML file with updated server status"
)
async def update_servers(interaction: discord.Interaction, file: discord.Attachment):
    """Update server status from uploaded YAML file.

    Args:
        interaction: Discord interaction object
        file: The uploaded YAML file
    """
    await interaction.response.defer(ephemeral=True)

    try:
        # Check file extension
        if not file.filename.endswith(('.yaml', '.yml')):
            await interaction.followup.send("❌ Please upload a YAML file (.yaml or .yml)", ephemeral=True)
            return

        # Download and parse YAML
        file_content = await file.read()
        yaml_data = yaml.safe_load(file_content.decode('utf-8'))

        if 'servers' not in yaml_data:
            await interaction.followup.send("❌ Invalid YAML format: 'servers' key not found", ephemeral=True)
            return

        # Update database
        updated_count = 0
        errors = []
        active_count = 0
        skip_count = 0

        for server in yaml_data['servers']:
            server_name = server.get('name')
            status = server.get('status')

            if not server_name or not status:
                continue

            # Validate status
            if status not in ['active', 'skip']:
                errors.append(f"Invalid status for {server_name}: {status} (must be 'active' or 'skip')")
                continue

            try:
                if bot.db.update_server_status(server_name, status):
                    updated_count += 1
                    if status == 'active':
                        active_count += 1
                    else:
                        skip_count += 1
                else:
                    errors.append(f"Server not found: {server_name}")
            except Exception as e:
                errors.append(f"Error updating {server_name}: {e}")

        # Send response
        response = f"✅ Updated {updated_count} servers\n"
        response += f"   - {active_count} set to active\n"
        response += f"   - {skip_count} set to skip"

        if errors:
            error_msg = "\n".join(errors[:5])  # Show first 5 errors
            response += f"\n\n⚠️ Errors:\n{error_msg}"
            if len(errors) > 5:
                response += f"\n... and {len(errors) - 5} more errors"

        await interaction.followup.send(response, ephemeral=True)

    except yaml.YAMLError as e:
        await interaction.followup.send(f"❌ Invalid YAML file: {e}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error updating servers: {e}", ephemeral=True)


def main():
    """Main function to run the bot."""
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
