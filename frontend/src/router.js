import { createRouter, createWebHashHistory } from 'vue-router';
import ControlRoom from './views/ControlRoom.vue';
import JudgePad from './views/JudgePad.vue';
import ScoreBoard from './views/ScoreBoard.vue';

const routes = [
  {
    path: '/',
    name: 'ControlRoom',
    component: ControlRoom
  },
  {
    path: '/judge',
    name: 'JudgePad',
    component: JudgePad
  },
  {
    path: '/board',
    name: 'ScoreBoard',
    component: ScoreBoard
  }
];

// Using Hash History (/#/board) avoids 404 errors with FastAPI
const router = createRouter({
  history: createWebHashHistory(),
  routes
});

export default router;
