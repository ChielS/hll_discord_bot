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
- **Player Discovery** (`/top_players`): Discover top 5 neutral players to follow using interactive buttons
- **Player Management** (`/manage_followed`): Manage your followed players using interactive buttons
- **Server Management** (`/manage_servers`): Create, update, and delete servers using interactive modals
- **Data Collection** (`/collect_data`): Manually trigger data collection from active servers

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

#### `/top_players` - Discover Top Neutral Players

**Purpose:** Discover new players to follow from the untracked player pool.

**Parameters:**
- `kpi`: Ranking metric (required)
  - `Kills Per Minute (KPM)` - Best fraggers
  - `Kill/Death Ratio (K/D)` - Most efficient killers
  - `Combat Score` - Overall combat performance
- `min_games`: Minimum games played (default: 3)

**Examples:**
```
/top_players kpi:Combat Score min_games:5
/top_players kpi:KPM min_games:10
/top_players kpi:K/D min_games:3
```

**What happens:**
1. Bot displays an embed with a condensed table-like view
2. **Only shows neutral players** (`follow=null`) - untracked players
3. Filters players by minimum games
4. Each player shows on one line:
   - Rank and name in bold
   - Status indicator (always ○ = Neutral for this command)
   - Games played, KPM, K/D ratio, Combat score
5. Below the table, three buttons per player:
   - **[Follow PlayerName]** (green) - Start tracking this player
   - **[Unfollow PlayerName]** (red) - Mark as not interested
   - **[Clear PlayerName]** (gray) - Keep neutral (no change)
6. Click any button to update - changes apply immediately

**Example format:**
```
#1 PlayerName | ○ | Games: 10 | KPM: 1.234 | K/D: 2.34 | Combat: 567.8
[Follow PlayerName] [Unfollow PlayerName] [Clear PlayerName]
```

---

#### `/manage_followed` - Manage Followed Players

**Purpose:** View and update players you're already tracking.

**Parameters:** None

**Example:**
```
/manage_followed
```

**What happens:**
1. Bot displays an embed with your 5 most recently updated followed players
2. **Sorted by when you last changed their follow status** (most recent first)
3. **Only shows followed players** (`follow=true`) - players you're tracking
4. Each player shows on one line:
   - Rank (based on recency, not performance)
   - Name in bold
   - Status indicator (always ✓ = Following)
   - Games played, KPM, K/D ratio, Combat score
5. Below the table, three buttons per player:
   - **[Follow PlayerName]** (green) - Already following (disabled)
   - **[Unfollow PlayerName]** (red) - Stop tracking this player
   - **[Clear PlayerName]** (gray) - Reset to neutral
6. Click any button to update - changes apply immediately

**Example format:**
```
⭐ Followed Players
Sorted by most recently updated

#1 PlayerName | ✓ | Games: 10 | KPM: 1.234 | K/D: 2.34 | Combat: 567.8
[Follow PlayerName] [Unfollow PlayerName] [Clear PlayerName]

#2 AnotherPlayer | ✓ | Games: 8 | KPM: 0.987 | K/D: 1.89 | Combat: 432.1
[Follow AnotherPlayer] [Unfollow AnotherPlayer] [Clear AnotherPlayer]
```

**Note:** Shows your 5 most recently updated follows, making it easy to review and adjust your latest tracking decisions

---

**Both commands limited to top 5 players due to Discord component constraints**

---

### Data Collection Commands

#### `/collect_data` - Run Data Collection

**Purpose:** Manually trigger data collection from all active servers.

**Parameters:** None

**Example:**
```
/collect_data
```

**What happens:**

1. **Initial Response**
   - Bot acknowledges command
   - Shows "Starting data collection..." message
   - Warns that it may take several minutes

2. **Background Processing**
   - Runs `get_data_single_all.py` script
   - Fetches game data from all servers with `status='active'`
   - Processes games from newest to oldest
   - Stops at games older than 4 weeks
   - Only processes games with >60 players
   - Updates player watchlist automatically

3. **Completion Summary**
   - Embed shows last 10 lines of output
   - Displays any errors if they occurred
   - Shows exit code (0 = success)

**Example Response:**
```
📊 Data Collection Complete

Summary
```
2025-11-20 12:53:51 - INFO - Server fin complete: 78 games processed, 0 skipped
2025-11-20 12:53:51 - INFO - Total: 78 games, 6,072 players
2025-11-20 12:53:51 - INFO - Data collection complete
```

Exit code: 0
```

**Timeout:**
- Script has a 10-minute timeout
- If it takes longer, you'll get a timeout message
- Script may continue running in background

**Use Cases:**
- Manually update stats after adding new servers
- Collect data on-demand instead of waiting for cron
- Test data collection setup
- Refresh player statistics

**Note:** This runs the same script as the automated cron job

---

### Server Management Commands

#### `/manage_servers` - Manage Servers

**Purpose:** Create, update, and delete Hell Let Loose servers using an interactive interface.

**Parameters:** None

**Example:**
```
/manage_servers
```

**What happens:**

1. **Server Overview**
   - Bot displays an embed showing:
     - Total number of servers
     - Status summary (active vs skip)
     - First 10 servers listed

2. **Interactive Components**
   - **Dropdown menu** - Select a server to view/update/delete (shows up to 25 servers)
   - **Create button** - Add a new server

**Workflow:**

### Creating a New Server

1. Click **"Create New Server"** button
2. Modal opens with fields:
   - **Server Name** - Unique identifier (e.g., "fin")
   - **Server URL** - API endpoint (e.g., "http://65.109.128.186:1110/")
   - **Description** - Display name (e.g., "HLL FINLAND")
   - **Status** - Either "active" or "skip"
3. Submit modal
4. Server created and confirmed

### Updating a Server

1. Select server from dropdown menu
2. Bot shows server details with **"Update"** and **"Delete"** buttons
3. Click **"Update [ServerName]"** button
4. Modal opens pre-filled with current values:
   - Server URL
   - Description
   - Status
5. Edit fields and submit
6. Server updated and confirmed

### Deleting a Server

1. Select server from dropdown menu
2. Click **"Delete [ServerName]"** button
3. Server immediately deleted from database
4. Confirmation message displayed

**Example Interface:**
```
🖥️ Server Management
Total servers: 21

Status Summary
✅ Active: 3
⏭️ Skip: 18

Servers (showing first 10)
✅ fin - HLL FINLAND
⏭️ crow - Crow Server
✅ test - Test Server
...

[Dropdown: Select a server...]
[Create New Server]
```

**Benefits:**
- ✅ **No file uploads** - Everything done through Discord UI
- ✅ **Instant feedback** - See changes immediately
- ✅ **Pre-filled forms** - Update modal shows current values
- ✅ **Safe deletion** - One-click delete with confirmation
- ✅ **Visual status** - See active/skip at a glance

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

### Test Server YAML Generation

```bash
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
