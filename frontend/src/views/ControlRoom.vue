<template>
  <div class="control-room" :class="{ 'dark-theme': isDarkMode }">
    <header class="header">
      <h1>Skate Contest - Control Room</h1>
      <div class="header-controls">
        <button class="btn-theme" @click="toggleTheme">
          {{ isDarkMode ? '☀️ Light' : '🌙 Dark' }}
        </button>
        <button class="btn warning small" v-if="isLive" @click="quitLiveMode">
          ⏹️ EXIT LIVE
        </button>
        <div v-if="isLive" class="live-indicator">🔴 LIVE</div>
      </div>
    </header>

    <!-- PHASE 1: SETUP -->
    <section v-if="!isLive" class="setup-section card">
      <h2>1. Event Setup & Registration</h2>

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
              <select v-model="newSkaterCategory">
                <option value="U12 Boy">U12 Boy</option>
                <option value="U12 Girl">U12 Girl</option>
                <option value="U15 Boy">U15 Boy</option>
                <option value="U15 Girl">U15 Girl</option>
                <option value="Open Boy">Open Boy</option>
                <option value="Open Girl">Open Girl</option>
              </select>
              <input v-model="newSkaterNationality" type="text" placeholder="Nationality (e.g. FRA)" maxlength="3" />
              <button class="btn primary" @click="addSkaterManually">Add Skater</button>
            </div>
            <div v-if="manualAddMessage" class="info-message">{{ manualAddMessage }}</div>
          </div>
        </div>

        <div class="skaters-list-container">
          <h3>Registered Skaters ({{ registeredSkaters.length }})</h3>
          <ul class="skaters-list">
            <li v-for="skater in registeredSkaters" :key="skater.id">
              <strong>{{ skater.first_name }} {{ skater.last_name }}</strong>
              - {{ skater.category }} ({{ skater.nationality }})
            </li>
            <li v-if="registeredSkaters.length === 0" class="empty-list">No skaters registered yet.</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- PHASE 2: TOURNAMENT SANDBOX (POOLS & HEATS) -->
    <section v-if="competitionId && !isLive" class="sandbox-section card">
      <h2>2. Tournament Sandbox (Pools & Heats)</h2>

      <div class="sandbox-filters">
        <div class="form-group">
          <label>Category:</label>
          <select v-model="selectedCategoryId" @change="fetchPools">
            <option disabled value="">-- Select Category --</option>
            <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>Phase:</label>
          <select v-model="selectedPhase" @change="fetchPools">
            <option value="Qualifications">Qualifications</option>
            <option value="Semi-Final">Semi-Final</option>
            <option value="Final">Final</option>
          </select>
        </div>
      </div>

      <div v-if="selectedCategoryId && selectedPhase" class="sandbox-workspace">
        <div class="pool-controls">
          <input v-model="newPoolName" type="text" placeholder="New Pool Name (e.g. Heat 1)" />
          <button class="btn primary" @click="createNewPool">+ Create Pool</button>
        </div>

        <div class="pools-grid">
          <div class="pool-card unassigned-pool">
            <h3>Unassigned Skaters ({{ unassignedSkaters.length }})</h3>
            <ul class="skater-assign-list">
              <li v-for="skater in unassignedSkaters" :key="skater.id">
                <span>{{ skater.first_name }} {{ skater.last_name }}</span>
                <select @change="assignSkater(skater.id, $event.target.value)">
                  <option value="" disabled selected>Assign to...</option>
                  <option v-for="pool in pools" :key="pool.id" :value="pool.id">{{ pool.name }}</option>
                </select>
              </li>
              <li v-if="unassignedSkaters.length === 0" class="empty-list">All skaters assigned!</li>
            </ul>
          </div>

          <div v-for="pool in pools" :key="pool.id" class="pool-card">
            <h3>{{ pool.name }} ({{ pool.competitors.length }})</h3>
            <ul class="skater-assign-list">
              <li v-for="skater in pool.competitors" :key="skater.competitor_id">
                <span>{{ skater.start_order }}. {{ skater.first_name }} {{ skater.last_name }}</span>
              </li>
              <li v-if="pool.competitors.length === 0" class="empty-list">Empty pool.</li>
            </ul>
          </div>
        </div>

        <hr style="margin: 20px 0;" />

        <div class="auto-generate-box">
          <h3>Auto-Generate Next Phase</h3>
          <p>Takes the Top N from the current phase, reverses their order, and distributes them into new pools.</p>
          <div class="input-row-small horizontal">
            <select v-model="genNextPhase">
              <option value="Semi-Final">To Semi-Final</option>
              <option value="Final">To Final</option>
            </select>
            <input v-model.number="genTopN" type="number" placeholder="Top N (e.g. 16)" title="Top N Skaters to Qualify" />
            <input v-model.number="genPoolCount" type="number" placeholder="Pools (e.g. 4)" title="Number of Pools to Create" />
            <button class="btn warning" @click="generateNextPhase">⚡ Generate</button>
          </div>
        </div>
      </div>

      <hr style="margin: 30px 0;" />

      <h2>3. Start Live Event</h2>
      <div class="form-group">
        <label>Number of Judges:</label>
        <select v-model="judgeCount" @change="saveState">
          <option :value="3">3 Judges</option>
          <option :value="5">5 Judges</option>
        </select>
        <button class="btn danger large wide" @click="startLiveEvent" :disabled="!competitionId">GO LIVE</button>
      </div>
    </section>

    <!-- PHASE 3: LIVE CONTROL DASHBOARD -->
    <section v-if="isLive" class="live-section card">
      <h2>Live Control Dashboard</h2>

      <div class="live-context-bar">
        <div class="form-group">
          <label>Active Category:</label>
          <select v-model="selectedCategoryId" @change="fetchPools">
            <option disabled value="">-- Select Category --</option>
            <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>Active Phase:</label>
          <select v-model="selectedPhase" @change="fetchPools">
            <option value="Qualifications">Qualifications</option>
            <option value="Semi-Final">Semi-Final</option>
            <option value="Final">Final</option>
          </select>
        </div>
        <div class="form-group">
          <label>Current Run Number:</label>
          <input v-model.number="currentRunNumber" type="number" min="1" max="3" />
        </div>
      </div>

      <div v-if="pools.length > 0" class="live-pools-grid">
        <div v-for="pool in pools" :key="pool.id" class="pool-card live-pool-card">
          <h3>{{ pool.name }}</h3>
          <ul class="skater-assign-list">
            <li v-for="skater in pool.competitors" :key="skater.competitor_id"
                :class="{ 'active-skater': currentCompetitorId === skater.competitor_id }">
              <span>{{ skater.start_order }}. {{ skater.first_name }} {{ skater.last_name }}</span>
              <button
                class="btn primary small"
                @click="prepCallSkater(skater.competitor_id, skater.first_name, skater.last_name)"
                :disabled="isVotingOpen"
              >
                Call
              </button>
            </li>
          </ul>
        </div>
      </div>
      <div v-else class="info-message">No pools found for this category and phase. Please set them up in the Sandbox.</div>

      <div class="call-skater-panel" v-if="currentCompetitorId">
        <div class="active-call-info">
          <h3>On Course: {{ currentSkaterName }} (Run {{ currentRunNumber }})</h3>
        </div>
        <div class="input-row">
          <button class="btn primary large" @click="callNextSkater">1. Push to Screen</button>
          <button class="btn warning large" @click="openVoting" :disabled="isVotingOpen">
            {{ isVotingOpen ? 'Voting is Open' : '2. Open Voting' }}
          </button>
          <button class="btn danger large" @click="markDNS" :disabled="isVotingOpen">☠️ DNS</button>
        </div>
      </div>

      <div v-if="currentCompetitorId && isVotingOpen && finalScore === null" class="organizer-judge-panel card-inner">
        <h3>Direct Judge Input (Organizer Backup)</h3>
        <div class="input-row">
          <div>
            <label>Acting as:</label>
            <select v-model.number="organizerJudgeId">
              <option v-for="i in judgeCount" :key="i" :value="i" :disabled="receivedScores.includes(i)">
                Judge {{ i }} {{ receivedScores.includes(i) ? '(Voted)' : '' }}
              </option>
            </select>
          </div>
          <div>
            <label>Score (0 - 100):</label>
            <input v-model.number="organizerScore" type="number" min="0" max="100" step="1" />
          </div>
          <button class="btn primary" @click="submitOrganizerScore">Submit Score</button>
        </div>
      </div>

      <div class="voting-status-panel">
        <h3>Judges Status</h3>
        <div class="judges-grid">
          <div v-for="i in judgeCount" :key="i" class="judge-indicator" :class="{ 'voted': receivedScores.includes(i) }">
            Judge {{ i }}
          </div>
        </div>
      </div>

      <div v-if="finalScore !== null" class="result-panel">
        <h3>Final Score for Run {{ currentRunNumber }}</h3>
        <div class="score-display">
          <span v-if="finalScore < 0">DNS</span>
          <span v-else>{{ finalScore.toFixed(2) }}</span>
        </div>
      </div>

      <hr style="margin: 30px 0;" />

      <div class="podium-control-panel">
        <button class="btn success large wide" @click="triggerPodium">🏆 SHOW PODIUM (END CONTEST)</button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';

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

