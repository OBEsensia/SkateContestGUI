# Skate Contest - Live Scoring System

A real-time, local-network web application designed to manage skateboarding competitions. It features a complete workflow including competitor registration, live multi-judge scoring via tablets, and an interactive public scoreboard.

## 🌟 Key Features

### 1. Registration & Management (Phase 1)
* **Smart Excel Import**: Instantly load skater lists via `.xlsx` files. The algorithm automatically resolves first name/last name column conflicts and parses categories.
* **Manual Wildcard Entry**: Add last-minute skaters on the fly directly from the control interface.

### 2. Tournament Sandbox & Phase Engine (Phase 2)
* **Tournament Sandbox**: A visual workspace allowing the organizer to filter by category and Phase (Qualifications, Semi-Final, Final).
* **Heat/Pool Creation**: Generate pools manually or auto-distribute. Easily assign or reassign unseeded skaters using dropdowns.
* **Auto-Qualification Engine (Top N)**: 
    * Automatically extracts the Top X skaters based on their Best Run score in a given phase.
    * **Reverse Start Order**: Skaters who qualify 1st will automatically skate last in the next phase (official skate contest rule).
    * **Mathematical Distribution**: Evenly distributes qualified skaters across the new phase's heats, handling remainders mathematically.

### 3. Live Control & Operational Robustness (Phase 3)
* **1-Click "Call to Screen"**: Click "Call" next to a skater in their live heat to instantly push them to the public scoreboard and notify the judges' tablets.
* **Safety "Re-Call" Feature**: If a mistake is made, clicking "🔄 Re-Call" resets the current run. The system retrieves the judges' previous score history for that run so they don't have to start from scratch.
* **DNS (Did Not Start) Handling**: Disqualify a skater with 1 click. Assigns a `-1.0` score in the database, locking them at the bottom of the leaderboard and excluding them from future phases.
* **Anti-Deadlock Security**: If a voting session gets stuck, the **⏹️ EXIT LIVE** button sends an asynchronous cancellation signal, clears the server's WebSocket cache, and instantly unlocks the organizer and judge interfaces.

### 4. Reporting & Archiving (Phase 4)
* **Multi-Tab Excel Export**: Generate an official `.xlsx` results file with one click (one tab per category and phase).
* **Full Traceability**: The export lists the actual rank, individual Run scores (1, 2, and 3), highlights **DNS** skaters in red, and explicitly states if a skater qualified for the next phase (including their next Heat and Start Order).

---

## 📐 Core Algorithm Logic

### Leaderboard Sorting & Start Order
To prevent empty or messy leaderboards at the start of a phase, the backend uses a multi-level SQL sorting rule:
1.  **Best Score** (Descending)
2.  **Heat / Pool Name** (Ascending - if scores are tied at 0.0)
3.  **Start Order** (Ascending)
*Result: At the start of a phase, the public screen displays the leaderboard in the exact chronological order skaters will drop in.*

### DNS (Did Not Start) Logic
Skaters marked as **DNS** receive a `-1.0` score. In the system, non-participants remain at `0.0` (provisional). Because the scoring scale is `0.0` to `100.0`, DNS skaters logically sink to the absolute bottom of the database ranking and are flagged with a red badge.

---

## 📸 Interface Tour & Screenshots

### 1. Control Room (Organizer Dashboard)
**Phase 1: Event Setup & Enrollment**
The setup phase allows the organizer to create events, configure the number of judges, and enroll skaters manually or via Excel.
* ![Control Room Phase 1](doc/ControlRoom_Phase1.png)
* ![Control Room Phase 1a](doc/ControlRoom_Phase1_a.png)
* ![Control Room Phase 1b](doc/ControlRoom_Phase1_b.png)
* ![Skater Enrollment](doc/ControlRoom_Phase1_Skaters_enroll.png)

**Phase 2: Live Competition Control**
The live dashboard controls the flow of the contest, pushing states to the judges and the public screen.
* ![Live Start](doc/ControlRoom_Phase2_live_start.png)
* ![Run in Progress](doc/ControlRoom_Phase2_run_in_progress.png)
* ![Voting Started](doc/ControlRoom_Phase2_voting_start.png)
* ![Manual Entry Backup](doc/ControlRoom_Phase2_voting_manual_entry.png)
* ![Voting Ended](doc/ControlRoom_Phase2_voting_end.png)

### 2. Judge Pad (Tablets)
A distraction-free, dark-themed interface for the judges to evaluate skaters efficiently.
* ![Select Chair](doc/Judge_pad_select_chair.png)
* ![Connected](doc/Judge_pad_connected.png)
* ![Run in Progress](doc/Judge_pad_run_in_progress.png)
* ![Voting Interface](doc/Judge_pad_voting.png)
* ![Vote Submission](doc/On_judge1_vote_submission.png)

### 3. Public Score Board
A responsive, high-contrast display designed for projectors and LED walls.
* ![Waiting for Event](doc/leaderboard_waiting.png)
* ![Run in Progress](doc/leaderboard_run_in_progress.png)
* ![Voting Progress](doc/leaderboard_voting_2-3.png)
* ![Voting End & Leaderboard Update](doc/leaderboard_voting_end_and_leaderboard.png)
* ![Podium](doc/leaderboard_podium.png)

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

## ⚙️ Usage Guide (Running a Contest)
### Step 1: Preparation & Import
1. Launch the server using start_skate_contest.bat.
2. Open the Control Room (http://localhost:8000).
3. Create the event and import the skater registration Excel file.

### Step 2: The Sandbox (Heats Creation)
1. Select your category and the Qualifications phase.
2. Create your Heats (e.g., "Heat 1", "Heat 2").
3. Assign your skaters from the orange Unassigned Skaters pool into their respective heats.

### Step 3: Going Live
1. Click GO LIVE.
2. Click Call next to the first skater on the list.
3. Once their run is over, click 1. Open Voting. Judges score on their tablets. Once the last judge submits, the final average is calculated and saved.
4. Repeat for all skaters in the phase.

### Step 4: Closing the Phase & Qualifying
1. Click ⏹️ EXIT LIVE.
2. Click 📥 Export Results to download and archive the official Qualifications Excel file.
3. In the green Auto-Generate Next Phase box, set it to Semi-Final, define the Top N to qualify (e.g., 16), and the number of target pools (e.g., 4).
4. Click ⚡ Generate. The system calculates the cut, reverses the start order, and builds the semi-final heats.
5. Click GO LIVE again, switch the view to Semi-Final, and call your first skater!

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
- **"Call" buttons stuck on gray (Inactive)?**
This means a previous run was left open or interrupted. Simply click ⏹️ EXIT LIVE. The system will trigger the cancel_voting procedure, flush the server's memory, and unlock all buttons.

- **Visual changes not applying?**
If you edit the Vue interface, run npm run build in the frontend folder to update the static files, then hard-refresh your browser (Ctrl + F5).

- **Backend code modifications not applying?**
Any change to Python files (main.py or competition_manager.py) requires a hard restart of the command prompt server (close the black window and rerun the .bat file).
