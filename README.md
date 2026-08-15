# Skate Contest - Live Scoring System

A real-time, local-network web application designed to manage skateboarding competitions. It features a complete workflow including competitor registration, live multi-judge scoring via tablets, and an interactive public scoreboard.

## 🌟 Key Features

* **Real-Time Synchronization**: Powered by FastAPI WebSockets for instant score submissions and leaderboard updates.
* **Resilient Architecture (Anti-F5)**: The system survives accidental page refreshes and temporary network drops using local storage and server-side state caching.
* **Three Dedicated Interfaces**:
  1. **Control Room (Organizer)**: The main dashboard to manage the event, add skaters, and control the flow of the competition.
  2. **Judge Pad (Tablets)**: A streamlined, touch-friendly interface for judges to submit scores.
  3. **Score Board (Public Screen)**: A responsive, high-contrast display for the public showing current skater status, live voting progress, and a dynamic Top 10 leaderboard.
* **Flexible Configuration**: Choose between 3 or 5 judges per event.
* **Excel Import**: Quickly load competitor lists using `.xlsx` files.
* **Podium Mode**: A dedicated fullscreen view to celebrate the Top 3 winners at the end of the contest.

---

## 🏗️ Tech Stack

* **Backend**: Python 3, FastAPI, SQLite, Uvicorn, WebSockets.
* **Frontend**: Vue.js 3 (Composition API), Vite, HTML5, CSS3.
* **Deployment**: The Vue.js application is compiled into static files and served directly by the FastAPI backend on a single port.

---

## 🚀 Installation & Setup

### Prerequisites
* **Node.js** & **npm** (for the frontend build)
* **Python 3.9+** (for the backend server)

### Step 1: Build the Frontend
Navigate to the frontend directory, install dependencies, and build the static files.
```bash
cd frontend
npm install
npm run build
```
Note: This will automatically generate the index.html and assets in the backend/static/ directory.

### Step 2: Setup the Backend
Navigate to the backend directory and install the required Python packages.

```bash
cd backend
pip install fastapi uvicorn pydantic openpyxl python-multipart websockets
```

## 🏁 Running the Application
To start the system, you can use the provided batch script if you are on Windows:
```dos
start_skate_contest.bat
```

(Alternatively, run uvicorn main:app --host 0.0.0.0 --port 8000 from the backend directory).

Once the server is running, access the interfaces via any web browser on the same network:
- Control Room (Regie): http://localhost:8000/
- Public Score Board: http://localhost:8000/#/board
- Judge Tablets: http://localhost:8000/#/judge

## 📖 Usage Guide (Day of the Event)
### Event Setup
1. Open the Control Room.
2. Create a new competition or load an existing one.
3. Import your .xlsx competitor list or use the "Manual Entry" to add wildcards.

4. Select the number of judges (3 or 5) and click GO LIVE.

### Live Competition Workflow
1. Call Skater: Enter the Bib Number and Run Number, then click 1. Call Skater (On Course).
    - The public screen will show "RUN IN PROGRESS". Judge tablets remain locked.

2. Open Voting: Once the run is finished, click 2. Open Voting.
    - Judge tablets unlock. The public screen shows the voting progress bar.

3. Scoring: Judges submit their scores (0.0 to 10.0) from their tablets.
    - If a tablet fails, the organizer can use the "Direct Judge Input" panel to submit a score manually.

4. Result: Once all scores are received, the system calculates the average, displays the final score, and updates the Top 10 Leaderboard automatically.

### End of Contest
Click the 🏆 SHOW PODIUM (END CONTEST) button in the Control Room to switch the public Score Board to a celebratory fullscreen display of the Top 3 skaters.

## 🛠️ Project Structure
```Plaintext
skate-contest/
├── backend/
│   ├── main.py                  # FastAPI server and WebSocket logic
│   ├── db_manager.py            # SQLite database initialization
│   ├── competition_manager.py   # CRUD operations and Excel import logic
│   ├── skate_contest.db         # Auto-generated SQLite database
│   └── static/                  # Auto-generated frontend build files
├── frontend/
│   ├── index.html               # Vite entry point
│   ├── package.json             # Node dependencies
│   ├── vite.config.js           # Vite configuration (routes to backend/static)
│   └── src/
│       ├── main.js              # Vue app initialization and Router
│       └── views/
│           ├── ControlRoom.vue  # Organizer Dashboard
│           ├── JudgePad.vue     # Judge Interface
│           └── ScoreBoard.vue   # Public Display
└── start_skate_contest.bat      # Windows startup script
```

## ⚠️ Troubleshooting
- **Blank screen on localhost:8000?**
Ensure you have run npm run build in the frontend directory. The backend needs the generated static files to serve the application.

- **WebSocket disconnected / Actions not triggering?**
Check the terminal running the Python server for errors. Ensure all devices (tablets, public screen PC) are connected to the exact same Wi-Fi network as the server host.

- **"Cannot use import statement outside a module" error?**
This means the backend served raw Vue/JS code instead of the built files. Ensure frontend/index.html is a standard Vite skeleton and run npm run build again.
- 