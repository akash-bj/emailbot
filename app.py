import os
import logging
import traceback
from flask import Flask, request, jsonify
from analyze import analyze_text
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

@app.route("/")
def index():
    return "SmartMail Bot (Production Fix) is Running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # 1. Parse Data
        data = request.get_json(force=True)
        app.logger.info(f"Incoming Payload: {data}")

        # 2. SMART TEXT EXTRACTION (The Fix)
        user_text = ""
        
        # Check for 'message' object at root (Common in Zobot)
        if "message" in data:
            msg_obj = data["message"]
            if isinstance(msg_obj, str):
                user_text = msg_obj
            elif isinstance(msg_obj, dict):
                # If message is an object, grab 'text' or 'content' inside it
                user_text = msg_obj.get("text") or msg_obj.get("content")

        # Check for 'visitor' -> 'message' (Legacy Zobot)
        if not user_text and "visitor" in data:
            vis_obj = data["visitor"]
            if "message" in vis_obj:
                user_text = vis_obj["message"]

        # Check for 'data' -> 'text' (Cliq/Other webhooks)
        if not user_text and "data" in data:
             if isinstance(data["data"], dict):
                user_text = data["data"].get("text") or data["data"].get("message")

        # Final Check: If user_text is still empty or not a string
        if not user_text or not isinstance(user_text, str):
            return jsonify({"replies": [{"text": "I received a signal, but couldn't read the text format."}]})

        # 3. Run Analysis
        result = analyze_text(user_text)

        # 4. Format Response
        bot_message = (
            f"🔍 **Analysis Report**\n"
            f"------------------------------\n"
            f"• **Tone:** {result.get('tone', 'Neutral')}\n"
            f"• **Urgency:** {result.get('urgency', 'Low')}\n\n"
            f"📝 **Summary:**\n{result.get('summary', 'No summary available')}\n\n"
            f"💡 **Suggested Reply:**\n{result.get('suggested_reply', 'No reply generated')}"
        )

        response = {
            "replies": [{"text": bot_message}],
            "suggestions": ["Create Ticket", "Draft Reply", "Escalate"]
        }
        return jsonify(response)

    except Exception as e:
        error_trace = traceback.format_exc()
        app.logger.error(f"CRASH: {error_trace}")
        return jsonify({"replies": [{"text": "⚠️ Bot had a hiccup processing that message. Please try again."}]})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