const quitLiveMode = () => {
  if (confirm("Are you sure you want to exit Live Mode and return to the Setup / Sandbox phase?")) {
    isLive.value = false;
    saveState();
  }
};

const existingCompetitions = ref([]);
const selectedCompetitionId = ref('');
const eventDate = ref('');
const uploadMessage = ref('');
const newSkaterFirstName = ref('');
const newSkaterLastName = ref('');
const newSkaterCategory = ref('Open Boy');
const newSkaterNationality = ref('FRA');
const manualAddMessage = ref('');

const categories = ref([]);
const selectedCategoryId = ref('');
const selectedPhase = ref('Qualifications');
const pools = ref([]);
const newPoolName = ref('');

const genNextPhase = ref('Semi-Final');
const genTopN = ref(16);
const genPoolCount = ref(4);

const currentCompetitorId = ref(null);
const currentSkaterName = ref('');
const currentRunNumber = ref(1);
const receivedScores = ref([]);
const finalScore = ref(null);

const organizerJudgeId = ref(1);
const organizerScore = ref(50.0);

let socket = null;

const unassignedSkaters = computed(() => {
  if (!selectedCategoryId.value) return [];
  const categorySkaters = registeredSkaters.value.filter(s => s.category_id === selectedCategoryId.value);
  const assignedIds = pools.value.flatMap(p => p.competitors.map(c => c.competitor_id));
  return categorySkaters.filter(s => !assignedIds.includes(s.id));
});

