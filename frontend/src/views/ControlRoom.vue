<template>
  <div class="control-room" :class="{ 'dark-theme': isDarkMode }">
    <header class="header">
      <h1>Skate Contest - Control Room</h1>
      <div class="header-controls">
        <button class="btn-theme" @click="toggleTheme">
          {{ isDarkMode ? '☀️ Light' : '🌙 Dark' }}
        </button>
        <div v-if="isLive" class="live-indicator">🔴 LIVE</div>
      </div>
    </header>

    <section v-if="!isLive" class="setup-section card">
      <h2>1. Event Setup</h2>
      <div v-if="!competitionId" class="setup-options">
        <div class="form-group load-box" v-if="existingCompetitions.length > 0">
          <h3>Load Existing Competition</h3>
          <select v-model="selectedCompetitionId">
            <option disabled value="">-- Select an event --</option>
            <option v-for="comp in existingCompetitions" :key="comp.id" :value="comp.id">
              {{ comp.event_date }} - {{ comp.name }}
            </option>
          </select>
          <button class="btn primary" @click="loadCompetition">Load</button>
        </div>

        <hr v-if="existingCompetitions.length > 0" />

        <div class="form-group">
          <h3>Create New Competition</h3>
          <label>Competition Name:</label>
          <input v-model="competitionName" type="text" placeholder="e.g., Summer Jam 2026" />
          <label>Event Date:</label>
          <input v-model="eventDate" type="date" />
          <button class="btn primary" @click="createCompetition">Create Competition</button>
        </div>
      </div>

      <div v-else class="registration-panel">
        <div class="success-message">
          Active Event: {{ competitionName }} (ID: {{ competitionId }})
        </div>

        <div class="split-panel">
          <div class="import-box">
            <h3>Import from Excel</h3>
            <input type="file" accept=".xlsx" @change="uploadExcel" />
            <div v-if="uploadMessage" class="info-message">{{ uploadMessage }}</div>
          </div>
          <div class="manual-box">
            <h3>Manual Entry (Wildcard)</h3>
            <div class="input-row-small">
              <input v-model="newSkaterFirstName" type="text" placeholder="First Name" />
              <input v-model="newSkaterLastName" type="text" placeholder="Last Name" />
              <input v-model.number="newSkaterBib" type="number" placeholder="Bib (e.g. 42)" />
              <button class="btn primary" @click="addSkaterManually">Add Skater</button>
            </div>
            <div v-if="manualAddMessage" class="info-message">{{ manualAddMessage }}</div>
          </div>
        </div>

        <div class="skaters-list-container">
          <h3>Registered Skaters ({{ registeredSkaters.length }})</h3>
          <ul class="skaters-list">
            <li v-for="skater in registeredSkaters" :key="skater.id">
              <strong>#{{ skater.bib_number }}</strong> - {{ skater.first_name }} {{ skater.last_name }}
            </li>
            <li v-if="registeredSkaters.length === 0" class="empty-list">No skaters registered yet.</li>
          </ul>
        </div>
        <hr />
        <h2>2. Start Live Event</h2>
        <div class="form-group">
          <label>Number of Judges:</label>
          <select v-model="judgeCount" @change="saveState">
            <option :value="3">3 Judges</option>
            <option :value="5">5 Judges</option>
          </select>
          <button class="btn danger large" @click="startLiveEvent">GO LIVE</button>
        </div>
      </div>
    </section>

    <!-- PHASE 2: LIVE CONTROL DASHBOARD -->
    <section v-else class="live-section card">
      <h2>Live Control Dashboard</h2>

      <div class="call-skater-panel">
        <div class="input-row">
          <div>
            <label>Competitor Bib Number:</label>
            <input v-model.number="currentCompetitorId" type="number" min="1" />
          </div>
          <div>
            <label>Run Number:</label>
            <input v-model.number="currentRunNumber" type="number" min="1" max="3" />
          </div>
          <!-- Bouton Étape 1 -->
          <button class="btn primary" @click="callNextSkater">1. Call Skater (On Course)</button>

          <!-- Bouton Étape 2 (Se désactive dès qu'on clique dessus) -->
          <button
            class="btn warning"
            @click="openVoting"
            :disabled="!currentCompetitorId || isVotingOpen"
          >
            {{ isVotingOpen ? 'Voting is Open' : '2. Open Voting' }}
          </button>
        </div>
      </div>

      <!-- Panneau de saisie Organisateur affiché SEULEMENT si les votes sont ouverts -->
      <div v-if="currentCompetitorId && isVotingOpen && finalScore === null" class="organizer-judge-panel card-inner">
        <h3>Direct Judge Input (Organizer Backup)</h3>
        <div class="input-row">
          <div>
            <label>Acting as:</label>
            <select v-model.number="organizerJudgeId">
              <option
                v-for="i in judgeCount"
                :key="i"
                :value="i"
                :disabled="receivedScores.includes(i)"
              >
                Judge {{ i }} {{ receivedScores.includes(i) ? '(Voted)' : '' }}
              </option>
            </select>
          </div>
          <div>
            <label>Score (0 - 10):</label>
            <input v-model.number="organizerScore" type="number" min="0.0" max="10.0" step="0.1" />
          </div>
          <button class="btn primary" @click="submitOrganizerScore">Submit Score</button>
        </div>
      </div>

      <div class="voting-status-panel">
        <h3>Judges Status</h3>
        <div class="judges-grid">
          <div
            v-for="i in judgeCount"
            :key="i"
            class="judge-indicator"
            :class="{ 'voted': receivedScores.includes(i) }"
          >
            Judge {{ i }}
          </div>
        </div>
      </div>

      <div v-if="finalScore !== null" class="result-panel">
        <h3>Final Score for Run {{ currentRunNumber }}</h3>
        <div class="score-display">{{ finalScore.toFixed(3) }}</div>
      </div>

      <hr style="margin: 30px 0;" />

      <div class="podium-control-panel">
        <button class="btn success large wide" @click="triggerPodium">🏆 SHOW PODIUM (END CONTEST)</button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const isDarkMode = ref(localStorage.getItem('control_room_theme') === 'dark');

const toggleTheme = () => {
  isDarkMode.value = !isDarkMode.value;
  localStorage.setItem('control_room_theme', isDarkMode.value ? 'dark' : 'light');
};

const isLive = ref(localStorage.getItem('is_live') === 'true');
const isVotingOpen = ref(localStorage.getItem('is_voting_open') === 'true');
const competitionId = ref(parseInt(localStorage.getItem('comp_id')) || null);
const competitionName = ref(localStorage.getItem('comp_name') || '');
const judgeCount = ref(parseInt(localStorage.getItem('judge_count')) || 3);
const liveLeaderboard = ref(JSON.parse(localStorage.getItem('leaderboard') || '[]'));
const registeredSkaters = ref(JSON.parse(localStorage.getItem('skaters') || '[]'));

const saveState = () => {
  localStorage.setItem('is_live', isLive.value);
  localStorage.setItem('is_voting_open', isVotingOpen.value);
  localStorage.setItem('comp_id', competitionId.value || '');
  localStorage.setItem('comp_name', competitionName.value);
  localStorage.setItem('judge_count', judgeCount.value);
  localStorage.setItem('leaderboard', JSON.stringify(liveLeaderboard.value));
  localStorage.setItem('skaters', JSON.stringify(registeredSkaters.value));
};

const existingCompetitions = ref([]);
const selectedCompetitionId = ref('');
const eventDate = ref('');
const uploadMessage = ref('');
const newSkaterFirstName = ref('');
const newSkaterLastName = ref('');
const newSkaterBib = ref('');
const manualAddMessage = ref('');

const currentCompetitorId = ref(null);
const currentRunNumber = ref(1);
const receivedScores = ref([]);
const finalScore = ref(null);

const organizerJudgeId = ref(1);
const organizerScore = ref(5.0);

let socket = null;

onMounted(async () => {
  if (isLive.value) {
    startLiveEvent();
  }

  try {
    const response = await fetch('/competitions/');
    if (response.ok) existingCompetitions.value = await response.json();
  } catch (error) {
    console.error(error);
  }
});

const loadCompetition = () => {
  if (!selectedCompetitionId.value) return;
  const comp = existingCompetitions.value.find(c => c.id === selectedCompetitionId.value);
  if (comp) {
    competitionId.value = comp.id;
    competitionName.value = comp.name;
    saveState();
    fetchRegisteredSkaters();
  }
};

const createCompetition = async () => {
  if (!competitionName.value || !eventDate.value) return;
  try {
    const response = await fetch('/competitions/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: competitionName.value, event_date: eventDate.value })
    });
    if (response.ok) {
      const data = await response.json();
      competitionId.value = data.competition_id;
      saveState();
      await fetchRegisteredSkaters();
    }
  } catch (error) { console.error(error); }
};

