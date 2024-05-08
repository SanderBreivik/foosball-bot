import os
import json
import random
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv, find_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Set up environment variables and logging
load_dotenv(find_dotenv())
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))

players = []

def assign_teams():
    random.shuffle(players)
    team1, team2 = players[:2], players[2:]
    logger.info(f"Teams assigned: Team 1 - {[player['name'] for player in team1]}, Team 2 - {[player['name'] for player in team2]}")
    return team1, team2

@app.route('/post_foosball', methods=['POST'])
def post_foosball():
    user_id = request.form.get('user_id')
    user_info = client.users_info(user=user_id)
    user_name = user_info['user']['name'] if user_info['ok'] else 'Unknown User'
    players.clear()
    players.append({'id': user_id, 'name': user_name})
    logger.info(f"{user_name} has initiated a foosball game.")

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"{user_name} har startet et foosballspill! Klikk for å delta:"}
        },
        {
            "type": "actions",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "Bli med!"}, "action_id": "join_game"}
            ]
        }
    ]

    try:
        response = client.chat_postMessage(
            channel='#foosball',
            blocks=blocks
        )
        logger.info("Foosball game invitation posted successfully.")
    except SlackApiError as e:
        logger.error(f"Failed to post foosball game invitation: {e.response['error']}")
        return jsonify({'error': e.response['error']}), 400

    return jsonify({'message': 'Message posted!'}), 200

@app.route('/slack/interactive', methods=['POST'])
def interactive():
    payload = json.loads(request.form['payload'])
    user_id = payload['user']['id']
    user_name = payload['user']['name']
    channel_id = payload['channel']['id']
    message_ts = payload['container']['message_ts']

    if len(players) < 4 and all(player['id'] != user_id for player in players):
        players.append({'id': user_id, 'name': user_name})
        logger.info(f"{user_name} joined the game, total players now: {len(players)}.")

    players_list = ", ".join([player['name'] for player in players])
    text = f"Spillere: {players_list}"

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text}
        }
    ]

    if len(players) < 4:
        join_button = {
            "type": "actions",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "Bli med!"}, "action_id": "join_game"}
            ]
        }
        blocks.append(join_button)
    else:
        team1, team2 = assign_teams()
        team_text = "\nLag 1: {}".format(", ".join(["<@{}>".format(player['id']) for player in team1]))
        team_text += "\nLag 2: {}".format(", ".join(["<@{}>".format(player['id']) for player in team2]))
        team_text += "\nAlle plasser er fylt. Lagene er klare!"
        logger.info("All player spots filled and teams announced.")
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": team_text}
        })

    try:
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            blocks=blocks
        )
        logger.info("Game status message updated successfully.")
    except SlackApiError as e:
        logger.error(f"Failed to update game status message: {e.response['error']}")
        return jsonify({'error': f'Failed to update message: {e.response["error"]}'}), 400
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

    return jsonify({'status': 'Message updated successfully'}), 200


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 3000)))
