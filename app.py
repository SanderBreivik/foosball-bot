from flask import Flask, request, jsonify
import os
import json
import random
import logging
import threading
from dotenv import load_dotenv, find_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from threading import Lock

# Set up environment variables and logging
load_dotenv(find_dotenv())
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))

players = []
players_lock = Lock()
current_team_message_ts = None

def check_foosball_status(channel_id, message_ts):
    if len(players) < 4:
        player_names = ", ".join([player['name'] for player in players]) if players else "Ingen"
        player_count = len(players)
        try:
            # Post a message indicating the game was cancelled due to insufficient players, 
            # and list the players who had signed up or mention that no one had signed up.
            cancellation_message = "Det har gått 5 minutter uten at alle plassene ble fylt opp. Kampen ble kansellert."
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

def assign_teams():
    random.shuffle(players)
    team1, team2 = players[:2], players[2:]
    logger.info(f"Teams assigned: Team 1 - {[player['name'] for player in team1]}, Team 2 - {[player['name'] for player in team2]}")
    return team1, team2

@app.route('/post_foosball', methods=['POST'])
def post_foosball():
    user_id = request.form.get('user_id')
    user_info = client.users_info(user=user_id)
    if user_info['ok']:
        user_name = user_info['user']['profile']['display_name'] or user_info['user']['real_name'] or user_info['user']['name']
    else:
        user_name = 'Unknown User'
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
            text="Foosball-invitasjon! ⚽",
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
    user_info = client.users_info(user=user_id)
    if user_info['ok']:
        user_name = user_info['user']['profile']['display_name'] or user_info['user']['real_name'] or user_info['user']['name']
    else:
        user_name = 'Unknown User'
    channel_id = payload['channel']['id']
    message_ts = payload['container']['message_ts']
    actions = payload.get('actions', [])
    if not actions:
        return jsonify({'error': 'No actions found in payload'}), 400

    action_ids = [action['action_id'] for action in actions]
    team_message_id = None
    with players_lock:
        if 'join_game' in action_ids:
            if len(players) < 4 and all(player['id'] != user_id for player in players):
                players.append({'id': user_id, 'name': user_name})
                logger.info(f"user object: {payload['user']}")
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
                logger.info("Game status message updated successfully.")
            
            if len(players) == 4:
                team1, team2 = assign_teams()
                team_text = "Lagene er klare!\nGrått lag 1 ⚪ (første spiller starter fremme): " + ", ".join([f"<@{player['id']}>" for player in team1])
                team_text += "\nBrunt lag 2 🟤 (første spiller starter fremme): " + ", ".join([f"<@{player['id']}>" for player in team2])
                shuffle_button = {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button", 
                            "text": {"type": "plain_text", "text": "Stokk om lagene"},
                            "action_id": "shuffle_teams"
                        }
                    ]
                }
                try:
                    response = client.chat_postMessage(
                        channel=channel_id,
                        text="Nytt foosballspill starter snart! 🚀",
                        blocks=json.dumps([{"type": "section", "text": {"type": "mrkdwn", "text": team_text}}, shuffle_button])
                    )
                    logger.info("New game announcement with team assignments posted and players notified.")
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
        
        if 'shuffle_teams' in action_ids and len(players) == 4:
            if players_lock.locked():
                # Notify the client that a shuffle operation is already in progress
                text = "Et annet lag er allerede i ferd med å bli stokket om. Prøv igjen senere."
                client.chat_postMessage(channel=channel_id, text=text)
                logger.info("Shuffle operation is already in progress. Notified the requester accordingly.")
                return jsonify({'status': 'Shuffle in progress'}), 200

            with players_lock:
               
                team1, team2 = assign_teams()  
                logger.info("Teams shuffled.")    
                team_text = "Lagene er blitt stokket om!\nGrått lag 1 ⚪: " + ", ".join([f"<@{player['id']}>" for player in team1])
                team_text += "\nBrunt lag 2 🟤: " + ", ".join([f"<@{player['id']}>" for player in team2])
                try:
                    response = client.chat_postMessage(
                        channel=channel_id,
                        text="Nytt foosballspill starter snart! 🚀",
                        blocks=json.dumps([{"type": "section", "text": {"type": "mrkdwn", "text": team_text}}, shuffle_button])
                    )
                    current_team_message_ts = response['ts']
                    logger.info("New game announcement with team assignments posted and players notified.")
                    if current_team_message_ts is not None:
                        try:
                            # Delete the previous team announcement message
                            client.chat_delete(channel=channel_id, ts=current_team_message_ts)
                            logger.info("Previous team announcement message deleted successfully.")
                        except SlackApiError as e:
                            logger.error(f"Failed to delete previous team announcement: {e.response['error']}")
                            return jsonify({'error': f'Failed to delete message: {e.response["error"]}'}), 400
                        except Exception as e:
                            logger.error(f"An unexpected error occurred while deleting message: {e}")
                            return jsonify({'error': 'An unexpected error occurred'}), 500
                except SlackApiError as e:
                    logger.error(f"Failed to post new game announcement or remove old message: {e.response['error']}")
                    return jsonify({'error': f'Failed to post/remove message: {e.response["error"]}'}), 400
                except Exception as e:
                    logger.error(f"An unexpected error occurred: {e}")
                    return jsonify({'error': 'An unexpected error occurred'}), 500
                return jsonify({'status': 'Action completed successfully'}), 200
            

        


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 3000)))
