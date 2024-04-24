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
        logging.info('Message posted successfully!')
    except SlackApiError as e:
        logging.error(f'Failed to post message: {e.response["error"]}')
        return jsonify({'error': e.response['error']}), 400
    return jsonify({'message': 'Message posted!'}), 200

@app.route('/slack/interactive', methods=['POST'])
def interactive():
    payload = json.loads(request.form['payload'])
    user_name = payload['user']['name']
    action_id = payload['actions'][0]['action_id']
    original_message = payload['message']

    updated_blocks = []
    for block in original_message['blocks']:
        if block['type'] == 'actions':
            updated_elements = []
            for element in block['elements']:
                new_element = element  # Copy the original element
                if element['action_id'] == action_id:
                    new_element['text']['text'] = f"{user_name} (selected)"  # Update the text
                    new_element['style'] = 'danger'  # Set style to danger
                    new_element['action_id'] = 'disabled'  # Disable further interactions
                updated_elements.append(new_element)
            block['elements'] = updated_elements
        updated_blocks.append(block)

    try:
        client.chat_update(
            channel=payload['channel']['id'],
            ts=payload['container']['message_ts'],
            text="Select your position:",
            blocks=updated_blocks
        )
        logger.info('Message updated successfully!')
        return jsonify({'status': 'Message updated successfully'}), 200
    except SlackApiError as e:
        logger.error(f'Failed to update message: {e.response["error"]}. Payload: {payload}')
        return jsonify({'error': f'Failed to update message: {e.response["error"]}'}), 400


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 3000)))