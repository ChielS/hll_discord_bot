"""Discord bot for Hell Let Loose - Main entry point."""
import os
import io
import json
import asyncio
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


class TopPlayersView(discord.ui.View):
    """View for displaying and updating top players."""

    def __init__(self, players: list, kpi: str, kpi_name: str, min_games: int):
        """Initialize the view with player data.

        Args:
            players: List of player dictionaries with stats
            kpi: KPI identifier (kpm, kd, combat)
            kpi_name: Display name of the KPI
            min_games: Minimum games filter
        """
        super().__init__(timeout=300)  # 5 minute timeout
        self.players = players
        self.kpi = kpi
        self.kpi_name = kpi_name
        self.min_games = min_games

        # Add 3 buttons for each player (max 5 players = 15 buttons)
        for idx, player in enumerate(players[:5], 1):
            current_follow = player['follow']

            # Truncate player name if too long (Discord button label limit is 80 chars)
            player_name = player['player_name'][:25] if len(player['player_name']) > 25 else player['player_name']

            # Follow button (green, disabled if currently following)
            follow_btn = discord.ui.Button(
                label=f"Follow {player_name}",
                style=discord.ButtonStyle.success,
                custom_id=f"follow_{player['player_id']}",
                disabled=(current_follow == 1),
                row=idx - 1
            )
            follow_btn.callback = lambda i, p=player: self.button_callback(i, p, "follow")
            self.add_item(follow_btn)

            # Unfollow button (red, disabled if currently unfollowed)
            unfollow_btn = discord.ui.Button(
                label=f"Unfollow {player_name}",
                style=discord.ButtonStyle.danger,
                custom_id=f"unfollow_{player['player_id']}",
                disabled=(current_follow == 0),
                row=idx - 1
            )
            unfollow_btn.callback = lambda i, p=player: self.button_callback(i, p, "unfollow")
            self.add_item(unfollow_btn)

            # Clear button (gray, disabled if currently null)
            clear_btn = discord.ui.Button(
                label=f"Clear {player_name}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"clear_{player['player_id']}",
                disabled=(current_follow is None),
                row=idx - 1
            )
            clear_btn.callback = lambda i, p=player: self.button_callback(i, p, "clear")
            self.add_item(clear_btn)

    async def button_callback(self, interaction: discord.Interaction, player: dict, action: str):
        """Handle button click.

        Args:
            interaction: Discord interaction
            player: Player data dictionary
            action: Action to perform (follow, unfollow, clear)
        """
        try:
            # Update database
            if action == "follow":
                success = bot.db.set_player_follow(player['player_id'], True)
                status_text = "now following"
                new_follow_status = 1
            elif action == "unfollow":
                success = bot.db.set_player_follow(player['player_id'], False)
                status_text = "unfollowed"
                new_follow_status = 0
            else:  # clear
                success = bot.db.clear_player_follow(player['player_id'])
                status_text = "status cleared"
                new_follow_status = None

            if success:
                # Update button states
                player['follow'] = new_follow_status

                # Rebuild view with updated button states
                for item in self.children:
                    if isinstance(item, discord.ui.Button):
                        # Check if this button belongs to the updated player
                        if player['player_id'] in item.custom_id:
                            if 'follow_' in item.custom_id and action == 'follow':
                                item.disabled = True
                            elif 'follow_' in item.custom_id:
                                item.disabled = False

                            if 'unfollow_' in item.custom_id and action == 'unfollow':
                                item.disabled = True
                            elif 'unfollow_' in item.custom_id:
                                item.disabled = False

                            if 'clear_' in item.custom_id and action == 'clear':
                                item.disabled = True
                            elif 'clear_' in item.custom_id:
                                item.disabled = False

                # Update the message with new button states
                await interaction.response.edit_message(view=self)

                # Send confirmation
                await interaction.followup.send(
                    f"✅ **{player['player_name']}** {status_text}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"⚠️ Player not found in database",
                    ephemeral=True
                )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error updating player: {e}",
                ephemeral=True
            )


