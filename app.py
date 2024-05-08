import os
import json
import random
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv, find_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv(find_dotenv())
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))

players = []

def assign_teams():
    random.shuffle(players)
    return players[:2], players[2:]

@app.route('/post_foosball', methods=['POST'])
def post_foosball():
    user_id = request.form.get('user_id')
    user_info = client.users_info(user=user_id)
    user_name = user_info['user']['name'] if user_info['ok'] else 'Unknown User'
    players.clear()
    players.append({'id': user_id, 'name': user_name})  # Add the original poster automatically
    
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
    
    response = client.chat_postMessage(
        channel='#foosball',
        blocks=blocks
    )
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
        players_list = ", ".join([player['name'] for player in players])
        text = f"Spillere: {players_list}"

        if len(players) == 4:
            team1, team2 = assign_teams()
            text += f"\nLag 1: {', '.join([player['name'] for player in team1])}"
            text += f"\nLag 2: {', '.join([player['name'] for player in team2])}"
            text += "\nAlle plasser er fylt. Lagene er klare!"

        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            blocks=[{
                "type": "section",
                "text": {"type": "mrkdwn", "text": text}
            }]
        )
    return jsonify({'status': 'Message updated successfully'}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 3000)))
