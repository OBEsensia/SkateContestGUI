<template>
  <div class="judge-app">
    <!-- HEADER -->
    <header class="judge-header">
      <div class="header-left">
        <span class="status-dot" :class="{ 'connected': isConnected }"></span>
        <h1>{{ competitionName.toUpperCase() }}</h1>
      </div>
      <div class="header-right" v-if="selectedJudge">
         <span class="judge-badge">
             JUDGE {{ selectedJudge }} <span v-if="judgeNames[selectedJudge]"> - {{ judgeNames[selectedJudge] }}</span>
         </span>
         <button class="btn outline small" @click="logout">Change</button>
      </div>
    </header>

    <!-- ÉCRAN DE SÉLECTION DU JUGE -->
    <div v-if="!selectedJudge" class="selection-screen">
      <div class="card">
        <h2>Select your Judge Chair</h2>
        <p class="subtitle">Please assign this tablet to a specific judge.</p>

        <div class="judge-grid">
          <button v-for="i in totalJudges" :key="i" class="btn primary huge" @click="selectJudge(i)" style="display: flex; flex-direction: column; align-items: center; gap: 5px;">
            <span>JUDGE {{ i }}</span>
            <span v-if="judgeNames[i]" style="font-size: 1rem; font-weight: normal; color: #bbdefb;">
                {{ judgeNames[i] }}
            </span>
          </button>
        </div>
      </div>
    </div>

    <!-- ÉCRAN DE VOTE ET CLASSEMENT -->
    <div v-else class="voting-layout">

      <!-- ZONE DE VOTE (Haut) -->
      <div class="voting-screen">
        <div v-if="!currentSkaterName" class="waiting-state card">
          <h2>Waiting for the next skater...</h2>
          <div class="spinner"></div>
        </div>

        <div v-else class="active-state card">
           <div class="skater-info">
             <h2 class="skater-name">{{ currentSkaterName }}</h2>
             <h3 class="run-info">RUN {{ currentRunNumber }} <span v-if="maxRuns" class="max-run">/ {{ maxRuns }}</span></h3>
           </div>

           <!-- ETAT 1 : Run en cours -->
           <div v-if="!isVotingOpen && !hasVoted" class="waiting-vote">
              <div class="pulse-icon">👀</div>
              <p class="main-instruction">Run in progress... Watch carefully!</p>
              <p class="sub-instruction">Wait for the head judge to open voting.</p>
           </div>

           <!-- ETAT 2 : Vote Ouvert -->
           <div v-if="isVotingOpen && !hasVoted" class="voting-pad">
              <div class="score-display" :class="{ 'high-score': score >= 80, 'low-score': score < 40 }">
                  {{ score.toFixed(1) }}
              </div>

              <input type="range" v-model.number="score" min="0" max="100" step="0.1" class="score-slider" />

              <div class="score-inputs">
                <button class="btn adjust danger" @click="adjustScore(-1)">- 1.0</button>
                <button class="btn adjust warning" @click="adjustScore(-0.1)">- 0.1</button>

                <!-- Saisie manuelle avec écoute de la touche Entrée -->
                <input type="number" v-model.number="score" min="0" max="100" step="0.1" class="manual-input" @keydown.enter="submitScore" />

                <button class="btn adjust primary" @click="adjustScore(0.1)">+ 0.1</button>
                <button class="btn adjust success" @click="adjustScore(1)">+ 1.0</button>
              </div>

              <button class="btn success giant submit-btn" @click="submitScore">SUBMIT SCORE</button>
           </div>

           <!-- ETAT 3 : A voté -->
           <div v-if="hasVoted" class="voted-state">
              <div class="check-icon">✅</div>
              <h2>Score Submitted!</h2>
              <div class="submitted-score">{{ score.toFixed(1) }}</div>
              <p class="sub-instruction">Waiting for other judges to finish...</p>
           </div>
        </div>
      </div>

      <!-- ZONE CLASSEMENT (Bas) -->
      <div class="judge-leaderboard card" v-if="leaderboard.length > 0">
        <h3>Current Ranking</h3>
        <table class="mini-table">
          <thead>
            <tr>
              <th>Rk</th>
              <th>Skater</th>
              <th class="right-align">Score</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(skater, index) in leaderboard" :key="skater.id" :class="{'dns-row': skater.score < 0}">
              <td>{{ skater.score < 0 ? '-' : index + 1 }}</td>
              <td>
                {{ skater.name }}
                <span class="skater-cat">{{ skater.category }}</span>
              </td>
              <td class="score-cell right-align">
                {{ skater.score < 0 ? 'DNS' : skater.score.toFixed(2) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';

const isConnected = ref(false);
const competitionName = ref('SKATE CONTEST');
const totalJudges = ref(3);
const maxRuns = ref(3);

const selectedJudge = ref(parseInt(localStorage.getItem('judge_id')) || null);
const currentSkaterName = ref('');
const currentRunNumber = ref(null);
const judgeNames = ref({});
const leaderboard = ref([]);

const isVotingOpen = ref(false);
const hasVoted = ref(false);
const score = ref(50.0);

let socket = null;

const connectWebSocket = () => {
  const serverIp = window.location.hostname || "127.0.0.1";
  socket = new WebSocket(`ws://${serverIp}:8000/ws`);

  socket.onopen = () => {
    isConnected.value = true;
  };

  socket.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);

      if (payload.type === 'board_meta') {
        competitionName.value = payload.competition_name || 'SKATE CONTEST';
        if (payload.judge_count) {
            totalJudges.value = payload.judge_count;
            if (selectedJudge.value !== null && selectedJudge.value > totalJudges.value) {
                logout();
                alert(`The competition has been reconfigured for ${totalJudges.value} judges. You have been disconnected.`);
            }
        }
        if (payload.max_runs) maxRuns.value = payload.max_runs;
        if (payload.judge_names) judgeNames.value = payload.judge_names;
      }
      else if (payload.type === 'new_run') {
        currentSkaterName.value = payload.skater_name;
        currentRunNumber.value = payload.run_number;
        isVotingOpen.value = false;
        hasVoted.value = false;

        if (payload.previous_scores && payload.previous_scores[selectedJudge.value] !== undefined) {
            score.value = payload.previous_scores[selectedJudge.value];
            hasVoted.value = true;
        } else {
            score.value = 50.0;
        }
      }
      else if (payload.type === 'voting_opened') {
        isVotingOpen.value = true;
      }
      else if (payload.type === 'run_completed') {
        isVotingOpen.value = false;
        if (payload.is_cancelled) {
            currentSkaterName.value = '';
            hasVoted.value = false;
        }
      }
      else if (payload.type === 'leaderboard_updated') {
        leaderboard.value = payload.leaderboard;
      }
      else if (payload.type === 'board_reset') {
        competitionName.value = 'SKATE CONTEST';
        currentSkaterName.value = '';
        isVotingOpen.value = false;
        hasVoted.value = false;
        score.value = 50.0;
        leaderboard.value = [];
      }
    } catch (error) {
      console.error(error);
    }
  };

  socket.onclose = () => {
    isConnected.value = false;
    setTimeout(connectWebSocket, 3000);
  };
};