const fetchRegisteredSkaters = async () => {
  if (!competitionId.value) return;
  try {
    const response = await fetch(`/competitions/${competitionId.value}/competitors/`);
    if (response.ok) {
      registeredSkaters.value = await response.json();
      saveState();
    }
  } catch (error) { console.error(error); }
};

const uploadExcel = async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  try {
    const response = await fetch(`/competitions/${competitionId.value}/import-excel/`, {
      method: 'POST', body: formData
    });
    if (response.ok) await fetchRegisteredSkaters();
  } catch (error) { console.error(error); }
};

const addSkaterManually = async () => {
  if (!newSkaterFirstName.value || !newSkaterLastName.value || !newSkaterBib.value) return;
  try {
    const response = await fetch(`/competitions/${competitionId.value}/competitors/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        first_name: newSkaterFirstName.value,
        last_name: newSkaterLastName.value,
        bib_number: newSkaterBib.value
      })
    });
    if (response.ok) {
      newSkaterFirstName.value = '';
      newSkaterLastName.value = '';
      newSkaterBib.value = '';
      await fetchRegisteredSkaters();
    }
  } catch (error) { console.error(error); }
};

const startLiveEvent = () => {
  isLive.value = true;
  saveState();

  const serverIp = window.location.hostname || "127.0.0.1";
  socket = new WebSocket(`ws://${serverIp}:8000/ws`);

  socket.onopen = () => {
    socket.send(JSON.stringify({
      action: "start_live",
      judge_count: judgeCount.value,
      competition_name: competitionName.value
    }));

    if (liveLeaderboard.value.length > 0) {
      socket.send(JSON.stringify({ action: "update_leaderboard", leaderboard: liveLeaderboard.value }));
    }
  };

  socket.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);

      if (payload.type === 'voting_opened') {
        isVotingOpen.value = true;
        saveState();
      } else if (payload.type === 'score_received') {
        if (!receivedScores.value.includes(payload.judge_id)) {
          receivedScores.value.push(payload.judge_id);
        }
        const nextUnvoted = Array.from({length: judgeCount.value}, (_, i) => i + 1).find(id => !receivedScores.value.includes(id));
        if (nextUnvoted) organizerJudgeId.value = nextUnvoted;

      } else if (payload.type === 'run_completed') {
        finalScore.value = payload.final_score;
        isVotingOpen.value = false;

        const skater = registeredSkaters.value.find(s => s.bib_number === currentCompetitorId.value);
        const name = skater ? `${skater.first_name} ${skater.last_name}` : `Skater #${currentCompetitorId.value}`;

        const existingIndex = liveLeaderboard.value.findIndex(s => s.bib_number === currentCompetitorId.value);

        if (existingIndex !== -1) {
            if (payload.final_score > liveLeaderboard.value[existingIndex].score) {
                liveLeaderboard.value[existingIndex].score = payload.final_score;
            }
        } else {
            liveLeaderboard.value.push({ bib_number: currentCompetitorId.value, name: name, score: payload.final_score });
        }

        liveLeaderboard.value.sort((a, b) => b.score - a.score);
        liveLeaderboard.value = liveLeaderboard.value.slice(0, 10);
        saveState();

        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ action: "update_leaderboard", leaderboard: liveLeaderboard.value }));
        }
      }
    } catch (error) {}
  };

  socket.onclose = () => { setTimeout(startLiveEvent, 2000); };
};