onMounted(async () => {
  if (isLive.value) startLiveEvent();
  try {
    const response = await fetch('/competitions/');
    if (response.ok) existingCompetitions.value = await response.json();
  } catch (error) { console.error(error); }

  if (competitionId.value) {
    await fetchCategories();
    if (categories.value.length > 0) {
      selectedCategoryId.value = categories.value[0].id;
      await fetchPools();
    }
  }
});

const loadCompetition = async () => {
  if (!selectedCompetitionId.value) return;
  const comp = existingCompetitions.value.find(c => c.id === selectedCompetitionId.value);
  if (comp) {
    competitionId.value = comp.id;
    competitionName.value = comp.name;
    saveState();
    await fetchRegisteredSkaters();
    await fetchCategories();
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
      await fetchCategories();
    }
  } catch (error) { console.error(error); }
};

const fetchCategories = async () => {
  if (!competitionId.value) return;
  try {
    const response = await fetch(`/competitions/${competitionId.value}/categories/`);
    if (response.ok) {
      categories.value = await response.json();
    }
  } catch (error) { console.error(error); }
};

const fetchPools = async () => {
  if (!competitionId.value || !selectedCategoryId.value || !selectedPhase.value) return;
  try {
    const response = await fetch(`/competitions/${competitionId.value}/categories/${selectedCategoryId.value}/pools/?phase=${selectedPhase.value}`);
    if (response.ok) {
      pools.value = await response.json();
    }
  } catch (error) { console.error(error); }
};