const selectJudge = (judgeNumber) => {
  selectedJudge.value = judgeNumber;
  localStorage.setItem('judge_id', judgeNumber);
};

const logout = () => {
  selectedJudge.value = null;
  localStorage.removeItem('judge_id');
};

const adjustScore = (amount) => {
  let newScore = score.value + amount;
  if (newScore > 100) newScore = 100;
  if (newScore < 0) newScore = 0;
  score.value = parseFloat(newScore.toFixed(1));
};

watch(score, (newVal) => {
  if (newVal > 100) score.value = 100;
  if (newVal < 0) score.value = 0;
});

const submitScore = () => {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    alert("Connection lost. Please wait to reconnect.");
    return;
  }

  hasVoted.value = true;

  socket.send(JSON.stringify({
    action: 'submit_score',
    judge_id: selectedJudge.value,
    score: parseFloat(score.value)
  }));
};

// --- ÉCOUTEUR GLOBAL POUR LA TOUCHE ENTRÉE ---
const handleKeydown = (event) => {
  if (event.key === 'Enter' && selectedJudge.value && isVotingOpen.value && !hasVoted.value) {
    submitScore();
  }
};

onMounted(() => {
  connectWebSocket();
  window.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  if (socket) socket.close();
  window.removeEventListener('keydown', handleKeydown);
});
</script>

<style scoped>
.judge-app {
  background-color: #121212;
  color: #ffffff;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: 'Helvetica Neue', Arial, sans-serif;
  touch-action: manipulation;
}

