import os
import logging
import traceback
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from analyze import analyze_text
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app) # Allow dashboard to fetch data

logging.basicConfig(level=logging.INFO)

# --- IN-MEMORY DATABASE (Resets when server restarts, perfect for Demo) ---
# Stores: {'tone': 'Angry', 'urgency': 'High', 'summary': '...', 'timestamp': ...}
GLOBAL_STATS = []

# --- DASHBOARD HTML TEMPLATE (Embed here for simplicity) ---
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>SmartMail Command Center</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: white; padding: 20px; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .card { background: #16213e; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        h2 { margin-top: 0; font-size: 18px; color: #a8a8ff; }
        .stat-big { font-size: 40px; font-weight: bold; }
        .red { color: #ff4d4d; } .green { color: #4dff88; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #333; }
        th { color: #888; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 SmartMail Insight Engine</h1>
        <div>Live Status: <span class="green">● Online</span></div>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Total Emails Analyzed</h2>
            <div class="stat-big" id="totalCount">0</div>
        </div>
        <div class="card">
            <h2>Critical Urgency</h2>
            <div class="stat-big red" id="urgentCount">0</div>
        </div>
    </div>
    <br>
    <div class="grid">
        <div class="card">
            <h2>Real-time Sentiment Analysis</h2>
            <canvas id="toneChart"></canvas>
        </div>
        <div class="card">
            <h2>Incoming Feed</h2>
            <table id="feedTable">
                <thead><tr><th>Tone</th><th>Urgency</th><th>Summary</th></tr></thead>
                <tbody id="feedBody"></tbody>
            </table>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('toneChart').getContext('2d');
        const toneChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Angry', 'Neutral', 'Positive'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: ['#ff4d4d', '#888888', '#4dff88'],
                    borderWidth: 0
                }]
            },
            options: { cutout: '70%' }
        });

        async function fetchData() {
            try {
                let res = await fetch('/api/stats');
                let data = await res.json();
                
                // Update Numbers
                document.getElementById('totalCount').innerText = data.total;
                document.getElementById('urgentCount').innerText = data.high_urgency;

                // Update Chart
                toneChart.data.datasets[0].data = [data.angry, data.neutral, data.positive];
                toneChart.update();

                // Update Table
                let rows = "";
                data.recent.forEach(item => {
                    let color = item.tone.includes("Angry") ? "red" : "white";
                    rows += `<tr>
                        <td style="color:${color}">${item.tone}</td>
                        <td>${item.urgency}</td>
                        <td>${item.summary.substring(0, 40)}...</td>
                    </tr>`;
                });
                document.getElementById('feedBody').innerHTML = rows;

            } catch(e) { console.log(e); }
        }

        // Poll every 2 seconds for "Live" effect
        setInterval(fetchData, 2000);
        fetchData();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return "SmartMail Bot is Running."

# --- NEW ROUTE: MANAGER DASHBOARD ---
@app.route("/dashboard")
def dashboard():
    return render_template_string(DASHBOARD_HTML)

# --- NEW ROUTE: API FOR DASHBOARD ---
@app.route("/api/stats")
def stats():
    # Calculate stats from memory
    total = len(GLOBAL_STATS)
    urgent = sum(1 for x in GLOBAL_STATS if x['urgency'] == 'High')
    angry = sum(1 for x in GLOBAL_STATS if "Angry" in x['tone'] or "Negative" in x['tone'])
    positive = sum(1 for x in GLOBAL_STATS if "Positive" in x['tone'])
    neutral = total - angry - positive

    return jsonify({
        "total": total,
        "high_urgency": urgent,
        "angry": angry,
        "positive": positive,
        "neutral": neutral,
        "recent": GLOBAL_STATS[-5:][::-1] # Last 5 items
    })

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        app.logger.info(f"Incoming Payload: {data}")

        # --- EXTRACT TEXT ---
        user_text = ""
        if "message" in data and isinstance(data["message"], dict):
             user_text = data["message"].get("text") or data["message"].get("content")
        if not user_text and "visitor" in data:
            if "message" in data["visitor"]: user_text = data["visitor"]["message"]
        if not user_text and "data" in data and isinstance(data["data"], dict):
            user_text = data["data"].get("text") or data["data"].get("message")

        if not user_text:
             return jsonify({"replies": [{"text": "System Error: No text found."}]})

        # --- ANALYZE ---
        result = analyze_text(user_text)

        # --- SAVE TO GLOBAL STATS (The Magic) ---
        GLOBAL_STATS.append({
            "tone": result['tone'],
            "urgency": result['urgency'],
            "summary": result['summary']
        })

        # --- FORMAT RESPONSE ---
        bot_message = (
            f"🔍 **Analysis Report**\n"
            f"------------------------------\n"
            f"• **Tone:** {result.get('tone', 'Neutral')}\n"
            f"• **Urgency:** {result.get('urgency', 'Low')}\n\n"
            f"📝 **Summary:**\n{result.get('summary', 'No summary')}\n\n"
            f"💡 **Suggested Reply:**\n{result.get('suggested_reply', 'No reply')}"
        )

        response = {
            "replies": [{"text": bot_message}],
            "suggestions": ["Create Ticket", "Draft Reply", "Escalate"]
        }
        return jsonify(response)

    except Exception as e:
        error_trace = traceback.format_exc()
        app.logger.error(f"CRASH: {error_trace}")
        return jsonify({"replies": [{"text": "⚠️ Processing Error."}]})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
