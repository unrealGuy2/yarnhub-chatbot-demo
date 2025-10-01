import os
import time
import re
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# --- SETUP ---
load_dotenv()

app = Flask(__name__)
CORS(app)

# --- Your boss's Assistant ID ---
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# Initialize the OpenAI client
client = openai.OpenAI()

# --- CLEANING FUNCTION ---
def clean_response(text: str) -> str:
    """
    Removes all [source] references and any bracketed numbers like [1], [2], etc.
    Also cleans up spaces.
    """
    # Remove [source] or [sources]
    text = re.sub(r"\[source[s]?\]", "", text, flags=re.IGNORECASE)

    # Remove numeric citations like [1], [12], [34]
    text = re.sub(r"\[\d+\]", "", text)

    # Remove any leftover [ ... ] completely
    text = re.sub(r"\[[^\]]*\]", "", text)

    # Fix spaces before punctuation (e.g., "game ." -> "game.")
    text = re.sub(r"\s+([.,!?])", r"\1", text)

    # Collapse multiple spaces
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()

# --- THE WEBHOOK ---
@app.route("/webhook", methods=["POST"])
def handle_webhook():
    try:
        data = request.get_json()
        user_message = data.get("message")

        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        # Step 1: Create a new Thread (a conversation)
        thread = client.beta.threads.create()

        # Step 2: Add the user's message to the Thread
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )

        # Step 3: Run the Assistant on this Thread
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )

        # Step 4: Wait for the Assistant to finish processing
        while run.status in ["queued", "in_progress"]:
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            time.sleep(0.5)

        # Step 5: Retrieve the messages from the Thread
        messages = client.beta.threads.messages.list(thread_id=thread.id)

        # Step 6: Get the latest message from the Assistant
        ai_reply = messages.data[0].content[0].text.value

        # --- Clean the reply ---
        ai_reply = clean_response(ai_reply)

        return jsonify({"reply": ai_reply})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# --- Run server ---
if __name__ == "__main__":
    app.run(port=5001, debug=True)