.judge-header {
  background-color: #1e1e1e;
  padding: 15px 20px;
  border-bottom: 2px solid #333;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left { display: flex; align-items: center; gap: 15px; }
.header-left h1 { margin: 0; font-size: 1.2rem; letter-spacing: 1px; color: #fff; }

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: #d32f2f;
  box-shadow: 0 0 8px #d32f2f;
}
.status-dot.connected {
  background-color: #4caf50;
  box-shadow: 0 0 8px #4caf50;
}

.header-right { display: flex; align-items: center; gap: 15px; }
.judge-badge { font-weight: bold; background-color: #333; padding: 5px 12px; border-radius: 15px; color: #ff9800; }

.selection-screen {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

/* Layout pour organiser le vote en haut et le leaderboard en bas */
.voting-layout {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  gap: 20px;
}

.voting-screen, .judge-leaderboard {
  width: 100%;
  max-width: 800px;
}

.card {
  background-color: #1e1e1e;
  border: 1px solid #333;
  border-radius: 12px;
  padding: 30px;
  text-align: center;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}

.selection-screen h2 { font-size: 2rem; margin-top: 0; margin-bottom: 10px; }
.subtitle { color: #aaa; margin-bottom: 40px; font-size: 1.1rem; }

.judge-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  justify-content: center;
}

.skater-info { margin-bottom: 30px; border-bottom: 1px solid #333; padding-bottom: 20px; }
.skater-name { font-size: 3rem; margin: 0 0 10px 0; color: #fff; text-transform: uppercase; }
.run-info { font-size: 1.8rem; color: #1976d2; margin: 0; }
.max-run { color: #555; }

.waiting-vote, .voted-state { padding: 30px 20px; }
.pulse-icon { font-size: 4rem; margin-bottom: 20px; animation: pulse 2s infinite; }
.check-icon { font-size: 4rem; margin-bottom: 20px; }
.main-instruction { font-size: 1.5rem; font-weight: bold; color: #fff; margin-bottom: 10px; }
.sub-instruction { font-size: 1.2rem; color: #888; font-style: italic; }

@keyframes pulse { 0% { opacity: 0.5; transform: scale(0.9); } 50% { opacity: 1; transform: scale(1.1); } 100% { opacity: 0.5; transform: scale(0.9); } }

.voting-pad { display: flex; flex-direction: column; align-items: center; gap: 30px; }

.score-display {
  font-size: 6rem;
  font-weight: 900;
  background-color: #2a2a2a;
  padding: 10px 40px;
  border-radius: 12px;
  border: 2px solid #444;
  color: #fff;
  min-width: 250px;
  transition: color 0.3s;
}
.score-display.high-score { color: #4caf50; border-color: #4caf50; }
.score-display.low-score { color: #f44336; border-color: #f44336; }

.score-slider {
  width: 100%;
  max-width: 600px;
  height: 15px;
  border-radius: 10px;
  background: #333;
  outline: none;
  -webkit-appearance: none;
}
.score-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #1976d2;
  cursor: pointer;
  box-shadow: 0 0 10px rgba(0,0,0,0.5);
}

.score-inputs {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  flex-wrap: wrap;
}

.manual-input {
  width: 120px;
  text-align: center;
  font-size: 2rem;
  font-weight: bold;
  padding: 15px;
  background-color: #2a2a2a;
  color: #fff;
  border: 1px solid #444;
  border-radius: 8px;
}
.manual-input:focus { outline: none; border-color: #1976d2; }
.manual-input::-webkit-outer-spin-button, .manual-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }

.submitted-score {
  font-size: 5rem;
  font-weight: 900;
  color: #4caf50;
  margin: 20px 0;
}

/* BUTTONS */
.btn {
  padding: 12px 20px;
  font-size: 1.1rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
  transition: background-color 0.2s, transform 0.1s;
}
.btn:active { transform: scale(0.95); }
.btn.primary { background-color: #1976d2; color: white; }
.btn.success { background-color: #388e3c; color: white; }
.btn.warning { background-color: #f57c00; color: white; }
.btn.danger { background-color: #d32f2f; color: white; }
.btn.outline { background-color: transparent; border: 1px solid #666; color: #ccc; }
.btn.small { padding: 6px 12px; font-size: 0.9rem; }
.btn.huge { font-size: 1.5rem; padding: 25px 40px; border-radius: 12px; }
.btn.giant { font-size: 2rem; padding: 20px 50px; border-radius: 12px; width: 100%; max-width: 600px; margin-top: 20px; }
.btn.adjust { font-size: 1.5rem; padding: 15px 25px; min-width: 90px; }

.spinner {
  border: 6px solid #333;
  border-top: 6px solid #1976d2;
  border-radius: 50%;
  width: 60px;
  height: 60px;
  animation: spin 1s linear infinite;
  margin: 30px auto;
}
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

/* STYLES DU LEADERBOARD MINIATURE */
.judge-leaderboard h3 {
  margin-top: 0;
  color: #1976d2;
  font-size: 1.5rem;
  border-bottom: 1px solid #333;
  padding-bottom: 10px;
}
.mini-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 15px;
  text-align: left;
}
.mini-table th, .mini-table td {
  padding: 12px 10px;
  border-bottom: 1px solid #333;
  color: #e0e0e0;
}
.mini-table th {
  color: #888;
  font-size: 0.9rem;
  text-transform: uppercase;
}
.skater-cat {
  display: block;
  font-size: 0.8rem;
  color: #aaa;
  margin-top: 4px;
}
.right-align {
  text-align: right;
}
.score-cell {
  font-weight: bold;
  font-size: 1.2rem;
  color: #fff;
}
.dns-row td {
  color: #f44336;
  opacity: 0.7;
}
.dns-row .score-cell {
  color: #f44336;
}
</style>