const createNewPool = async () => {
  if (!newPoolName.value || !selectedCategoryId.value) return;
  try {
    const response = await fetch('/pools/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        competition_id: competitionId.value,
        category_id: selectedCategoryId.value,
        phase: selectedPhase.value,
        name: newPoolName.value
      })
    });
    if (response.ok) {
      newPoolName.value = '';
      await fetchPools();
    }
  } catch (error) { console.error(error); }
};

const assignSkater = async (skaterId, poolId) => {
  if (!poolId || !skaterId) return;

  const targetPool = pools.value.find(p => p.id === parseInt(poolId));
  const newOrder = targetPool ? targetPool.competitors.length + 1 : 1;

  try {
    const response = await fetch('/pools/assign/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pool_id: parseInt(poolId),
        competitor_id: skaterId,
        start_order: newOrder
      })
    });
    if (response.ok) {
      await fetchPools();
    }
  } catch (error) { console.error(error); }
};

const generateNextPhase = async () => {
  if (!competitionId.value || !selectedCategoryId.value) return;
  if (!confirm(`Are you sure you want to generate the ${genNextPhase.value} pools from the top ${genTopN.value} of ${selectedPhase.value}?`)) return;

  try {
    const response = await fetch(`/competitions/${competitionId.value}/categories/${selectedCategoryId.value}/generate-phase/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        current_phase: selectedPhase.value,
        next_phase: genNextPhase.value,
        top_n: genTopN.value,
        pools_count: genPoolCount.value
      })
    });
    if (response.ok) {
      alert(`Success! Generated ${genPoolCount.value} new pools for ${genNextPhase.value}.`);
      selectedPhase.value = genNextPhase.value;
      await fetchPools();
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
    if (response.ok) {
      await fetchRegisteredSkaters();
      await fetchCategories();
      uploadMessage.value = "Import successful!";
    }
  } catch (error) { console.error(error); }
};

const addSkaterManually = async () => {
  if (!newSkaterFirstName.value || !newSkaterLastName.value) return;
  try {
    const response = await fetch(`/competitions/${competitionId.value}/competitors/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        first_name: newSkaterFirstName.value,
        last_name: newSkaterLastName.value,
        category: newSkaterCategory.value,
        nationality: newSkaterNationality.value.toUpperCase()
      })
    });
    if (response.ok) {
      newSkaterFirstName.value = '';
      newSkaterLastName.value = '';
      await fetchRegisteredSkaters();
      await fetchCategories();
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
        if (!receivedScores.value.includes(payload.judge_id)) receivedScores.value.push(payload.judge_id);
        const nextUnvoted = Array.from({length: judgeCount.value}, (_, i) => i + 1).find(id => !receivedScores.value.includes(id));
        if (nextUnvoted) organizerJudgeId.value = nextUnvoted;
      } else if (payload.type === 'run_completed') {
        finalScore.value = payload.final_score;
        isVotingOpen.value = false;

        const skater = registeredSkaters.value.find(s => s.id === currentCompetitorId.value);
        const name = skater ? `${skater.first_name} ${skater.last_name}` : `ID #${currentCompetitorId.value}`;

        if (payload.is_dns || payload.final_score < 0) {
            finalScore.value = -1.0;
        }

        const existingIndex = liveLeaderboard.value.findIndex(s => s.id === currentCompetitorId.value);

        if (existingIndex !== -1) {
            if (payload.final_score > liveLeaderboard.value[existingIndex].score) {
                liveLeaderboard.value[existingIndex].score = payload.final_score;
            }
        } else {
            liveLeaderboard.value.push({ id: currentCompetitorId.value, name: name, score: payload.final_score, category: skater.category, nationality: skater.nationality });
        }
        liveLeaderboard.value.sort((a, b) => b.score - a.score);
        saveState();
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ action: "update_leaderboard", leaderboard: liveLeaderboard.value }));
        }
      }
    } catch (error) {}
  };
  socket.onclose = () => { setTimeout(startLiveEvent, 2000); };
};

