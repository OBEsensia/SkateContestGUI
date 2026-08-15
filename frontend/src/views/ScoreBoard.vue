<template>
  <div class="board-app">
    <header class="board-header">
      <div class="header-content">
        <div class="live-badge" :class="{ 'active': isLive }">
          {{ isLive ? '🔴 LIVE' : 'OFFLINE' }}
        </div>
        <h1>{{ competitionName.toUpperCase() }}</h1>
      </div>
    </header>

    <!-- MODE PODIUM -->
    <div v-if="isPodiumMode" class="podium-view">
      <h1 class="podium-title">🏆 PODIUM FINAL 🏆</h1>
      <div class="podium-podium-container">
        <!-- 2ème Place -->
        <div class="podium-step rank-2-step" v-if="leaderboard[1]">
          <div class="podium-score">{{ leaderboard[1].score.toFixed(2) }}</div>
          <div class="podium-name">{{ leaderboard[1].name }}</div>
          <div class="podium-badge">2</div>
        </div>
        <!-- 1ère Place -->
        <div class="podium-step rank-1-step" v-if="leaderboard[0]">
          <div class="podium-score gold-score">{{ leaderboard[0].score.toFixed(2) }}</div>
          <div class="podium-name gold-name">{{ leaderboard[0].name }}</div>
          <div class="podium-badge gold-badge">1</div>
        </div>
        <!-- 3ème Place -->
        <div class="podium-step rank-3-step" v-if="leaderboard[2]">
          <div class="podium-score">{{ leaderboard[2].score.toFixed(2) }}</div>
          <div class="podium-name">{{ leaderboard[2].name }}</div>
          <div class="podium-badge">3</div>
        </div>
      </div>
    </div>

    <!-- MODE STANDARD -->
    <div v-else class="board-content">
      <div class="current-action-panel card">
        <div v-if="!currentCompetitorId" class="waiting-state">
          <h2>Waiting for the next skater...</h2>
          <div class="spinner"></div>
        </div>

        <div v-else class="active-state">
          <div class="competitor-info">
            <span class="label">SKATER</span>
            <h2 class="competitor-id">#{{ currentCompetitorId }}</h2>
            <h3 class="skater-name" v-if="currentSkaterName">{{ currentSkaterName }}</h3>
            <h3 class="run-info">RUN {{ currentRunNumber }}</h3>
          </div>

          <div v-if="boardState === 'skating'" class="status-message-box skating">
            <h2>🔥 RUN IN PROGRESS 🔥</h2>
            <p>Skater on course</p>
          </div>

          <div v-else-if="boardState === 'voting'" class="progress-section">
            <p>Judges Voting...</p>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: progressPercentage + '%' }"></div>
            </div>
            <p class="votes-count">{{ receivedVotes }} / {{ totalJudges }} Votes</p>
          </div>

          <div v-else-if="boardState === 'scored'" class="score-section">
            <div class="score-label">FINAL SCORE</div>
            <div class="huge-score">{{ finalScore.toFixed(2) }}</div>
          </div>
        </div>
      </div>

      <div class="leaderboard-panel card">
        <h2>Top 10 Leaderboard</h2>
        <div class="table-responsive">
          <table class="leaderboard-table">
            <thead>
              <tr>
                <th class="col-rank">Rank</th>
                <th class="col-skater">Skater</th>
                <th class="col-score">Best Score</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(entry, index) in leaderboard" :key="index">
                <td class="col-rank"><span class="rank-badge" :class="'rank-' + (index + 1)">{{ index + 1 }}</span></td>
                <td class="col-skater">
                  <div class="lb-skater-name">{{ entry.name }}</div>
                  <div class="lb-bib">Bib #{{ entry.bib_number }}</div>
                </td>
                <td class="col-score highlight">{{ entry.score.toFixed(2) }}</td>
              </tr>
              <tr v-if="leaderboard.length === 0">
                <td colspan="3" class="empty-state">No scores recorded yet.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';

const isLive = ref(false);
const competitionName = ref('SKATE CONTEST');
const currentCompetitorId = ref(null);
const currentSkaterName = ref('');
const currentRunNumber = ref(null);
const finalScore = ref(null);
const receivedVotes = ref(0);
const totalJudges = ref(3);
const leaderboard = ref([]);