@bot.tree.command(name="top_players", description="Discover top neutral players by KPI")
@app_commands.describe(
    kpi="Select ranking metric: kpm (kills per minute), kd (kill/death ratio), or combat (combat score)",
    min_games="Minimum number of games played (default: 3)"
)
@app_commands.choices(kpi=[
    app_commands.Choice(name="Kills Per Minute (KPM)", value="kpm"),
    app_commands.Choice(name="Kill/Death Ratio (K/D)", value="kd"),
    app_commands.Choice(name="Combat Score", value="combat")
])
async def top_players(interaction: discord.Interaction, kpi: str, min_games: int = 3):
    """View and follow top 5 neutral players by KPI (only shows untracked players).

    Args:
        interaction: Discord interaction object
        kpi: The KPI to rank by (kpm, kd, combat)
        min_games: Minimum number of games played
    """
    await interaction.response.defer()

    try:
        # Get watchlist (only follow=NULL - neutral players)
        all_players = bot.db.get_watchlist(follow_only=False)

        # Filter to only include follow=NULL and minimum games
        filtered_players = [
            p for p in all_players
            if p['follow'] is None and p['number_of_games'] >= min_games
        ]

        # Sort by the requested KPI
        if kpi == "kpm":
            sorted_players = sorted(filtered_players, key=lambda x: x['mean_kpm'] or 0, reverse=True)
            kpi_name = "Kills Per Minute (KPM)"
            kpi_emoji = "🔫"
        elif kpi == "kd":
            sorted_players = sorted(filtered_players, key=lambda x: x['mean_kd'] or 0, reverse=True)
            kpi_name = "Kill/Death Ratio (K/D)"
            kpi_emoji = "⚔️"
        else:  # combat
            sorted_players = sorted(filtered_players, key=lambda x: x['mean_combat'] or 0, reverse=True)
            kpi_name = "Combat Score"
            kpi_emoji = "🎯"

        # Take top 5 only
        top_5 = sorted_players[:5]

        if not top_5:
            await interaction.followup.send(
                "No neutral players found matching criteria. All top players may already be tracked."
            )
            return

        # Create embed with condensed table format
        embed = discord.Embed(
            title=f"{kpi_emoji} Top Players - {kpi_name}",
            color=discord.Color.blue()
        )

        # Build condensed list
        player_lines = []
        for idx, player in enumerate(top_5, 1):
            # Follow status indicator
            if player['follow'] == 1:
                status = "✓"
            elif player['follow'] == 0:
                status = "✗"
            else:
                status = "○"

            # Format stats
            kpm = f"{player['mean_kpm']:.3f}" if player['mean_kpm'] else "N/A"
            kd = f"{player['mean_kd']:.2f}" if player['mean_kd'] else "N/A"
            combat = f"{player['mean_combat']:.1f}" if player['mean_combat'] else "N/A"

            # Create condensed line
            line = f"**#{idx} {player['player_name']}** | {status} | Games: {player['number_of_games']} | KPM: {kpm} | K/D: {kd} | Combat: {combat}"
            player_lines.append(line)

        # Set description with all players
        embed.description = "\n\n".join(player_lines)
        embed.set_footer(text=f"Min games: {min_games} • Click buttons to update • Active button is disabled")

        # Create view with buttons
        view = TopPlayersView(top_5, kpi, kpi_name, min_games)

        # Send embed with view
        await interaction.followup.send(
            embed=embed,
            view=view
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Error loading players: {e}"
        )


@bot.tree.command(name="manage_followed", description="Manage followed players (sorted by when followed)")
async def manage_followed(interaction: discord.Interaction):
    """View and manage followed players (sorted by most recently followed).

    Args:
        interaction: Discord interaction object
    """
    await interaction.response.defer()

    try:
        # Get watchlist (only follow=1 - followed players, ordered by last_updated)
        all_players = bot.db.get_watchlist(follow_only=True, order_by_updated=True)

        # Take top 5 only
        top_5 = all_players[:5]

        if not top_5:
            await interaction.followup.send(
                "No followed players found. Use /top_players to discover players to follow."
            )
            return

        # Create embed with condensed table format
        embed = discord.Embed(
            title="⭐ Followed Players",
            description="Sorted by most recently updated",
            color=discord.Color.green()
        )

        # Build condensed list
        player_lines = []
        for idx, player in enumerate(top_5, 1):
            # Format stats
            kpm = f"{player['mean_kpm']:.3f}" if player['mean_kpm'] else "N/A"
            kd = f"{player['mean_kd']:.2f}" if player['mean_kd'] else "N/A"
            combat = f"{player['mean_combat']:.1f}" if player['mean_combat'] else "N/A"

            # Create condensed line (all followed, so status is always ✓)
            line = f"**#{idx} {player['player_name']}** | ✓ | Games: {player['number_of_games']} | KPM: {kpm} | K/D: {kd} | Combat: {combat}"
            player_lines.append(line)

        # Set description with all players
        embed.description = "\n\n".join(player_lines)
        embed.set_footer(text="Showing 5 most recently updated • Click buttons to update")

        # Create view with buttons (pass dummy kpi values since not used)
        view = TopPlayersView(top_5, "combat", "Combat Score", 0)

        # Send embed with view
        await interaction.followup.send(
            embed=embed,
            view=view
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Error loading followed players: {e}"
        )


