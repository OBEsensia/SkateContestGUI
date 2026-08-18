<template>
  <div class="judge-app">
    <div v-if="!judgeId" class="setup-screen">
      <h1>Select Judge Position</h1>
      <div class="button-grid">
        <button v-for="id in activeJudgeCount" :key="id" @click="selectJudge(id)">
          Judge {{ id }}
        </button>
      </div>
    </div>

    <div v-else class="active-screen">
      <div class="status-bar" :class="{ 'connected': isConnected }">
        {{ isConnected ? 'Connected - Judge ' + judgeId : 'Reconnecting...' }}
      </div>

      <div v-if="!currentCompetitorId" class="waiting-screen">
        <h2>Waiting for the Control Room...</h2>
        <div class="spinner"></div>
      </div>

      <div v-else-if="!isVotingOpen" class="waiting-screen skater-on-course">
        <h2>🔥 RUN IN PROGRESS 🔥</h2>
        <h3 class="phase-info">{{ currentPhase }} - Run {{ currentRunNumber }}</h3>
        <h2 class="skater-name">{{ currentSkaterName }}</h2>
        <p class="skater-meta">{{ currentNationality }} - {{ currentCategory }}</p>
        <p class="instruction">Watch the run. Waiting for voting to open...</p>
        <div class="spinner"></div>
      </div>

      <div v-else class="scoring-screen">
        <h3 class="phase-info">{{ currentPhase }} - Run {{ currentRunNumber }}</h3>
        <h2 class="skater-name">{{ currentSkaterName }}</h2>
        <p class="skater-meta">{{ currentNationality }} - {{ currentCategory }}</p>

        <div class="score-input-container">
          <input
            type="number"
            class="score-input"
            v-model.number="currentScore"
            min="0"
            max="100"
            step="0.1"
            :disabled="hasSubmitted"
            @blur="validateManualInput"
          />
        </div>

        <div class="controls-grid" :class="{ 'disabled': hasSubmitted }">
          <button class="adj-btn" @click="adjustScore(-10)">-10</button>
          <button class="adj-btn" @click="adjustScore(-5)">-5</button>
          <button class="adj-btn" @click="adjustScore(5)">+5</button>
          <button class="adj-btn" @click="adjustScore(10)">+10</button>

          <button class="adj-btn fine-tune" @click="adjustScore(-1)">-1</button>
          <button class="adj-btn fine-tune" @click="adjustScore(-0.1)">-0.1</button>
          <button class="adj-btn fine-tune" @click="adjustScore(0.1)">+0.1</button>
          <button class="adj-btn fine-tune" @click="adjustScore(1)">+1</button>
        </div>

        <button
          class="submit-btn"
          :disabled="hasSubmitted"
          @click="submitScore"
        >
          {{ hasSubmitted ? 'SCORE SUBMITTED' : 'SUBMIT SCORE' }}
        </button>
      </div>

      <div class="judge-leaderboard" v-if="leaderboard.length > 0">
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
import { ref, onMounted, onUnmounted } from 'vue';

const isConnected = ref(false);
const currentCompetitorId = ref(null);
const currentSkaterName = ref('');
const currentCategory = ref('');
const currentNationality = ref('');
const currentPhase = ref('');
const currentRunNumber = ref(null);

const currentScore = ref(50.0);
const hasSubmitted = ref(false);
const isVotingOpen = ref(false);

const leaderboard = ref([]);

const judgeId = ref(parseInt(sessionStorage.getItem('judge_id')) || null);
const activeJudgeCount = ref(5);
let socket = null;

onMounted(() => {
  if (judgeId.value) connectWebSocket();
});

const selectJudge = (selectedId) => {
  judgeId.value = selectedId;
  sessionStorage.setItem('judge_id', selectedId);
  connectWebSocket();
};

const connectWebSocket = () => {
  const serverIp = window.location.hostname || "127.0.0.1";
  socket = new WebSocket(`ws://${serverIp}:8000/ws`);

  socket.onopen = () => { isConnected.value = true; };

  socket.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);

      if (payload.type === 'board_meta') {
        if (payload.judge_count) activeJudgeCount.value = payload.judge_count;
      }
      else if (payload.type === 'new_run') {
        currentCompetitorId.value = payload.competitor_id;
        currentSkaterName.value = payload.skater_name;
        currentCategory.value = payload.category || '';
        currentNationality.value = payload.nationality || '';
        currentPhase.value = payload.phase || 'Qualifications';
        currentRunNumber.value = payload.run_number;

        if (payload.previous_scores && payload.previous_scores[judgeId.value] !== undefined) {
            currentScore.value = payload.previous_scores[judgeId.value];
        } else {
            currentScore.value = 50.0;
        }

        isVotingOpen.value = false;
        hasSubmitted.value = false;
      }
      else if (payload.type === 'voting_opened') {
        isVotingOpen.value = true;
        hasSubmitted.value = false;
      }
      else if (payload.type === 'run_completed') {
        if (payload.is_cancelled) {
          currentCompetitorId.value = null;
        }
        isVotingOpen.value = false;
        hasSubmitted.value = false;
      }
      // MISE A JOUR DU CLASSEMENT EN TEMPS REEL
      else if (payload.type === 'leaderboard_updated') {
        leaderboard.value = payload.leaderboard;
      }
      else if (payload.type === 'podium_mode') {
        if (payload.leaderboard) leaderboard.value = payload.leaderboard;
      }
    } catch (error) {}
  };

  socket.onclose = () => {
    isConnected.value = false;
    setTimeout(connectWebSocket, 2000);
  };
};