const boardState = ref('waiting');
const isPodiumMode = ref(false);

let socket = null;

const progressPercentage = computed(() => {
  if (totalJudges.value === 0) return 0;
  return (receivedVotes.value / totalJudges.value) * 100;
});

const connectWebSocket = () => {
  const serverIp = window.location.hostname || "127.0.0.1";
  socket = new WebSocket(`ws://${serverIp}:8000/ws`);

  socket.onopen = () => { isLive.value = true; };

  socket.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);

      if (payload.type === 'board_meta') {
        competitionName.value = payload.competition_name || 'SKATE CONTEST';
        if (payload.judge_count) totalJudges.value = payload.judge_count;
      }
      else if (payload.type === 'new_run') {
        currentCompetitorId.value = payload.competitor_id;
        currentSkaterName.value = payload.skater_name;
        currentRunNumber.value = payload.run_number;
        finalScore.value = null;
        receivedVotes.value = 0;
        boardState.value = 'skating';
        isPodiumMode.value = false;
      }
      else if (payload.type === 'voting_opened') {
        boardState.value = 'voting';
      }
      else if (payload.type === 'score_received') {
        receivedVotes.value++;
      }
      else if (payload.type === 'run_completed') {
        finalScore.value = payload.final_score;
        boardState.value = 'scored';
      }
      else if (payload.type === 'leaderboard_updated') {
        leaderboard.value = payload.leaderboard;
      }
      else if (payload.type === 'podium_mode') {
        isPodiumMode.value = true;
        if (payload.leaderboard) leaderboard.value = payload.leaderboard;
      }
    } catch (error) {}
  };

  socket.onclose = () => {
    isLive.value = false;
    setTimeout(connectWebSocket, 3000);
  };
};

onMounted(() => { connectWebSocket(); });
onUnmounted(() => { if (socket) socket.close(); });
</script>

