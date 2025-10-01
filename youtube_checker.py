import time
import requests
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build

# --- SETUP ---
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
CHATBOT_WEBHOOK_URL = "http://127.0.0.1:5001/webhook"
VIDEO_ID = "fHbuZwXIp04"  # replace with your video ID

# Keep track of last replied comment to avoid duplicates
last_comment_id = None  

def get_latest_comment_and_reply():
    global last_comment_id
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

        request = youtube.commentThreads().list(
            part="snippet",
            videoId=VIDEO_ID,
            maxResults=1,
            order="time"
        )
        response = request.execute()

        if not response.get("items"):
            print("No comments found on this video.")
            return

        latest_comment = response["items"][0]
        comment_id = latest_comment["id"]
        comment_text = latest_comment["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
        comment_author = latest_comment["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"]

        # Skip if we've already replied to this comment
        if comment_id == last_comment_id:
            return  

        print("-" * 40)
        print(f"💬 Latest comment by '{comment_author}': {comment_text}")

        # Ask AI for a reply
        chatbot_response = requests.post(CHATBOT_WEBHOOK_URL, json={"message": comment_text}, timeout=60)

        if chatbot_response.status_code == 200:
            ai_reply = chatbot_response.json().get("reply", "Could not get a response.")
            print(f"✅ AI Reply: {ai_reply}")

            # --- Post reply back to YouTube ---
            youtube.comments().insert(
                part="snippet",
                body={
                    "snippet": {
                        "parentId": comment_id,
                        "textOriginal": ai_reply
                    }
                }
            ).execute()

            print("📌 Reply posted to YouTube.")

            # Remember last comment replied
            last_comment_id = comment_id
        else:
            print(f"❌ Error from chatbot, status {chatbot_response.status_code}")

    except Exception as e:
        print(f"⚠️ Error: {e}")

if __name__ == "__main__":
    print("🚀 Watching YouTube comments (Ctrl+C to stop)...")
    while True:
        get_latest_comment_and_reply()
        time.sleep(30)  # check every 30 seconds
