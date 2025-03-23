# BlackHorse Guild Loot System

A Discord bot for managing guild loot priorities and queues.

## Features
- Item priority queue management
- Player management
- Guild master commands
- Automatic queue updates
- Roll and raffle systems

## Setup
1. Clone this repository
2. Install requirements: `pip install -r requirements.txt`
3. Create a `.env` file with your Discord bot token:
   ```
   DISCORD_TOKEN=your_token_here
   ```
4. Run the bot: `python discordbot.py`

## Commands
### General Commands
- `/itemlist` - View all item priority lists
- `/itemqueue` - View priority list for specific item
- `/myloot` - View all your item priorities
- `/roll` - Roll the dice (1-100)
- `/raffle` - Random selection among guildies

### Guild Master Commands
- `/moveplayer` - Change player's position in queue
- `/pass` - Player passes on item
- `/bind` - Bind item to player
- `/additem` - Add new item to track
- `/deleteitem` - Delete item
- `/addplayer` - Add new guild member
- `/kickplayer` - Remove guild member

## Deployment
This bot is configured to run on Render.com. To deploy:
1. Fork this repository
2. Create a new Web Service on Render
3. Connect your GitHub repository
4. Add environment variable: `DISCORD_TOKEN`
5. Deploy! 