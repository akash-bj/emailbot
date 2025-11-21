import os
import logging
from flask import Flask, request, jsonify
from analyze import analyze_text
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# Set up logging to see errors in Render Dashboard
logging.basicConfig(level=logging.INFO)

@app.route("/")
def index():
    return "SmartMail Insight Bot (SalesIQ Edition) is Healthy!"

@app.route("/webhook", methods=["POST"])
def webhook():
    user_text = ""
    try:
        data = request.get_json(force=True)
        # Log the raw data to Render Console (for debugging)
        app.logger.info(f"Incoming Data: {data}")

        # --- UNIVERSAL MESSAGE EXTRACTOR ---
        # Strategy 1: Direct 'text' or 'message'
        if "text" in data:
            user_text = data["text"]
        elif "message" in data:
            user_text = data["message"]
        
        # Strategy 2: Nested in 'visitor'
        elif "visitor" in data:
            if "message" in data["visitor"]:
                user_text = data["visitor"]["message"]
            elif "text" in data["visitor"]:
                user_text = data["visitor"]["text"]

        # Strategy 3: Nested in 'data' (Common in some Zobot versions)
        elif "data" in data:
            if "text" in data["data"]:
                user_text = data["data"]["text"]
            elif "message" in data["data"]:
                user_text = data["data"]["message"]

    except Exception as e:
        app.logger.error(f"Parsing Error: {e}")
        pass

    # FALLBACK: If we still can't find text, ask user to retry
    if not user_text:
        return jsonify({
            "replies": [{
                "text": "System Error: I received the signal, but couldn't find the text. Please check Render Logs."
            }]
        })

    # --- RUN AI ANALYSIS ---
    result = analyze_text(user_text)

    bot_message = (
        f"🔍 **Analysis Report**\n"
        f"------------------------------\n"
        f"• **Tone:** {result['tone']}\n"
        f"• **Urgency:** {result['urgency']}\n\n"
        f"📝 **Summary:**\n{result['summary']}\n\n"
        f"💡 **Suggested Reply:**\n{result['suggested_reply']}"
    )

    response = {
        "replies": [{"text": bot_message}],
        "suggestions": ["Create Ticket", "Draft Reply", "Escalate"]
    }
    
    return jsonify(response)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
