from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import time
from datetime import datetime
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8289

HISTORY_FILE = Path(__file__).with_name("cycle_history.json")


def load_history():
    """Load previously saved cycle records."""
    if not HISTORY_FILE.exists():
        return []

    try:
        with HISTORY_FILE.open("r", encoding="utf-8") as file:
            history = json.load(file)

        return history if isinstance(history, list) else []

    except (json.JSONDecodeError, OSError):
        return []
def save_history(history):
    """Save cycle records to disk."""
    with HISTORY_FILE.open("w", encoding="utf-8") as file:
        json.dump(history, file, indent=4)

state = {
    "status": "Idle",
    "mode": None,
    "start_time": None,
    "duration": 0,
    "temperature": "Cold",
    "cycle_type": "Normal",
    "cycle_recorded": False,
}

def record_cycle(mode, duration, temperature, cycle_type, status, started_at):
    """Append one cycle record to the history file."""
    history = load_history()
    ended_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history.append({
        "mode": mode,
        "duration": int(duration),
        "temperature": temperature,
        "cycle_type": cycle_type,
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at,
    })
    save_history(history)

def get_current_state():
    """Calculate and return the current machine status."""
    if state["status"] == "Running" and state["start_time"] is not None:
        elapsed = time.monotonic() - state["start_time"]
        duration = max(1, int(state["duration"]))
        remaining = max(0, int(duration - elapsed))
        progress = min(100, int(elapsed / duration * 100))

        if elapsed >= duration:
            if not state["cycle_recorded"]:
                record_cycle(
                    state["mode"],
                    state["duration"],
                    state["temperature"],
                    state["cycle_type"],
                    "Completed",
                    state["started_at"],
                )
                state["cycle_recorded"] = True
            state["status"] = "Completed"
            state["start_time"] = None
            remaining = 0
            progress = 100
    else:
        remaining = 0
        progress = 100 if state["status"] == "Completed" else 0

    return {
        "status": state["status"],
        "mode": state["mode"],
        "remaining": remaining,
        "progress": progress,
        "temperature": state["temperature"],
        "cycle_type": state["cycle_type"],
    }

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartWash</title>
<style>
    * { box-sizing: border-box; }
    body {
        font-family: Arial, sans-serif;
        max-width: 850px;
        margin: 30px auto;
        padding: 16px;
        background: #f2f6fa;
        color: #1d2939;
    }
    .panel {
        background: white;
        padding: 22px;
        border-radius: 12px;
        box-shadow: 0 2px 10px #ccc;
    }
    label { display: block; margin-top: 15px; font-weight: bold; }
    select, button {
        padding: 10px;
        margin-top: 6px;
        width: 100%;
        font-size: 16px;
    }
    button {
        cursor: pointer;
        border: none;
        border-radius: 6px;
        margin-top: 12px;
    }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    .wash { background: #1976d2; color: white; }
    .spin { background: #00897b; color: white; }
    .stop { background: #d32f2f; color: white; }
    .history-button { background: #374151; color: white; }
    #progress { width: 100%; height: 20px; margin-top: 10px; }
    #message { font-weight: bold; min-height: 1.3em; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { border: 1px solid #d0d5dd; padding: 9px; text-align: left; }
    th { background: #eef2f6; }
    .controls { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
    .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 12px; }
    .stat { background: #f2f6fa; padding: 12px; border-radius: 8px; }
    @media (max-width: 520px) {
        .controls, .stats { grid-template-columns: 1fr; }
    }
</style>
</head>
<body>
<div class="panel">
    <h1>SmartWash Simulator</h1>
    <h3>Washing Settings</h3>

    <label for="duration">Wash Duration</label>
    <select id="duration">
        <option value="60">1 minute (testing)</option>
        <option value="180">3 minutes (testing)</option>
        <option value="300" selected>5 minutes</option>
    </select>

    <label for="temperature">Water Temperature</label>
    <select id="temperature">
        <option value="Cold">Cold</option>
        <option value="30°C">30°C</option>
        <option value="40°C">40°C</option>
    </select>

    <label for="cycle">Cycle Type</label>
    <select id="cycle">
        <option value="Quick">Quick</option>
        <option value="Normal" selected>Normal</option>
        <option value="Heavy">Heavy</option>
    </select>

    <hr>
    <h3>Machine Controls</h3>
    <div class="controls">
        <button class="wash" onclick="sendAction('wash')">Wash</button>
        <button class="spin" onclick="sendAction('spin')">Spin</button>
        <button class="stop" onclick="sendAction('stop')">Stop</button>
    </div>

    <h3>Machine Status</h3>
    <p>Status: <span id="status">Idle</span></p>
    <p>Mode: <span id="mode">None</span></p>
    <p>Time Remaining: <span id="timer">00:00</span></p>
    <p>Temperature: <span id="shownTemp">Cold</span></p>
    <p>Cycle Type: <span id="shownCycle">Normal</span></p>
    <progress id="progress" value="0" max="100"></progress>
    <p id="progressText">0%</p>
    <p id="message" role="status">Ready</p>

    <hr>
    <h3>Cycle History</h3>
    <button class="history-button" onclick="loadHistory()">View Cycle History</button>
    <div class="stats">
        <div class="stat">Total cycles: <strong id="totalCycles">0</strong></div>
        <div class="stat">Completed: <strong id="completedCycles">0</strong></div>
        <div class="stat">Stopped: <strong id="stoppedCycles">0</strong></div>
    </div>
    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Mode</th>
                    <th>Duration</th>
                    <th>Temperature</th>
                    <th>Cycle Type</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th>Ended</th>
                </tr>
            </thead>
            <tbody id="historyBody">
                <tr><td colspan="7">Click “View Cycle History” to load saved records.</td></tr>
            </tbody>
        </table>
    </div>
</div>

<script>
async function sendAction(action) {
    const settings = {
        action,
        duration: Number(document.getElementById("duration").value),
        temperature: document.getElementById("temperature").value,
        cycle_type: document.getElementById("cycle").value
    };

    try {
        const response = await fetch("/api/action", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(settings)
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.message || "Request failed");
        document.getElementById("message").textContent = result.message || "Done";
        await refreshStatus();
        if (action === "stop") await loadHistory();
    } catch (error) {
        document.getElementById("message").textContent = "Error: " + error.message;
    }
}

async function refreshStatus() {
    try {
        const response = await fetch("/api/status", {cache: "no-store"});
        const data = await response.json();

        document.getElementById("status").textContent = data.status;
        document.getElementById("mode").textContent = data.mode || "None";
        document.getElementById("shownTemp").textContent = data.temperature;
        document.getElementById("shownCycle").textContent = data.cycle_type;
        document.getElementById("progress").value = data.progress;
        document.getElementById("progressText").textContent = data.progress + "%";

        const minutes = Math.floor(data.remaining / 60);
        const seconds = data.remaining % 60;
        document.getElementById("timer").textContent =
            String(minutes).padStart(2, "0") + ":" +
            String(seconds).padStart(2, "0");

        if (data.status === "Completed") {
            document.getElementById("message").textContent = "Cycle completed!";
            await loadHistory();
        }
    } catch (error) {
        document.getElementById("message").textContent =
            "Could not refresh status: " + error.message;
    }
}

async function loadHistory() {
    const body = document.getElementById("historyBody");
    try {
        const response = await fetch("/api/history", {cache: "no-store"});
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Could not load history");

        const history = Array.isArray(data.history) ? data.history : [];
        body.replaceChildren();

        document.getElementById("totalCycles").textContent = history.length;
        document.getElementById("completedCycles").textContent =
            history.filter(item => item.status === "Completed").length;
        document.getElementById("stoppedCycles").textContent =
            history.filter(item => item.status === "Stopped").length;

        if (history.length === 0) {
            const row = body.insertRow();
            const cell = row.insertCell();
            cell.colSpan = 7;
            cell.textContent = "No saved cycles yet. Run a Wash or Spin cycle first.";
            return;
        }

        history.slice().reverse().forEach(cycle => {
            const row = body.insertRow();
            const values = [
                cycle.mode ?? "—",
                cycle.duration != null ? cycle.duration + " sec" : "—",
                cycle.temperature ?? "—",
                cycle.cycle_type ?? "—",
                cycle.status ?? "—",
                cycle.started_at ?? cycle.timestamp ?? "—",
                cycle.ended_at ?? "—"
            ];
            values.forEach(value => {
                row.insertCell().textContent = String(value);
            });
        });
    } catch (error) {
        body.replaceChildren();
        const row = body.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 7;
        cell.textContent = "Could not load history: " + error.message;
    }
}

setInterval(refreshStatus, 1000);
refreshStatus();
</script>
</body>
</html>
"""

class SmartWashHandler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        response = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(response)

    def do_GET(self):
        if self.path == "/":
            content = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == "/api/status":
            self.send_json(get_current_state())
        elif self.path == "/api/history":
            self.send_json({"history": load_history()})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/api/action":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            self.send_json({"message": "Invalid JSON request."}, status=400)
            return

        action = data.get("action")
        if action == "stop":
            if state["status"] == "Running" and not state["cycle_recorded"]:
                record_cycle(
                    state["mode"],
                    state["duration"],
                    state["temperature"],
                    state["cycle_type"],
                    "Stopped",
                    state.get("started_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                )
            state.update({
                "status": "Idle",
                "mode": None,
                "start_time": None,
                "duration": 0,
                "cycle_recorded": False,
            })
            message = "Machine stopped."

        elif action in ("wash", "spin"):
            if state["status"] == "Running":
                self.send_json({"message": "A cycle is already running. Stop it before starting another."}, status=409)
                return

            if action == "wash":
                try:
                    duration = int(data.get("duration", 300))
                except (ValueError, TypeError):
                    self.send_json({"message": "Invalid wash duration."}, status=400)
                    return
                if duration not in (60, 180, 300):
                    self.send_json({"message": "Invalid wash duration."}, status=400)
                    return
            else:
                duration = 120

            temperature = data.get("temperature", "Cold")
            if temperature not in ("Cold", "30°C", "40°C"):
                temperature = "Cold"
            cycle_type = data.get("cycle_type", "Normal")
            if cycle_type not in ("Quick", "Normal", "Heavy"):
                cycle_type = "Normal"

            state.update({
                "status": "Running",
                "mode": action.title(),
                "start_time": time.monotonic(),
                "duration": duration,
                "temperature": temperature,
                "cycle_type": cycle_type,
                "cycle_recorded": False,
                "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            message = action.title() + " cycle started."
        else:
            self.send_json({"message": "Unknown action."}, status=400)
            return

        self.send_json({"message": message, "state": get_current_state()})

if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), SmartWashHandler)
    print(f"SmartWash running at http://{HOST}:{PORT}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSmartWash server stopped.")
    finally:
        server.server_close()