const callNextSkater = () => {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  receivedScores.value = [];
  finalScore.value = null;
  organizerScore.value = 5.0;
  organizerJudgeId.value = 1;
  isVotingOpen.value = false;
  saveState();

  const skater = registeredSkaters.value.find(s => s.bib_number === currentCompetitorId.value);
  const skaterName = skater ? `${skater.first_name} ${skater.last_name}` : '';

  socket.send(JSON.stringify({
    action: "call_skater",
    competitor_id: currentCompetitorId.value,
    skater_name: skaterName,
    run_number: currentRunNumber.value
  }));
};

const openVoting = () => {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  isVotingOpen.value = true;
  saveState();
  socket.send(JSON.stringify({ action: "open_voting" }));
};

const triggerPodium = () => {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  socket.send(JSON.stringify({ action: "show_podium", leaderboard: liveLeaderboard.value }));
};

const submitOrganizerScore = () => {
  if (!socket || socket.readyState !== WebSocket.OPEN || !isLive.value) return;
  if (receivedScores.value.includes(organizerJudgeId.value)) return;

  socket.send(JSON.stringify({ action: 'submit_score', judge_id: organizerJudgeId.value, score: organizerScore.value }));
  organizerScore.value = 5.0;
};

onUnmounted(() => { if (socket) socket.close(); });
</script>

