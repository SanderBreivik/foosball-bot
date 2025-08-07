# Foosball Bot 🏓

A Slack bot that helps organize foosball games in your workspace. Players can join games, teams are automatically assigned, and game rules are randomly selected for added fun!

## Features

- 🎮 Start foosball games with a simple Slack command
- 👥 Interactive button-based player registration
- 🎯 Automatic team assignment (2v2)
- 🎲 Random game rules (including a rare "Super Crazy Mode")
- ⏰ Automatic game cancellation after 5 minutes if not enough players join
- 📢 Player notifications when teams are formed

## Prerequisites

- Python 3.7 or higher
- A Slack workspace with admin privileges
- Slack App configured with appropriate permissions

## Slack App Setup

### 1. Create a Slack App

1. Go to [Slack API](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name your app (e.g., "Foosball Bot") and select your workspace

### 2. Configure OAuth & Permissions

In your Slack app settings:

1. Navigate to **OAuth & Permissions**
2. Add the following **Bot Token Scopes**:
   - `channels:history`
   - `channels:read`
   - `chat:write`
   - `commands`
   - `users:read`

3. Install the app to your workspace and copy the **Bot User OAuth Token**

### 3. Create Slash Command

1. Navigate to **Slash Commands**
2. Click "Create New Command"
3. Configure:
   - **Command**: `/foosball`
   - **Request URL**: `https://your-app-url/post_foosball`
   - **Short Description**: "Start a foosball game"

### 4. Enable Interactivity

1. Navigate to **Interactivity & Shortcuts**
2. Turn on **Interactivity**
3. Set **Request URL**: `https://your-app-url/slack/interactive`

### 5. Create #foosball Channel

Create a `#foosball` channel in your Slack workspace where the bot will post game invitations.

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/foosball-bot.git
cd foosball-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```env
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
PORT=3000
```

Replace `xoxb-your-bot-token-here` with your actual Bot User OAuth Token from Slack.

### 4. Local Development

```bash
python app.py
```

The app will run on `http://localhost:3000`

For local development with Slack, you'll need to expose your local server using a tool like [ngrok](https://ngrok.com/):

```bash
ngrok http 3000
```

Use the ngrok HTTPS URL in your Slack app configuration.

## Deployment Options

### Deploy to Fly.io (Recommended)

This project includes a `fly.toml` configuration file for easy deployment to Fly.io.

1. Install [Fly CLI](https://fly.io/docs/getting-started/installing-flyctl/)
2. Login to Fly.io:
   ```bash
   flyctl auth login
   ```
3. Deploy the app:
   ```bash
   flyctl deploy
   ```
4. Set your environment variables:
   ```bash
   flyctl secrets set SLACK_BOT_TOKEN=xoxb-your-bot-token-here
   ```

### Deploy to Heroku

1. Install [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
2. Create a new Heroku app:
   ```bash
   heroku create your-foosball-bot
   ```
3. Set environment variables:
   ```bash
   heroku config:set SLACK_BOT_TOKEN=xoxb-your-bot-token-here
   ```
4. Deploy:
   ```bash
   git push heroku main
   ```

## Usage

### Starting a Game

1. In any Slack channel, type `/foosball`
2. The bot will post a message in the `#foosball` channel
3. Players click "Bli med!" (Join!) to register
4. When 4 players have joined, teams are automatically assigned
5. Game rules are randomly selected and displayed

### Game Rules

The bot randomly selects between two game modes:

- **Crazy Mode** (99% chance): First to 10 points, must win by 2. Scoring team switches positions.
- **Super Crazy Mode** (1% chance): Same as Crazy Mode, but the scoring player switches teams with the player in the corresponding position.

### Automatic Cancellation

If fewer than 4 players join within 5 minutes, the game is automatically cancelled and all registered players are notified.

## Project Structure

```
foosball-bot/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── Procfile           # Process configuration for deployment
├── fly.toml           # Fly.io deployment configuration
├── .env               # Environment variables (not in repo)
└── README.md          # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and commit: `git commit -am 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Create a Pull Request

## Troubleshooting

### Common Issues

1. **Bot not responding to slash command**
   - Verify the Request URL in Slack app settings
   - Check that your app is running and accessible
   - Ensure the bot is installed in your workspace

2. **Interactive buttons not working**
   - Verify the Interactivity Request URL is correct
   - Check that the bot has the necessary permissions

3. **Bot can't post messages**
   - Ensure the bot is a member of the `#foosball` channel
   - Verify `chat:write` permission is granted

### Logs

The application logs important events. Check your deployment platform's logs for debugging:

- **Fly.io**: `flyctl logs`
- **Heroku**: `heroku logs --tail`
- **Local**: Check your terminal output

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.
