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

# --- Your Assistant ID ---
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# Initialize OpenAI client
client = openai.OpenAI()

# --- CLEANING FUNCTION ---
def clean_response(text: str) -> str:
    """
    Cleans AI responses by removing:
    - Square bracket references [ ... ]
    - Weird unicode markers like  ... 
    - Tokens like :source:, :ref:, etc.
    - Standalone numbers
    - Extra spaces and punctuation issues
    """

    if not text:
        return ""

    # Remove [ ... ] references
    text = re.sub(r"\[[^\]]*\]", "", text)

    # Remove weird markers like ...
    text = re.sub(r".*?", "", text)

    # Remove special tokens like :source:, :ref:, :footnote:
    text = re.sub(r":\w+:", "", text, flags=re.IGNORECASE)

    # Remove standalone numbers
    text = re.sub(r"\b\d+\b", "", text)

    # Fix spacing before punctuation
    text = re.sub(r"\s+([.,!?])", r"\1", text)

    # Collapse multiple spaces
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()

# --- WEBHOOK ---
@app.route("/webhook", methods=["POST"])
def handle_webhook():
    try:
        data = request.get_json()
        user_message = data.get("message")

        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        # Step 1: Create a new Thread
        thread = client.beta.threads.create()

        # Step 2: Add the user message
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )

        # Step 3: Run the Assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )

        # Step 4: Wait until it's finished
        while run.status in ["queued", "in_progress"]:
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            time.sleep(0.5)

        # Step 5: Get messages
        messages = client.beta.threads.messages.list(thread_id=thread.id)

        # Step 6: Extract latest assistant reply safely
        ai_reply = None
        for msg in messages.data:
            if msg.role == "assistant":
                # Find the first text block
                for block in msg.content:
                    if block.type == "text":
                        ai_reply = block.text.value
                        break
            if ai_reply:
                break

        if not ai_reply:
            return jsonify({"reply": "Sorry, I couldn’t generate a response this time."})

        # --- Debug logs ---
        print("\nRAW AI REPLY >>>", ai_reply)
        cleaned = clean_response(ai_reply)
        print("CLEANED REPLY >>>", cleaned, "\n")

        return jsonify({"reply": cleaned})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# --- Run locally ---
if __name__ == "__main__":
    app.run(port=5001, debug=True)