class ServerCreateModal(discord.ui.Modal, title="Create New Server"):
    """Modal for creating a new server."""

    name = discord.ui.TextInput(
        label="Server Name",
        placeholder="e.g., fin",
        max_length=50,
        required=True
    )

    url = discord.ui.TextInput(
        label="Server URL",
        placeholder="http://example.com:1110/",
        max_length=200,
        required=True
    )

    description = discord.ui.TextInput(
        label="Description",
        placeholder="e.g., HLL FINLAND",
        max_length=100,
        required=True
    )

    status = discord.ui.TextInput(
        label="Status (active/skip)",
        placeholder="active or skip",
        default="skip",
        max_length=10,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        try:
            # Validate status
            status_value = self.status.value.strip().lower()
            if status_value not in ['active', 'skip']:
                await interaction.response.send_message(
                    "❌ Status must be 'active' or 'skip'",
                    ephemeral=True
                )
                return

            # Add server to database
            bot.db.add_server(
                self.name.value.strip(),
                self.url.value.strip(),
                self.description.value.strip(),
                status_value,
                ""
            )

            await interaction.response.send_message(
                f"✅ Server **{self.name.value}** created successfully!",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error creating server: {e}",
                ephemeral=True
            )


class ServerUpdateModal(discord.ui.Modal, title="Update Server"):
    """Modal for updating a server."""

    def __init__(self, server: dict):
        super().__init__()
        self.server_name = server['name']

        # Pre-fill with current values
        self.url = discord.ui.TextInput(
            label="Server URL",
            default=server['url'],
            max_length=200,
            required=True
        )
        self.add_item(self.url)

        self.description = discord.ui.TextInput(
            label="Description",
            default=server['description'],
            max_length=100,
            required=True
        )
        self.add_item(self.description)

        self.status = discord.ui.TextInput(
            label="Status (active/skip)",
            default=server['status'],
            max_length=10,
            required=True
        )
        self.add_item(self.status)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        try:
            # Validate status
            status_value = self.status.value.strip().lower()
            if status_value not in ['active', 'skip']:
                await interaction.response.send_message(
                    "❌ Status must be 'active' or 'skip'",
                    ephemeral=True
                )
                return

            # Update server (need to update the add_server method to handle updates)
            bot.db.add_server(
                self.server_name,
                self.url.value.strip(),
                self.description.value.strip(),
                status_value,
                ""
            )

            await interaction.response.send_message(
                f"✅ Server **{self.server_name}** updated successfully!",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error updating server: {e}",
                ephemeral=True
            )


class ServerManagementView(discord.ui.View):
    """View for managing servers."""

    def __init__(self, servers: list):
        super().__init__(timeout=300)
        self.servers = {s['name']: s for s in servers}

        # Add server selection dropdown (max 25 options)
        if servers:
            options = [
                discord.SelectOption(
                    label=f"{s['name'][:80]}",
                    description=f"{s['status']} | {s['description'][:80]}",
                    value=s['name']
                )
                for s in servers[:25]
            ]

            select = discord.ui.Select(
                placeholder="Select a server to update or delete...",
                options=options,
                custom_id="server_select"
            )
            select.callback = self.select_callback
            self.add_item(select)

        # Add Create button
        create_btn = discord.ui.Button(
            label="Create New Server",
            style=discord.ButtonStyle.success,
            custom_id="create_server"
        )
        create_btn.callback = self.create_callback
        self.add_item(create_btn)

    async def select_callback(self, interaction: discord.Interaction):
        """Handle server selection."""
        server_name = interaction.data['values'][0]
        server = self.servers.get(server_name)

        if not server:
            await interaction.response.send_message(
                "❌ Server not found",
                ephemeral=True
            )
            return

        # Create view with Update and Delete buttons
        view = discord.ui.View(timeout=60)

        update_btn = discord.ui.Button(
            label=f"Update {server_name}",
            style=discord.ButtonStyle.primary
        )
        update_btn.callback = lambda i: self.update_callback(i, server)
        view.add_item(update_btn)

        delete_btn = discord.ui.Button(
            label=f"Delete {server_name}",
            style=discord.ButtonStyle.danger
        )
        delete_btn.callback = lambda i: self.delete_callback(i, server)
        view.add_item(delete_btn)

        await interaction.response.send_message(
            f"**{server['name']}**\n"
            f"📍 URL: {server['url']}\n"
            f"📝 Description: {server['description']}\n"
            f"🔧 Status: {server['status']}\n\n"
            f"What would you like to do?",
            view=view,
            ephemeral=True
        )

    async def create_callback(self, interaction: discord.Interaction):
        """Handle create button click."""
        modal = ServerCreateModal()
        await interaction.response.send_modal(modal)

    async def update_callback(self, interaction: discord.Interaction, server: dict):
        """Handle update button click."""
        modal = ServerUpdateModal(server)
        await interaction.response.send_modal(modal)

    async def delete_callback(self, interaction: discord.Interaction, server: dict):
        """Handle delete button click."""
        try:
            # Delete server from database (need to add delete method)
            conn = bot.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM servers WHERE name = ?", (server['name'],))
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()

            if rows_affected > 0:
                await interaction.response.send_message(
                    f"✅ Server **{server['name']}** deleted successfully!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"⚠️ Server **{server['name']}** not found",
                    ephemeral=True
                )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error deleting server: {e}",
                ephemeral=True
            )


