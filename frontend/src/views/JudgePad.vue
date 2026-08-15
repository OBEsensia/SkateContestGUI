<template>
  <div class="judge-app">
    <!-- State 1: Judge Selection -->
    <div v-if="!judgeId" class="setup-screen">
      <h1>Select Judge Position</h1>
      <div class="button-grid">
        <button v-for="id in activeJudgeCount" :key="id" @click="selectJudge(id)">
          Judge {{ id }}
        </button>
      </div>
    </div>

    <!-- State 2 & 3: Active Connection -->
    <div v-else class="active-screen">
      <div class="status-bar" :class="{ 'connected': isConnected }">
        {{ isConnected ? 'Connected - Judge ' + judgeId : 'Reconnecting...' }}
      </div>

      <!-- State 2A: Waiting for Next Run -->
      <div v-if="!currentCompetitorId" class="waiting-screen">
        <h2>Waiting for the Control Room...</h2>
        <div class="spinner"></div>
      </div>

      <!-- State 2B: Run in Progress (Skater on course, waiting for Open Voting) -->
      <div v-else-if="!isVotingOpen" class="waiting-screen skater-on-course">
        <h2>🔥 RUN IN PROGRESS 🔥</h2>
        <h3>Competitor #{{ currentCompetitorId }} - Run {{ currentRunNumber }}</h3>
        <p>Watch the run. Waiting for voting to open...</p>
        <div class="spinner"></div>
      </div>

      <!-- State 3: Scoring Screen (Voting is open) -->
      <div v-else class="scoring-screen">
        <h2>Competitor: {{ currentCompetitorId }}</h2>
        <h3>Run: {{ currentRunNumber }}</h3>

        <div class="score-input-container">
          <input
            type="number"
            class="score-input"
            v-model.number="currentScore"
            min="0.0"
            max="10.0"
            step="0.1"
            :disabled="hasSubmitted"
            @blur="validateManualInput"
          />
        </div>

        <div class="controls" :class="{ 'disabled': hasSubmitted }">
          <button class="adj-btn" @click="adjustScore(-1.0)">-1.0</button>
          <button class="adj-btn" @click="adjustScore(-0.1)">-0.1</button>
          <button class="adj-btn" @click="adjustScore(0.1)">+0.1</button>
          <button class="adj-btn" @click="adjustScore(1.0)">+1.0</button>
        </div>

        <button
          class="submit-btn"
          :disabled="hasSubmitted"
          @click="submitScore"
        >
          {{ hasSubmitted ? 'SCORE SUBMITTED' : 'SUBMIT SCORE' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const isConnected = ref(false);
const currentCompetitorId = ref(null);
const currentRunNumber = ref(null);
const currentScore = ref(5.0);
const hasSubmitted = ref(false);
const isVotingOpen = ref(false);

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
      } else if (payload.type === 'new_run') {
        currentCompetitorId.value = payload.competitor_id;
        currentRunNumber.value = payload.run_number;
        isVotingOpen.value = false;
        hasSubmitted.value = false;
      } else if (payload.type === 'voting_opened') {
        isVotingOpen.value = true;
        currentScore.value = 5.0;
        hasSubmitted.value = false;
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
  if (currentScore.value < 0.0) currentScore.value = 0.0;
  if (currentScore.value > 10.0) currentScore.value = 10.0;
  currentScore.value = Math.round(currentScore.value * 10) / 10;
};

const submitScore = () => {
  if (!socket || !isConnected.value || hasSubmitted.value) return;
  socket.send(JSON.stringify({ action: 'submit_score', judge_id: judgeId.value, score: currentScore.value }));
  hasSubmitted.value = true;
};

onUnmounted(() => { if (socket) socket.close(); });
</script>

<style scoped>
.judge-app { font-family: Arial, sans-serif; background-color: #121212; color: #ffffff; height: 100vh; display: flex; flex-direction: column; }
.setup-screen { padding: 20px; text-align: center; }
.button-grid { display: flex; flex-direction: column; gap: 15px; max-width: 400px; margin: 0 auto; }
.button-grid button { padding: 20px; font-size: 1.5rem; background-color: #1976d2; color: white; border: none; border-radius: 10px; }
.status-bar { background-color: #d32f2f; color: white; padding: 10px; text-align: center; font-weight: bold; }
.status-bar.connected { background-color: #388e3c; }
.waiting-screen { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 20px; }
.skater-on-course h2 { color: #ff9800; margin-bottom: 10px; font-size: 2rem; }
.skater-on-course h3 { color: #fff; margin-bottom: 10px; }
.skater-on-course p { color: #aaa; margin-top: 10px; text-transform: uppercase; letter-spacing: 1px; }
.scoring-screen { padding: 20px; display: flex; flex-direction: column; }
h2, h3 { text-align: center; margin: 10px 0; }
.score-input-container { display: flex; justify-content: center; margin: 20px 0; }
.score-input { font-size: 6rem; text-align: center; font-weight: bold; background-color: transparent; color: #ffffff; border: 2px dashed #424242; border-radius: 10px; width: 80%; max-width: 300px; padding: 10px; }
.score-input:focus { outline: none; border-color: #1976d2; background-color: rgba(25, 118, 210, 0.1); }
.score-input:disabled { border: 2px solid transparent; color: #888888; }
.score-input::-webkit-outer-spin-button, .score-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.score-input[type=number] { -moz-appearance: textfield; }
.controls { display: flex; justify-content: space-around; margin-bottom: 30px; }
.adj-btn { font-size: 2rem; padding: 20px; background-color: #424242; color: white; border: none; border-radius: 10px; touch-action: manipulation; }
.submit-btn { width: 100%; font-size: 2.5rem; padding: 30px; background-color: #1976d2; color: white; border: none; border-radius: 15px; font-weight: bold; }
.submit-btn:disabled, .controls.disabled .adj-btn { background-color: #555555; color: #888888; }
</style>
