from flask import Flask, request, jsonify
import os
import json
import logging
from dotenv import load_dotenv, find_dotenv
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))

@app.route('/post_foosball', methods=['POST'])
def post_foosball():
    try:
        response = client.chat_postMessage(
            channel='#test_chanel',
            text="Bli med på foosball da! Velg en ledig spot:",
            blocks=[
                {
                    "type": "actions",
                    "block_id": "foosball_select",
                    "elements": [
                        {"type": "button", "text": {"type": "plain_text", "text": "Spot 1"}, "value": "spot1", "action_id": "spot1"},
                        {"type": "button", "text": {"type": "plain_text", "text": "Spot 2"}, "value": "spot2", "action_id": "spot2"},
                        {"type": "button", "text": {"type": "plain_text", "text": "Spot 3"}, "value": "spot3", "action_id": "spot3"},
                        {"type": "button", "text": {"type": "plain_text", "text": "Spot 4"}, "value": "spot4", "action_id": "spot4"}
                    ]
                }
            ]
        )
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
                    element['action_id'] = "disabled-"+user_name  # This will effectively disable the button

    try:
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text="Select your position:",
            blocks=blocks
        )
        logging.info(f"Message updated: {message_ts}")
        return jsonify({'status': 'Message updated successfully'}), 200
    except SlackApiError as e:
        logging.error(f"Failed to update message: {e.response['error']}, blocks: {blocks}")
        return jsonify({'error': f'Failed to update message: {e.response["error"]}'}), 400
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({'error': 'An error occurred'}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 3000)))
