from flask import Flask, request, jsonify
import os
import json
import random
import logging
import threading
from dotenv import load_dotenv, find_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Set up environment variables and logging
load_dotenv(find_dotenv())
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
current_timer = None
players = []

def check_foosball_status(channel_id, message_ts, due_to_join=False):
    global current_timer

    if len(players) < 4:
        # Cancel the timer if this check was triggered by a player joining
        if due_to_join and current_timer:
            current_timer.cancel()

        player_names = ", ".join([player['name'] for player in players]) if players else "Ingen"
        player_count = len(players)

        if not due_to_join:
            # This block is only executed if the timer naturally expired
            try:
                cancellation_message = "Det har gått 5 minutter uten at alle plassene ble fylt opp. Kampen ble kanselert."
                if player_count > 0:
                    cancellation_message += f" Påmeldte spillere var: {player_names}."
                else:
                    cancellation_message += " Det var ingen påmeldte spillere."
                
                client.chat_postMessage(
                    channel=channel_id,
                    text=cancellation_message
                )
                client.chat_delete(channel=channel_id, ts=message_ts)
                logger.info("Game canceled due to incomplete participation.")
            except SlackApiError as e:
                logger.error(f"Failed to cancel game: {e.response['error']}")
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")

        # Restart the timer as long as there are less than 4 players and the check was due to a player joining
        if len(players) < 4 and due_to_join:
            current_timer = threading.Timer(300, check_foosball_status, args=[channel_id, message_ts])
            current_timer.start()

def assign_teams():
    random.shuffle(players)
    team1, team2 = players[:2], players[2:]
    logger.info(f"Teams assigned: Team 1 - {[player['name'] for player in team1]}, Team 2 - {[player['name'] for player in team2]}")
    return team1, team2

@app.route('/post_foosball', methods=['POST'])
def post_foosball():
    global current_timer
    current_timer = threading.Timer(300, check_foosball_status, args=[response['channel'], response['ts']])
    current_timer.start()
    
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
    
    threading.Timer(300, check_foosball_status, args=[response['channel'], response['ts']]).start()

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
        join_button = {
            "type": "actions",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "Bli med!"}, "action_id": "join_game"}
            ]
        }
        
        blocks.append(join_button)
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            blocks=blocks
        )
        check_foosball_status(channel_id, message_ts, due_to_join=True)
        logger.info("Game status message updated successfully.")
        
    if len(players) == 4:
        team1, team2 = assign_teams()
        team_text = "Lagene er klare!\nLag 1 (første spiller starter fremme): " + ", ".join([f"<@{player['id']}>" for player in team1])
        team_text += "\nLag 2 (første spiller starter fremme): " + ", ".join([f"<@{player['id']}>" for player in team2])

        try:
            # Posting a new message with user mentions to notify players
            response = client.chat_postMessage(
                channel=channel_id,
                text=team_text
            )
            logger.info("New game announcement with team assignments posted and players notified.")
            # Delete the original message
            client.chat_delete(
                channel=channel_id,
                ts=message_ts
            )
            logger.info("Original game invitation message removed.")
        except SlackApiError as e:
            logger.error(f"Failed to post new game announcement or remove old message: {e.response['error']}")
            return jsonify({'error': f'Failed to post/remove message: {e.response["error"]}'}), 400
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return jsonify({'error': 'An unexpected error occurred'}), 500

    return jsonify({'status': 'Action completed successfully'}), 200


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 3000)))