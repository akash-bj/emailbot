import os
from flask import Flask, request, jsonify
# Ensure analyze.py is updated to the "Lightweight API" version first!
from analyze import analyze_text 
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

@app.route("/")
def index():
    return "SmartMail Insight Bot (Cliq Edition) is Running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Entry point for Zoho Cliq Slash Command.
    Usage in Cliq: /smartmail [paste_email_text_here]
    """
    
    # 1. EXTRACT TEXT
    # Zoho Cliq sends Slash Command data as Form Data in the 'arguments' field.
    user_text = request.form.get("arguments")

    # Fallback: Check JSON (Useful for testing via Postman)
    if not user_text and request.is_json:
        data = request.get_json()
        user_text = data.get("text") or data.get("message")

    # Validation
    if not user_text:
        return jsonify({
            "text": "⚠️ Error: No text provided. usage: /smartmail [paste email text]"
        })

    # 2. RUN ANALYSIS
    # This calls your lightweight analyze.py
    try:
        result = analyze_text(user_text)
    except Exception as e:
        return jsonify({"text": f"❌ Analysis Failed: {str(e)}"})

    # 3. FORMAT FOR ZOHO CLIQ (JSON CARD)
    # This specific JSON structure creates the visual card in Cliq
    response = {
        "text": "🤖 *SmartMail Insight Report*",
        "card": {
            "title": "Email Intelligence",
            "theme": "modern-inline",
            "thumbnail": "https://cdn-icons-png.flaticon.com/512/4712/4712035.png"
        },
        "slides": [
            {
                "type": "label",
                "title": "Key Metrics",
                "data": [
                    {"label": "Tone", "value": result.get("tone", "Neutral")},
                    {"label": "Urgency", "value": result.get("urgency", "Low")}
                ]
            },
            {
                "type": "text",
                "title": "📝 Summary",
                "data": result.get("summary", "No summary generated.")
            },
            {
                "type": "text",
                "title": "💡 Suggested Reply",
                "data": result.get("suggested_reply", "No reply generated.")
            }
        ],
        "buttons": [
            {
                "label": "Create Ticket",
                "action": {
                    "type": "open_url",
                    # Link to Zoho Desk ticket creation (or a dummy link for demo)
                    "url": "https://desk.zoho.com/support/home" 
                }
            }
        ]
    }

    return jsonify(response)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)