@bot.tree.command(name="collect_data", description="Run data collection from active servers")
async def collect_data(interaction: discord.Interaction):
    """Trigger data collection script.

    Args:
        interaction: Discord interaction object
    """
    await interaction.response.defer()

    try:
        # Send initial message
        await interaction.followup.send(
            "🔄 Starting data collection...\n"
            "This may take several minutes depending on the number of active servers."
        )

        # Run the data collection script
        # Get the directory where bot.py is located
        bot_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(bot_dir, "get_data_single_all.py")

        # Run the script asynchronously to avoid blocking the event loop
        process = await asyncio.create_subprocess_exec(
            "python", script_path,
            cwd=bot_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Wait for completion with timeout (10 minutes)
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=600
            )
        except asyncio.TimeoutError:
            # Kill the process if it times out
            process.kill()
            await process.wait()
            await interaction.followup.send(
                "⏱️ Data collection timed out after 10 minutes.\n"
                "The process has been terminated."
            )
            return

        # Decode output
        stdout_text = stdout.decode('utf-8') if stdout else ""
        stderr_text = stderr.decode('utf-8') if stderr else ""

        # Parse the output to get summary
        output_lines = stdout_text.strip().split('\n') if stdout_text else []
        error_lines = stderr_text.strip().split('\n') if stderr_text else []

        # Create response embed
        embed = discord.Embed(
            title="📊 Data Collection Complete",
            color=discord.Color.green() if process.returncode == 0 else discord.Color.red()
        )

        # Add summary from last few lines of output
        if output_lines:
            summary = "\n".join(output_lines[-10:])  # Last 10 lines
            embed.add_field(
                name="Summary",
                value=f"```\n{summary[:1000]}\n```",
                inline=False
            )

        # Add errors if any
        if process.returncode != 0 and error_lines:
            error_msg = "\n".join(error_lines[-5:])  # Last 5 error lines
            embed.add_field(
                name="❌ Errors",
                value=f"```\n{error_msg[:1000]}\n```",
                inline=False
            )

        embed.set_footer(text=f"Exit code: {process.returncode}")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(
            f"❌ Error running data collection: {e}"
        )


@bot.tree.command(name="manage_servers", description="Manage servers (create, update, delete)")
async def manage_servers(interaction: discord.Interaction):
    """Manage servers using interactive interface.

    Args:
        interaction: Discord interaction object
    """
    await interaction.response.defer()

    try:
        # Get all servers
        servers = bot.db.get_all_servers()

        # Create embed with server list
        embed = discord.Embed(
            title="🖥️ Server Management",
            description=f"Total servers: **{len(servers)}**",
            color=discord.Color.blue()
        )

        # Add server summary
        active_count = sum(1 for s in servers if s['status'] == 'active')
        skip_count = len(servers) - active_count

        embed.add_field(
            name="Status Summary",
            value=f"✅ Active: {active_count}\n⏭️ Skip: {skip_count}",
            inline=False
        )

        # Show first 10 servers in embed
        if servers:
            server_list = []
            for server in servers[:10]:
                status_emoji = "✅" if server['status'] == 'active' else "⏭️"
                server_list.append(f"{status_emoji} **{server['name']}** - {server['description']}")

            embed.add_field(
                name="Servers (showing first 10)",
                value="\n".join(server_list),
                inline=False
            )

            if len(servers) > 10:
                embed.set_footer(text=f"... and {len(servers) - 10} more servers")

        # Create view
        view = ServerManagementView(servers)

        # Send embed with view
        await interaction.followup.send(
            embed=embed,
            view=view
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Error loading servers: {e}"
        )


def main():
    """Main function to run the bot."""
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
