from flask import Flask, request, jsonify
import os
import json
import logging
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv, find_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))

# Dictionary to track the status of spots
match_spots = {
    "spot1": None,
    "spot2": None,
    "spot3": None,
    "spot4": None
}

def cancel_match_if_incomplete(channel_id, message_ts, scheduled_time):
    threading.Timer(300, check_spots_and_cancel, args=(channel_id, message_ts)).start()

def check_spots_and_cancel(channel_id, message_ts):
    # Check if all spots are filled
    if all(match_spots.values()):
        logging.info("All spots are filled. Match confirmed.")
        return
    try:
        client.chat_postMessage(
            channel=channel_id,
            text="Match cancelled: Not all spots were filled in time."
        )
        logging.info("Match cancelled due to incomplete team.")
    except SlackApiError as e:
        logging.error(f"Failed to cancel match: {e.response['error']}")

@app.route('/post_foosball', methods=['POST'])
def post_foosball():
    user_id = request.form.get('user_id')
    user_info = client.users_info(user=user_id)
    user_name = user_info['user']['name'] if user_info['ok'] else 'Unknown User'

    # User that triggered the command fills the first spot
    match_spots["spot1"] = user_name
    blocks = [
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
            channel='#test_chanel',
            text="Bli med på foosball da! Velg en ledig spot:",
            blocks=blocks
        )
        # Schedule a timer to check if the match is complete after 5 minutes
        scheduled_time = datetime.now() + timedelta(minutes=5)
        cancel_match_if_incomplete(response['channel'], response['ts'], scheduled_time)
    except SlackApiError as e:
        logging.error(f"Failed to post message: {e.response['error']}")
        return jsonify({'error': e.response['error']}), 400
    logging.info(f"Message posted!")
    return jsonify({'message': 'Message posted!'}), 200

@app.route('/slack/interactive', methods=['POST'])
def interactive():
    payload = json.loads(request.form['payload'])
    user_name = payload['user']['name']
    action_id = payload['actions'][0]['action_id']
    channel_id = payload['channel']['id']
    message_ts = payload['container']['message_ts']

    # Update the block that contains the button clicked
    blocks = payload['message']['blocks']
    for block in blocks:
        if block['type'] == 'actions':
            for element in block['elements']:
                if element['action_id'] == action_id:
                    element['text']['text'] = f"{user_name} (selected)"
                    element['style'] = 'danger'
                    element['action_id'] = f"disabled-{user_name}"
                    match_spots[element['value']] = user_name

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