<style scoped>
.board-app { background-color: #0a0a0a; color: #ffffff; min-height: 100vh; display: flex; flex-direction: column; font-family: 'Helvetica Neue', Arial, sans-serif; overflow-x: hidden; }
.board-header { background-color: #141414; padding: 15px 30px; border-bottom: 2px solid #333; }
.header-content { display: flex; align-items: center; gap: 20px; }
.board-header h1 { margin: 0; font-size: 1.5rem; letter-spacing: 2px; text-transform: uppercase; color: #fff; }
.live-badge { padding: 5px 12px; border-radius: 15px; font-weight: bold; background-color: #555; color: #aaa; font-size: 0.9rem; }
.live-badge.active { background-color: #d32f2f; color: white; animation: pulse 2s infinite; }
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }

.board-content { flex: 1; display: flex; flex-direction: row; gap: 20px; padding: 20px; }
@media (max-width: 900px) { .board-content { flex-direction: column; } }

.card { background-color: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 30px; display: flex; flex-direction: column; }
.current-action-panel { flex: 1; align-items: center; justify-content: center; text-align: center; }
.waiting-state h2 { color: #888; font-weight: normal; }
.competitor-info { margin-bottom: 30px; }
.label { color: #888; letter-spacing: 3px; font-size: 1.2rem; }
.competitor-id { font-size: clamp(3rem, 6vw, 5rem); margin: 10px 0; color: #fff; }
.skater-name { font-size: 2.2rem; color: #fff; margin: 0 0 15px 0; text-transform: uppercase; letter-spacing: 1px; }
.run-info { font-size: 2rem; color: #1976d2; margin: 0; }

.status-message-box.skating { background-color: rgba(255, 152, 0, 0.1); border: 2px solid #ff9800; padding: 20px 40px; border-radius: 10px; animation: glow 1.5s infinite alternate; }
.status-message-box.skating h2 { color: #ff9800; margin: 0 0 10px 0; font-size: 1.8rem; }
.status-message-box.skating p { color: #ccc; margin: 0; font-size: 1.2rem; text-transform: uppercase; letter-spacing: 2px; }
@keyframes glow { from { box-shadow: 0 0 5px rgba(255, 152, 0, 0.2); } to { box-shadow: 0 0 20px rgba(255, 152, 0, 0.6); } }

.progress-section { width: 100%; max-width: 400px; margin: 0 auto; }
.progress-bar { height: 20px; background-color: #333; border-radius: 10px; overflow: hidden; margin: 15px 0; }
.progress-fill { height: 100%; background-color: #4caf50; transition: width 0.3s ease; }
.votes-count { font-size: 1.2rem; color: #aaa; }

.score-section { animation: popIn 0.5s ease-out forwards; }
.score-label { font-size: 1.5rem; color: #ff9800; letter-spacing: 5px; margin-bottom: -10px; }
.huge-score { font-size: clamp(6rem, 15vw, 12rem); font-weight: 900; color: #fff; line-height: 1.1; text-shadow: 0 0 20px rgba(255, 152, 0, 0.4); }
@keyframes popIn { 0% { transform: scale(0.8); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }

.leaderboard-panel { flex: 1; }
.leaderboard-panel h2 { margin-top: 0; color: #fff; text-transform: uppercase; letter-spacing: 2px; border-bottom: 2px solid #333; padding-bottom: 15px; margin-bottom: 20px; }
.table-responsive { width: 100%; overflow-x: auto; }
.leaderboard-table { width: 100%; min-width: 400px; border-collapse: collapse; }
.leaderboard-table th, .leaderboard-table td { padding: 15px; text-align: left; border-bottom: 1px solid #333; }
.leaderboard-table th { color: #888; text-transform: uppercase; font-size: 0.9rem; }
.leaderboard-table tbody tr:hover { background-color: #222; }
.rank-badge { display: inline-block; width: 30px; height: 30px; line-height: 30px; text-align: center; background-color: #333; border-radius: 50%; font-weight: bold; }
.rank-1 { background-color: #ffd700; color: #000; }
.rank-2 { background-color: #c0c0c0; color: #000; }
.rank-3 { background-color: #cd7f32; color: #000; }
.lb-skater-name { font-weight: bold; font-size: 1.1rem; color: #fff; margin-bottom: 4px; }
.lb-bib { font-size: 0.85rem; color: #888; }
.col-score.highlight { font-weight: bold; color: #4caf50; font-size: 1.2rem; }
.empty-state { text-align: center !important; color: #666; padding: 30px !important; font-style: italic; }

.podium-view { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; background: radial-gradient(circle at center, #1a1a1a 0%, #0a0a0a 100%); padding: 40px; }
.podium-title { font-size: 3rem; letter-spacing: 4px; color: #ffd700; margin-bottom: 50px; text-transform: uppercase; text-shadow: 0 0 20px rgba(255, 215, 0, 0.4); }
.podium-podium-container { display: flex; align-items: flex-end; justify-content: center; gap: 30px; width: 100%; max-width: 800px; height: 400px; }
.podium-step { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; border-radius: 12px 12px 0 0; padding: 20px; position: relative; box-shadow: 0 10px 30px rgba(0,0,0,0.5); animation: slideUp 0.8s ease-out forwards; }
.rank-1-step { background: linear-gradient(to top, #b7950b, #d4ac0d); height: 100%; border: 2px solid #f1c40f; }
.rank-2-step { background: linear-gradient(to top, #7f8c8d, #95a5a6); height: 75%; border: 2px solid #bdc3c7; }
.rank-3-step { background: linear-gradient(to top, #a04000, #b9770e); height: 55%; border: 2px solid #e67e22; }
@keyframes slideUp { from { transform: translateY(50px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
.podium-badge { position: absolute; top: -25px; width: 50px; height: 50px; border-radius: 50%; background: #fff; color: #000; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; font-weight: bold; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
.gold-badge { background: #ffd700; border: 3px solid #fff; color: #000; font-size: 2rem; width: 60px; height: 60px; top: -30px; }
.podium-name { font-size: 1.5rem; font-weight: bold; text-align: center; margin-bottom: 10px; color: #fff; text-transform: uppercase; }
.gold-name { font-size: 2rem; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }
.podium-score { font-size: 1.8rem; font-weight: 900; color: #fff; background: rgba(0,0,0,0.3); padding: 5px 15px; border-radius: 20px; }
.gold-score { font-size: 2.5rem; background: rgba(0,0,0,0.4); color: #ffd700; }
</style>
