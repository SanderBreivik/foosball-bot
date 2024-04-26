import os
import json
import logging
import threading
import random
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from dotenv import load_dotenv, find_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from threading import Lock

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))

class MatchSpots:
    def __init__(self):
        self.lock = Lock()
        self.spots = {f"spot{i}": None for i in range(1, 5)}

    def assign_spot(self, user_id, user_name):
        with self.lock:
            spot = self.get_available_spot()
            if spot:
                self.spots[spot] = {"user_id": user_id, "name": user_name}
                return spot
            return None
    
    def already_assigned(self, user_id):
        return any(spot and spot['user_id'] == user_id for spot in self.spots.values())

    def get_available_spot(self):
        for spot, value in self.spots.items():
            if value is None:
                return spot
        return None
    
    def isFull(self):
        return all(spot and spot['user_id'] for spot in self.spots.values())
    
    def get_user_ids(self):
        return [spot['user_id'] for spot in self.spots.values() if spot]
    
    

match_spots = MatchSpots()

def cancel_match_if_incomplete(channel_id, message_ts):
    threading.Timer(300, check_spots_and_update, args=(channel_id, message_ts)).start()

def check_spots_and_update(channel_id, message_ts):
    if all(spot and spot['user_id'] for spot in match_spots.values()):
        logging.info("All spots are filled. Match confirmed.")
        return
    try:
        text = "Kamp kanselert, ikke nok spillere. Prøv igjen senere!"
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=text
        )
        logging.info("Updated original message to show match cancellation.")
    except SlackApiError as e:
        logging.error(f"Failed to update original message: {e.response['error']}")

import random

def announce_complete_match(channel_id):
    logger.info(f"Announcing complete match. Match spots: {match_spots.spots}")
    user_ids = match_spots.get_user_ids()  
    random.shuffle(user_ids)
    
    # Splitting the players into two teams
    mid_point = len(user_ids) // 2
    team1 = user_ids[:mid_point]
    team2 = user_ids[mid_point:]
    
    # Generating the message with tagged users for each team
    team1_tags = ' '.join([f"<@{player}>" for player in team1])
    team2_tags = ' '.join([f"<@{player}>" for player in team2])
    
    message_text = (f"The match is set!\n"
                    f"Team 1: {team1_tags}\n"
                    f"Team 2: {team2_tags}")

    try:
        client.chat_postMessage(
            channel=channel_id,
            text=message_text
        )
        logging.info("Announced complete match with all players tagged and teams formed.")
    except SlackApiError as e:
        logging.error(f"Failed to announce complete match: {e.response['error']}")

@app.route('/post_foosball', methods=['POST'])
def post_foosball():
    user_id = request.form.get('user_id')
    user_info = client.users_info(user=user_id)
    user_name = user_info['user']['name'] if user_info['ok'] else 'Unknown User'

    if match_spots.already_assigned(user_id):
        logger.info(f"User {user_name} has already joined the foosball match.")
        return jsonify({'message': 'User already joined the match.'}), 200
    else:
        match_spots.assign_spot(user_id, user_name)
        logger.info(f"User {user_name} has joined the foosball match. Match spots: {match_spots.spots}")
        
    logger.info(f"User {user_name} has joined the foosball match. Match spots: {match_spots.spots}")
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "Bli med på foosball da! Velg en ledig spot:"}
        },
        {
            "type": "actions",
            "block_id": "foosball_select",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": f"{user_name} (selected)"}, "value": "spot1", "action_id": "disabled-spot1", "style": "danger"},
                {"type": "button", "text": {"type": "plain_text", "text": "Spot 2"}, "value": "spot2", "action_id": "spot2"},
                {"type": "button", "text": {"type": "plain_text", "text": "Spot 3"}, "value": "spot3", "action_id": "spot3"},
                {"type": "button", "text": {"type": "plain_text", "text": "Spot 4"}, "value": "spot4", "action_id": "spot4"}
            ]
        }
    ]
    try:
        response = client.chat_postMessage(
            channel='#foosball',
            text="Bli med på foosball da! Velg en ledig spot:",
            blocks=blocks
        )
        cancel_match_if_incomplete(response['channel'], response['ts'])
    except SlackApiError as e:
        logging.error(f"Failed to post message: {e.response['error']}")
        return jsonify({'error': e.response['error']}), 400
    logging.info(f"Message posted!")
    return jsonify({'message': 'Message posted!'}), 200

@app.route('/slack/interactive', methods=['POST'])
def interactive():
    payload = json.loads(request.form['payload'])
    user_id = payload['user']['id']
    user_name = payload['user']['name']
    action_id = payload['actions'][0]['action_id']
    channel_id = payload['channel']['id']
    message_ts = payload['container']['message_ts']

    blocks = payload['message']['blocks']
    spot = match_spots.assign_spot(user_id, user_name)
    if spot:
        logger.info(f"User {user_name} has joined the foosball match. Match spots: {match_spots.spots}")
    else:
        logger.info(f"No available spots for user {user_name}.")

    for block in blocks:
        if block['type'] == 'actions':
            for element in block['elements']:
                if element['action_id'] == action_id:
                    element['text']['text'] = f"{user_name} (selected)"
                    element['style'] = 'danger'
                    element['action_id'] = f"disabled-{element['value']}"

    if (match_spots.isFull()):
        logger.info("All spots are filled, announcing the match.")
        announce_complete_match(channel_id)
    else:
        try:
            client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text="Select your position:",
                blocks=blocks
            )
            logging.info(f"Message updated: {message_ts}")
        except SlackApiError as e:
            logging.error(f"Failed to update message: {e.response['error']}, blocks: {blocks}")
            return jsonify({'error': f'Failed to update message: {e.response["error"]}'}), 400
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return jsonify({'error': 'An error occurred'}), 500

    return jsonify({'status': 'Message updated successfully'}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 3000)))
