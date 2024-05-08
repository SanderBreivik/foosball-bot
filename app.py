import os
import json
import logging
import threading
from flask import Flask, request, jsonify
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
from threading import Lock

spot_lock = Lock()
spots_filled = {'spot1': None, 'spot2': None, 'spot3': None, 'spot4': None}


def check_foosball_status(channel_id, message_ts):
    with spot_lock:
        if not all(spot is not None for spot in spots_filled.values()):
            try:
                client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text="Det har gått 5 minutter uten at alle plassene ble fylt opp. Kampen ble kanselert"
                )
                logging.info(f"Game cancelled due to incomplete participation.")
            except SlackApiError as e:
                logging.error(f"Failed to cancel game: {e.response['error']}")
            except Exception as e:
                logging.error(f"An error occurred: {e}")


@app.route('/post_foosball', methods=['POST'])
def post_foosball():
    user_id = request.form.get('user_id')
    user_info = client.users_info(user=user_id)
    user_name = user_info['user']['name'] if user_info['ok'] else 'Unknown User'
    spots_filled.update({'spot1': None, 'spot2': None, 'spot3': None, 'spot4': None})

    spots_filled["spot1"] = user_id
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "Bli med på foosball da! Velg en ledig spot:"}
        },
        {
            "type": "actions",
            "block_id": "foosball_select",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": f"{user_name} (selected)"}, "value": "spot1", "action_id": f"disabled-{user_name}", "style": "danger"},
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
        threading.Timer(300, check_foosball_status, args=[response['channel'], response['ts']]).start()

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
    spot_id = payload['actions'][0]['value']

    blocks = payload['message']['blocks']

    with spot_lock:
        if spots_filled[spot_id] is None and spots_filled.values().count(user_id) == 0:
            spots_filled[spot_id] = user_id
            for block in blocks:
                if block['type'] == 'actions':
                    for element in block['elements']:
                        if element['action_id'] == action_id:
                            element['text']['text'] = f"{user_name} (selected)"
                            element['style'] = 'danger'
                            element['action_id'] = f"disabled-{user_name}"
        
    all_filled = all(spot is not None for spot in spots_filled.values())
    logger.info(f"Spots filled: {spots_filled}")
    

    try:
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text="Select your position:" if not all_filled else "All spots filled!",
            blocks=blocks
        )
        logging.info(f"Message updated: {message_ts}")
        if all_filled:
            tag_message = " ".join([f"<@{name}>" for name in spots_filled.values()])
            client.chat_postMessage(
                channel=channel_id,
                text=f"All spots are filled! Players: {tag_message}"
            )
    except SlackApiError as e:
        logging.error(f"Failed to update message: {e.response['error']}, blocks: {blocks}")
        return jsonify({'error': f'Failed to update message: {e.response["error"]}'}), 400
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({'error': 'An error occurred'}), 500

    return jsonify({'status': 'Message updated successfully'}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 3000)))