const prepCallSkater = (skaterId, firstName, lastName) => {
  currentCompetitorId.value = skaterId;
  currentSkaterName.value = `${firstName} ${lastName}`;
  receivedScores.value = [];
  finalScore.value = null;
  organizerScore.value = 50.0;
  organizerJudgeId.value = 1;
  isVotingOpen.value = false;
};

const callNextSkater = () => {
  if (!socket || socket.readyState !== WebSocket.OPEN || !currentCompetitorId.value) return;
  saveState();

  const skater = registeredSkaters.value.find(s => s.id === currentCompetitorId.value);

  socket.send(JSON.stringify({
    action: "call_skater",
    competitor_id: currentCompetitorId.value,
    skater_name: currentSkaterName.value,
    category: skater ? skater.category : '',
    nationality: skater ? skater.nationality : '',
    phase: selectedPhase.value,
    run_number: currentRunNumber.value
  }));
};

const openVoting = () => {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  isVotingOpen.value = true;
  saveState();
  socket.send(JSON.stringify({ action: "open_voting" }));
};

const markDNS = () => {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  if (confirm(`CRITICAL ACTION: Are you sure you want to disqualify ${currentSkaterName.value} (DNS)? This will assign a score of -1.0 for this run.`)) {
    isVotingOpen.value = false;
    saveState();
    socket.send(JSON.stringify({ action: "dns_skater" }));
  }
};

const triggerPodium = () => {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  socket.send(JSON.stringify({ action: "show_podium", leaderboard: liveLeaderboard.value }));
};

const submitOrganizerScore = () => {
  if (!socket || socket.readyState !== WebSocket.OPEN || !isLive.value) return;
  if (receivedScores.value.includes(organizerJudgeId.value)) return;

  socket.send(JSON.stringify({ action: 'submit_score', judge_id: organizerJudgeId.value, score: organizerScore.value }));
  organizerScore.value = 50.0;
};

onUnmounted(() => { if (socket) socket.close(); });
</script>