const adjustScore = (amount) => {
  if (hasSubmitted.value) return;
  currentScore.value += amount;
  validateManualInput();
};

const validateManualInput = () => {
  if (currentScore.value === '' || isNaN(currentScore.value)) currentScore.value = 0.0;
  if (currentScore.value < 0) currentScore.value = 0.0;
  if (currentScore.value > 100) currentScore.value = 100.0;
  currentScore.value = Math.round(currentScore.value * 10) / 10;
};

const submitScore = () => {
  if (!socket || !isConnected.value || hasSubmitted.value) return;
  socket.send(JSON.stringify({
    action: 'submit_score',
    judge_id: judgeId.value,
    score: currentScore.value
  }));
  hasSubmitted.value = true;
};

onUnmounted(() => { if (socket) socket.close(); });
</script>

<style scoped>
.judge-app { font-family: Arial, sans-serif; background-color: #121212; color: #ffffff; min-height: 100vh; display: flex; flex-direction: column; overflow-y: auto; }
.setup-screen { padding: 20px; text-align: center; }
.button-grid { display: flex; flex-direction: column; gap: 15px; max-width: 400px; margin: 0 auto; }
.button-grid button { padding: 20px; font-size: 1.5rem; background-color: #1976d2; color: white; border: none; border-radius: 10px; }
.status-bar { background-color: #d32f2f; color: white; padding: 10px; text-align: center; font-weight: bold; position: sticky; top: 0; z-index: 10; }
.status-bar.connected { background-color: #388e3c; }

.active-screen { flex: 1; display: flex; flex-direction: column; }
.waiting-screen { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 20px; }
.skater-on-course h2 { color: #ff9800; margin-bottom: 5px; font-size: 2.5rem; }
.phase-info { color: #1976d2; font-size: 1.5rem; margin: 10px 0 20px 0; text-transform: uppercase; letter-spacing: 1px; }
.skater-name { color: #fff; font-size: 2.2rem; margin: 0; text-transform: uppercase; }
.skater-meta { color: #aaa; font-size: 1.2rem; margin: 5px 0 20px 0; }
.instruction { color: #888; margin-top: 10px; text-transform: uppercase; letter-spacing: 1px; }

.scoring-screen { padding: 20px; display: flex; flex-direction: column; align-items: center; flex-shrink: 0; }
.scoring-screen .phase-info { margin-bottom: 5px; }
.scoring-screen .skater-meta { margin-bottom: 10px; }

.score-input-container { display: flex; justify-content: center; margin: 20px 0; width: 100%; }
.score-input { font-size: 6rem; text-align: center; font-weight: bold; background-color: transparent; color: #ffffff; border: 2px dashed #424242; border-radius: 10px; width: 80%; max-width: 300px; padding: 10px; }
.score-input:focus { outline: none; border-color: #1976d2; background-color: rgba(25, 118, 210, 0.1); }
.score-input:disabled { border: 2px solid transparent; color: #888888; }
.score-input::-webkit-outer-spin-button, .score-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.score-input[type=number] { -moz-appearance: textfield; }

.controls-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; width: 100%; max-width: 500px; margin-bottom: 30px; }
.adj-btn { font-size: 1.5rem; padding: 15px 0; background-color: #424242; color: white; border: none; border-radius: 10px; touch-action: manipulation; }
.fine-tune { background-color: #2c2c2c; border: 1px solid #444; }
.submit-btn { width: 100%; max-width: 500px; font-size: 2.5rem; padding: 30px; background-color: #1976d2; color: white; border: none; border-radius: 15px; font-weight: bold; }
.submit-btn:disabled, .controls-grid.disabled .adj-btn { background-color: #555555; color: #888888; }

/* Leaderboard Tablet Styling */
.judge-leaderboard { margin: 20px auto 40px auto; padding: 20px; background-color: #1a1a1a; border-radius: 12px; border: 1px solid #333; width: 90%; max-width: 600px; }
.judge-leaderboard h3 { color: #888; font-size: 1.2rem; margin-top: 0; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px; text-align: center; }
.mini-table { width: 100%; border-collapse: collapse; text-align: left; }
.mini-table th { color: #666; border-bottom: 1px solid #444; padding-bottom: 8px; text-transform: uppercase; font-size: 0.85rem; }
.mini-table td { padding: 12px 0; border-bottom: 1px solid #2c2c2c; color: #ddd; font-size: 1.1rem; }
.mini-table .right-align { text-align: right; }
.mini-table .score-cell { font-weight: bold; color: #4caf50; }
.skater-cat { font-size: 0.8rem; color: #666; margin-left: 8px; font-weight: normal; }
.dns-row td { color: #ff5252; opacity: 0.6; }
.dns-row .score-cell { color: #ff5252; }
</style>