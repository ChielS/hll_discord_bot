# Hell Let Loose Discord Bot

A Discord bot for Hell Let Loose that collects player statistics from game servers, maintains a player watchlist, and provides ranking data through Discord slash commands.

## Features

### Player Statistics Collection
- Automatically fetches game data from Hell Let Loose servers
- Tracks player performance: kills, deaths, K/D ratio, combat/support/defense scores, kills per minute
- Filters games by date (last 2-4 weeks) and minimum player count (>60 players)
- Stores all data in SQLite database

### Player Watchlist
- Automatically tracks all players who appear in collected games
- Calculate mean statistics: K/D ratio, KPM, combat score
- Mark players to follow/unfollow
- Auto-updates when new game data is collected

### Discord Commands
- **Player Rankings**: Get top N players by KPM, K/D, or Combat Score as YAML files
- **Server Management**: View and update server status (active/skip) via YAML files
- **Watchlist Management**: Edit player follow status via YAML file workflow

### Database Views
- Pre-built ranking views for quick queries
- Player statistics aggregated across all games
- Automatic ranking by KPM, K/D ratio, and combat score

## Requirements

- **Python 3.9 or higher**
- **uv package manager** (for dependency management)
- **Discord bot token** (from Discord Developer Portal)
- **Raspberry Pi** (recommended) or any Linux/macOS/Windows system

## Installation

### 1. Install uv Package Manager

**On Linux/macOS (including Raspberry Pi):**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Or using pip:**
```bash
pip install uv
```

### 2. Clone the Repository

```bash
git clone <your-repo-url>
cd hll_discord_bot
```

### 3. Install Dependencies

```bash
uv sync
```

This will install:
- `discord.py` - Discord bot framework
- `python-dotenv` - Environment variable management
- `pyyaml` - YAML file handling
- `requests` - HTTP requests for game data

## Discord Bot Setup

### 1. Create Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** and give it a name (e.g., "HLL Stats Bot")
3. Go to the **"Bot"** section and click **"Add Bot"**

### 2. Configure Bot Permissions

1. Under **"Privileged Gateway Intents"**, enable:
   - ✅ Message Content Intent

2. Under **"Bot Permissions"**, select:
   - ✅ Send Messages
   - ✅ Attach Files
   - ✅ Use Slash Commands

### 3. Get Bot Token