<style scoped>
.control-room { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; color: #333; min-height: 100vh; transition: all 0.3s ease; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.header-controls { display: flex; align-items: center; gap: 15px; }
.btn-theme { background-color: #e0e0e0; border: none; padding: 8px 15px; border-radius: 20px; cursor: pointer; font-weight: bold; transition: background-color 0.3s; }
.btn-theme:hover { background-color: #d5d5d5; }
.live-indicator { background-color: #d32f2f; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold; animation: pulse 2s infinite; }
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
.card { background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 20px; }
.card-inner { background-color: #f9f9f9; border: 1px solid #ddd; padding: 15px; border-radius: 6px; margin-bottom: 20px; }

.sandbox-filters, .live-context-bar { display: flex; gap: 20px; background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; align-items: flex-end; }
.pool-controls { display: flex; gap: 10px; margin-bottom: 20px; }
.pools-grid, .live-pools-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
.pool-card { background: #fff; border: 1px solid #ccc; border-radius: 6px; padding: 15px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
.unassigned-pool { border: 2px dashed #ff9800; background: #fff3e0; }
.pool-card h3 { margin-top: 0; padding-bottom: 10px; border-bottom: 1px solid #eee; font-size: 1.1rem; }
.skater-assign-list { list-style: none; padding: 0; margin: 0; max-height: 250px; overflow-y: auto; }
.skater-assign-list li { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f0f0f0; font-size: 0.9rem; }
.skater-assign-list select { padding: 4px; font-size: 0.8rem; max-width: 100px; }
.auto-generate-box { background: #e8f5e9; padding: 20px; border-radius: 8px; border: 1px solid #c8e6c9; }
.horizontal { display: flex; flex-direction: row; align-items: center; gap: 10px; }
.active-skater { background-color: #fff9c4; font-weight: bold; border-left: 4px solid #fbc02d; padding-left: 5px !important; }

.form-group { display: flex; flex-direction: column; gap: 10px; }
input, select { padding: 10px; font-size: 1rem; border: 1px solid #ccc; border-radius: 4px; background-color: white; color: #333; }
.btn { padding: 12px 20px; font-size: 1rem; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
.btn.primary { background-color: #1976d2; color: white; }
.btn.warning { background-color: #f57c00; color: white; }
.btn.success { background-color: #388e3c; color: white; }
.btn.danger { background-color: #d32f2f; color: white; }
.btn.large { font-size: 1.2rem; padding: 15px; }
.btn.small { padding: 5px 10px; font-size: 0.85rem; }
.btn.wide { width: 100%; margin-top: 10px; }
.btn:disabled { background-color: #ccc; cursor: not-allowed; }
.success-message { color: #2e7d32; font-weight: bold; font-size: 1.2rem; margin-bottom: 20px; }
.info-message { color: #1976d2; font-style: italic; margin-top: 10px; }
.split-panel { display: flex; gap: 20px; margin-top: 20px; }
.import-box, .manual-box { flex: 1; background: #f9f9f9; padding: 15px; border-radius: 8px; border: 1px solid #ddd; }
.input-row-small { display: flex; flex-direction: column; gap: 10px; }
.skaters-list-container { margin-top: 20px; background: #fff; border: 1px solid #eee; padding: 15px; border-radius: 8px; }
.skaters-list { list-style: none; padding: 0; max-height: 200px; overflow-y: auto; }
.skaters-list li { padding: 10px; border-bottom: 1px solid #eee; }
.input-row { display: flex; gap: 20px; align-items: flex-end; margin-top: 20px; }
.judges-grid { display: flex; gap: 15px; margin-top: 10px; }
.judge-indicator { flex: 1; text-align: center; padding: 15px; background-color: #e0e0e0; border-radius: 4px; font-weight: bold; transition: background-color 0.3s; }
.judge-indicator.voted { background-color: #4caf50; color: white; }
.result-panel { margin-top: 30px; text-align: center; padding: 20px; background-color: #fff3e0; border-radius: 8px; border: 2px solid #ff9800; }
.score-display { font-size: 4rem; font-weight: bold; color: #e65100; }
.active-call-info { background: #1976d2; color: white; padding: 15px; border-radius: 8px; margin-top: 20px; }
.active-call-info h3 { margin: 0; font-size: 1.5rem; }

.control-room.dark-theme { background-color: #121212; color: #e0e0e0; }
.dark-theme .card { background: #1e1e1e; box-shadow: 0 2px 8px rgba(0,0,0,0.5); }
.dark-theme .card-inner { background-color: #252525; border-color: #444; }
.dark-theme .btn-theme { background-color: #333; color: #e0e0e0; }
.dark-theme .btn-theme:hover { background-color: #444; }
.dark-theme h1, .dark-theme h2, .dark-theme h3 { color: #ffffff; }
.dark-theme input, .dark-theme select { background-color: #2c2c2c; color: #ffffff; border-color: #444; }
.dark-theme .sandbox-filters, .dark-theme .live-context-bar { background: #1a237e; }
.dark-theme .pool-card { background: #2c2c2c; border-color: #444; }
.dark-theme .unassigned-pool { border-color: #f57c00; background: #3e2723; }
.dark-theme .skater-assign-list li { border-bottom-color: #444; }
.dark-theme .auto-generate-box { background: #1b5e20; border-color: #2e7d32; }
.dark-theme .active-skater { background-color: #4a401a; border-left-color: #ffd600; }
.dark-theme .import-box, .dark-theme .manual-box { background: #2c2c2c; border-color: #444; }
.dark-theme .skaters-list-container { background: #1e1e1e; border-color: #444; }
.dark-theme .skaters-list li { border-bottom-color: #333; }
.dark-theme .judge-indicator { background-color: #424242; color: #aaa; }
.dark-theme .judge-indicator.voted { background-color: #388e3c; color: white; }
.dark-theme .result-panel { background-color: #3e2723; border-color: #d84315; }
.dark-theme .score-display { color: #ffb74d; }
</style>
