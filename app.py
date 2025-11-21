import os
from flask import Flask, request, jsonify
# This imports your secure analyze.py (do not change that file)
from analyze import analyze_text
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

@app.route("/")
def index():
    return "SmartMail Insight Bot (SalesIQ Edition) is Healthy!"

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    This function handles messages from Zoho SalesIQ.
    """
    # 1. READ DATA FROM SALESIQ
    user_text = ""
    try:
        data = request.get_json(force=True)
        # SalesIQ sends message inside ['visitor']['message'] usually
        if "visitor" in data and "message" in data["visitor"]:
            user_text = data["visitor"]["message"]
        elif "text" in data:
            user_text = data["text"]
    except:
        pass

    # If no text found, return nothing
    if not user_text:
        return jsonify({"replies": [{"text": "I couldn't read that message."}]})

    # 2. GET AI ANALYSIS (Using your analyze.py)
    result = analyze_text(user_text)

    # 3. FORMAT FOR SALESIQ (Chat Bubbles)
    # We create a nicely formatted message
    bot_message = (
        f"🔍 **SmartMail Analysis**\n"
        f"------------------------------\n"
        f"• **Tone:** {result['tone']}\n"
        f"• **Urgency:** {result['urgency']}\n\n"
        f"📝 **Summary:**\n{result['summary']}\n\n"
        f"💡 **Suggested Reply:**\n{result['suggested_reply']}"
    )

    # The JSON structure SalesIQ expects:
    response = {
        "replies": [
            {
                "text": bot_message
            }
        ],
        # These buttons appear as clickable chips
        "suggestions": ["Create Ticket", "Draft Reply", "Escalate"]
    }
    
    return jsonify(response)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