1. In the **"Bot"** section, click **"Reset Token"**
2. **Copy the token** (you'll need this for the `.env` file)
3. ⚠️ **Never share this token publicly!**

### 4. Invite Bot to Your Server

1. Go to **"OAuth2"** > **"URL Generator"**
2. Select scopes:
   - ✅ `bot`
   - ✅ `applications.commands`
3. Select permissions:
   - ✅ Send Messages
   - ✅ Attach Files
   - ✅ Use Slash Commands
4. **Copy the generated URL** and open it in your browser
5. Select your Discord server and authorize the bot

## Configuration

### 1. Create Environment File

```bash
cp .env.example .env
```

### 2. Add Discord Token

Edit `.env` and add your bot token:
```
DISCORD_TOKEN=your_actual_token_here
```

### 3. Initialize Database with Servers

The `servers.yaml` file contains Hell Let Loose server information. Load it into the database:

```bash
uv run load_servers.py
```

This will:
- Create the SQLite database (`bot_data.db`)
- Load all servers from `servers.yaml`
- Initialize database tables and views

**Expected output:**
```
Added server: crow (Crow Server)
Added server: fin (HLL FINLAND)
...
Successfully loaded 21 servers into the database.

Database Summary:
  Total servers: 21
  Active servers: 1
  Skip servers: 20
```

## Running the Bot

### Option 1: Run Directly (Development)

```bash
uv run bot.py
```

**Expected output:**
```
Slash commands synced!
Logged in as HLL Stats Bot (ID: 123456789...)
------
```

The bot is now running and will respond to Discord slash commands!

### Option 2: Run as Background Service (Production)

For Raspberry Pi or Linux servers, set up a systemd service:

#### Create Service File

```bash
sudo nano /etc/systemd/system/hll-discord-bot.service
```

#### Add Configuration

```ini
[Unit]
Description=Hell Let Loose Discord Bot
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/hll_discord_bot
ExecStart=/home/pi/.local/bin/uv run bot.py
Restart=always
RestartSec=10
Environment="PATH=/home/pi/.local/bin:/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
```

**Note:** Adjust `User` and `WorkingDirectory` paths for your system.

#### Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable hll-discord-bot

# Start the service
sudo systemctl start hll-discord-bot

# Check status
sudo systemctl status hll-discord-bot
```

#### Service Management Commands

```bash
# View logs
sudo journalctl -u hll-discord-bot -f

# Restart service
sudo systemctl restart hll-discord-bot

# Stop service
sudo systemctl stop hll-discord-bot

# Disable service
sudo systemctl disable hll-discord-bot
```

## Collecting Game Data

### Manual Data Collection

Run the data collection script to fetch player statistics from active servers:

```bash
uv run get_data_single_all.py
```

This will:
- Fetch game data from all servers with `status='active'`
- Start with the newest games (highest game ID)
- Stop when games are older than 4 weeks
- Only process games with >60 players
- Extract player stats and store in database
- Skip already processed games

**Expected output:**
```
2025-11-20 12:52:40 - INFO - Starting game data collection...
2025-11-20 12:52:40 - INFO - Found 1 active servers
2025-11-20 12:52:40 - INFO - Processing server: fin
2025-11-20 12:52:41 - INFO - Max game ID for fin: 6665
2025-11-20 12:52:41 - INFO - Processing game 6664 (78 players, 2025-11-19 19:45:25)
2025-11-20 12:52:41 - INFO - Game 6664 processed: 78 players stored
...
2025-11-20 12:53:51 - INFO - Server fin complete: 78 games processed, 0 skipped
```

### Automated Data Collection (Cron)

Set up a cron job to run data collection automatically:

```bash
crontab -e
```

Add this line to run every 6 hours:
```
0 */6 * * * cd /home/pi/hll_discord_bot && /home/pi/.local/bin/uv run get_data_single_all.py >> /home/pi/hll_discord_bot/logs/data_collection.log 2>&1
```

Create logs directory:
```bash
mkdir -p logs
```

### Initialize Player Watchlist

After collecting game data, populate the watchlist:

```bash
uv run manage_watchlist.py
```

This will:
- Create watchlist entries for all players
- Calculate mean statistics (K/D, KPM, combat score)
- Display top players

## Discord Commands Usage

Once the bot is running and invited to your Discord server:

### Player Ranking Commands

#### `/top_players` - Get Top Players by KPI

**Parameters:**
- `kpi`: Ranking metric (required)
  - `Kills Per Minute (KPM)` - Best fraggers
  - `Kill/Death Ratio (K/D)` - Most efficient killers
  - `Combat Score` - Overall combat performance
- `limit`: Number of players (default: 50)
- `min_games`: Minimum games played (default: 3)

**Examples:**
```
/top_players kpi:Combat Score limit:50 min_games:5
/top_players kpi:KPM limit:25 min_games:10
/top_players kpi:K/D limit:100 min_games:3
```

**What happens:**
1. Bot generates a YAML file with top N players
2. Only includes players with `follow=null` or `follow=true`
3. Filters players by minimum games
4. Sends file privately (ephemeral - only you see it)

**Sample YAML:**
```yaml
ranking_type: Combat Score
total_players: 50
min_games_filter: 5
instructions: Edit the 'follow' field for any player (true/false/null), then upload this file using /update_watchlist
players:
- rank: 1
  player_id: fc5eb4f3d7e154f3b95a8b870f041bb3
  player_name: Eversti Sandels
  number_of_games: 7
  mean_kpm: 0.551
  mean_kd: 24.43
  mean_combat: 843.1
  follow: true
```

#### `/update_watchlist` - Update Player Follow Status

**Parameters:**
- `file`: YAML file with edited follow status (required)

**Workflow:**
1. Use `/top_players` to download YAML file
2. Edit the `follow` field for any players:
   - `follow: true` - Mark as followed
   - `follow: false` - Mark as not followed
   - `follow: null` - Clear follow status
3. Upload edited file using `/update_watchlist file:[your_file.yaml]`
4. Bot confirms updates

**Example Response:**
```
✅ Updated 50 players in watchlist
```

### Server Management Commands

#### `/get_servers` - Get Server List

Downloads a YAML file with all servers and their current status.

**Example:**
```
/get_servers
```

**Sample YAML:**
```yaml
total_servers: 21
instructions: Edit the 'status' field for any server (active/skip), then upload this file using /update_servers
status_options:
- active
- skip
servers:
- name: fin
  url: http://65.109.128.186:1110/
  description: HLL FINLAND
  status: active
  clan: fin
```

#### `/update_servers` - Update Server Status

**Parameters:**
- `file`: YAML file with edited server status (required)

**Workflow:**
1. Use `/get_servers` to download YAML file
2. Edit the `status` field for any servers:
   - `status: active` - Enable data collection
   - `status: skip` - Disable data collection
3. Upload edited file using `/update_servers file:[your_file.yaml]`
4. Bot confirms updates

**Example Response:**
```
✅ Updated 21 servers
   - 3 set to active
   - 18 set to skip
```

### Greeting Commands

- `/hello` - Greet the bot and track your greeting count
- `/stats` - View your greeting statistics

## Database Schema

### Tables

**servers**
- Server configuration and status
- Fields: name, url, description, status, clan

**player_stats**
- Individual player performance per game
- Fields: server_name, game_id, game_start_time, player_id, player_name, kills, deaths, kill_death_ratio, combat_score, support_score, defense_score, kills_per_minute

**player_watchlist**
- Aggregated player statistics
- Auto-updated via database triggers
- Fields: player_id, player_name, mean_kd, mean_kpm, mean_combat, number_of_games, follow

**processed_games**
- Track which games have been processed
- Prevents duplicate data collection
- Fields: server_name, game_id, start_time, player_count, processed_at

### Views

**player_ranking_kills_per_minute**
- Ranks players by average KPM
- Filters: 3+ games, KPM > 0

**player_ranking_kd_ratio**
- Ranks players by overall K/D ratio
- Filters: 3+ games, deaths > 0

**player_ranking_combat_score**
- Ranks players by average combat score
- Filters: 3+ games, combat score > 0

## Management Scripts

### View Player Rankings

```bash
uv run show_rankings.py
```

Shows top 10 players by each metric (KPM, K/D, Combat).

### Manage Watchlist

```bash
uv run manage_watchlist.py
```

Refreshes watchlist and shows followed players.

### Test YAML Generation

```bash
# Test player rankings YAML
uv run test_yaml_generation.py

# Test servers YAML
uv run test_servers_yaml.py
```

## Project Structure

```
hll_discord_bot/
├── bot.py                          # Discord bot with slash commands
├── get_data_single_all.py          # Game data collection script
├── load_servers.py                 # Load servers from YAML into database
├── manage_watchlist.py             # Manage player watchlist
├── show_rankings.py                # Display player rankings
├── test_yaml_generation.py         # Test player ranking YAML generation
├── test_servers_yaml.py            # Test server YAML generation
├── database/
│   ├── __init__.py
│   └── db.py                       # SQLite database operations
├── servers.yaml                    # Server configuration file
├── .env                            # Environment variables (not in git)
├── .env.example                    # Environment template
├── .gitignore                      # Git ignore rules
├── pyproject.toml                  # uv package configuration
└── README.md                       # This file
```

## Deployment Checklist

- [ ] Install Python 3.9+ and uv
- [ ] Clone repository
- [ ] Run `uv sync` to install dependencies
- [ ] Create Discord bot application
- [ ] Enable Message Content Intent
- [ ] Copy bot token to `.env` file
- [ ] Invite bot to Discord server
- [ ] Run `uv run load_servers.py` to initialize database
- [ ] Edit `servers.yaml` and set desired servers to `status: active`
- [ ] Run `uv run load_servers.py` again to update server status
- [ ] Run `uv run get_data_single_all.py` to collect initial game data
- [ ] Run `uv run manage_watchlist.py` to populate watchlist
- [ ] Start bot with `uv run bot.py` or systemd service
- [ ] (Optional) Set up cron job for automated data collection
- [ ] Test Discord commands in your server

## Troubleshooting

### Bot Not Responding

**Problem:** Bot doesn't respond to slash commands

**Solutions:**
- Check bot is online: Look for green status in Discord
- Verify Message Content Intent is enabled in Developer Portal
- Wait 1-2 minutes after starting bot for commands to sync
- Try leaving and re-inviting the bot
- Check logs: `sudo journalctl -u hll-discord-bot -f`

### Database Errors

**Problem:** Database file permission errors

**Solutions:**
```bash
# Check ownership
ls -la bot_data.db

# Fix permissions
chmod 664 bot_data.db
chown pi:pi bot_data.db
```

### Data Collection Fails

**Problem:** get_data_single_all.py fails or returns no data

**Solutions:**
- Check server URLs are accessible: `curl <server_url>/api/get_scoreboard_maps?page=1&limit=10`
- Verify servers are marked as `status: active`
- Check date filter (default: 4 weeks) in get_data_single_all.py line 199
- Review logs for specific error messages

### Import Errors

**Problem:** ModuleNotFoundError

**Solution:**
```bash
# Reinstall dependencies
uv sync
```

### Service Won't Start

**Problem:** systemd service fails to start

**Solutions:**
```bash
# Check service status
sudo systemctl status hll-discord-bot

# View detailed logs
sudo journalctl -u hll-discord-bot -n 50

# Verify paths in service file
sudo nano /etc/systemd/system/hll-discord-bot.service

# Reload after changes
sudo systemctl daemon-reload
sudo systemctl restart hll-discord-bot
```

## Performance Notes

- **Database Size:** Expect ~1-2 MB per 1000 player records
- **Data Collection:** Processing 100 games takes ~2-3 minutes
- **Raspberry Pi:** Runs smoothly on Raspberry Pi 3B+ or newer
- **Memory Usage:** ~50-100 MB RAM for bot + data collection

## Security Notes

- Never commit `.env` file to git
- Keep Discord bot token secret
- Database contains player IDs (hashed) but no personal information
- Bot runs with minimal permissions (read/write to database, send Discord messages)

## License

MIT License

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review systemd/cron logs for errors
3. Verify Discord bot permissions
4. Check database file permissions