<style scoped>
/* CSS conservé à l'identique (Lights/Dark, boutons, etc.) */
.control-room { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; color: #333; min-height: 100vh; transition: all 0.3s ease; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.header-controls { display: flex; align-items: center; gap: 15px; }
.btn-theme { background-color: #e0e0e0; border: none; padding: 8px 15px; border-radius: 20px; cursor: pointer; font-weight: bold; transition: background-color 0.3s; }
.btn-theme:hover { background-color: #d5d5d5; }
.live-indicator { background-color: #d32f2f; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold; animation: pulse 2s infinite; }
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
.card { background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 20px; }
.card-inner { background-color: #f9f9f9; border: 1px solid #ddd; padding: 15px; border-radius: 6px; margin-bottom: 20px; }
.setup-options { display: flex; flex-direction: column; gap: 20px; }
.load-box { background-color: #e3f2fd; padding: 15px; border-radius: 6px; border: 1px solid #bbdefb; }
.form-group { display: flex; flex-direction: column; gap: 10px; }
input, select { padding: 10px; font-size: 1rem; border: 1px solid #ccc; border-radius: 4px; background-color: white; color: #333; }
.btn { padding: 12px 20px; font-size: 1rem; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; margin-top: 10px; }
.btn.primary { background-color: #1976d2; color: white; }
.btn.warning { background-color: #f57c00; color: white; }
.btn.success { background-color: #388e3c; color: white; }
.btn.danger { background-color: #d32f2f; color: white; }
.btn.large { font-size: 1.2rem; padding: 15px; }
.btn.wide { width: 100%; }
.btn:disabled { background-color: #ccc; cursor: not-allowed; }
.success-message { color: #2e7d32; font-weight: bold; font-size: 1.2rem; margin-bottom: 20px; }
.info-message { color: #1976d2; font-style: italic; margin-top: 10px; }
.split-panel { display: flex; gap: 20px; margin-top: 20px; }
.import-box, .manual-box { flex: 1; background: #f9f9f9; padding: 15px; border-radius: 8px; border: 1px solid #ddd; }
.input-row-small { display: flex; flex-direction: column; gap: 10px; }
.skaters-list-container { margin-top: 20px; background: #fff; border: 1px solid #eee; padding: 15px; border-radius: 8px; }
.skaters-list { list-style: none; padding: 0; max-height: 200px; overflow-y: auto; }
.skaters-list li { padding: 10px; border-bottom: 1px solid #eee; }
.skater-id { color: #888; font-size: 0.8rem; margin-left: 10px; }
.input-row { display: flex; gap: 20px; align-items: flex-end; }
.judges-grid { display: flex; gap: 15px; margin-top: 10px; }
.judge-indicator { flex: 1; text-align: center; padding: 15px; background-color: #e0e0e0; border-radius: 4px; font-weight: bold; transition: background-color 0.3s; }
.judge-indicator.voted { background-color: #4caf50; color: white; }
.result-panel { margin-top: 30px; text-align: center; padding: 20px; background-color: #fff3e0; border-radius: 8px; border: 2px solid #ff9800; }
.score-display { font-size: 4rem; font-weight: bold; color: #e65100; }
.control-room.dark-theme { background-color: #121212; color: #e0e0e0; }
.dark-theme .card { background: #1e1e1e; box-shadow: 0 2px 8px rgba(0,0,0,0.5); }
.dark-theme .card-inner { background-color: #252525; border-color: #444; }
.dark-theme .btn-theme { background-color: #333; color: #e0e0e0; }
.dark-theme .btn-theme:hover { background-color: #444; }
.dark-theme h1, .dark-theme h2, .dark-theme h3 { color: #ffffff; }
.dark-theme input, .dark-theme select { background-color: #2c2c2c; color: #ffffff; border-color: #444; }
.dark-theme .load-box { background-color: #1a237e; border-color: #3949ab; }
.dark-theme .import-box, .dark-theme .manual-box { background: #2c2c2c; border-color: #444; }
.dark-theme .skaters-list-container { background: #1e1e1e; border-color: #444; }
.dark-theme .skaters-list li { border-bottom-color: #333; }
.dark-theme .judge-indicator { background-color: #424242; color: #aaa; }
.dark-theme .judge-indicator.voted { background-color: #388e3c; color: white; }
.dark-theme .result-panel { background-color: #3e2723; border-color: #d84315; }
.dark-theme .score-display { color: #ffb74d; }
</style>