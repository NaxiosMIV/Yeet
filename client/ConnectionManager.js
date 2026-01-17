import { renderCanvas, screenToWorld, camera } from "./RenderCanvas.js";
import { updateLeaderboard } from "./UIManager.js";

// DOM References
const elements = {
  startScreen: document.getElementById("start-screen"),
  gameUI: document.getElementById("game-ui"),
  setupSection: document.getElementById("setup-section"),
  userDisplayName: document.getElementById("user-name"),
  authOverlay: document.getElementById("auth-overlay"),
  createTab: document.getElementById("createTab"),
  joinTab: document.getElementById("joinTab"),
  joinBox: document.getElementById("joinBox"),
  roomInput: document.getElementById("roomInput"),
  startBtn: document.getElementById("startBtn"),
  canvas: document.getElementById("game-canvas"),
  resetCam: document.getElementById("reset-cam"),
  googleContainer: document.getElementById("googleButtonContainer"),
  guestBtn: document.getElementById("customGuestBtn")
};

let globalWs;
let mode = "create";
window.myPlayerName = "Guest";

// --- STARTUP LOGIC ---
const init = () => {
  // 1. Mirror the Card Pieces
  const template = document.getElementById('login-template').innerHTML;
  document.querySelectorAll('.card-content').forEach(el => el.innerHTML = template);

  // 2. Setup UI Events
  setupUIEvents();

  // 3. Initialize Google Identity
  initGoogleIdentity();
};

const setupUIEvents = () => {
  elements.createTab.onclick = () => {
    mode = "create";
    elements.joinBox.classList.add("hidden");
    elements.createTab.className = "flex-1 py-2.5 rounded-xl font-bold text-sm bg-white dark:bg-slate-700 shadow text-primary";
    elements.joinTab.className = "flex-1 py-2.5 rounded-xl font-bold text-sm text-slate-500";
  };

  elements.joinTab.onclick = () => {
    mode = "join";
    elements.joinBox.classList.remove("hidden");
    elements.joinTab.className = "flex-1 py-2.5 rounded-xl font-bold text-sm bg-white dark:bg-slate-700 shadow text-primary";
    elements.createTab.className = "flex-1 py-2.5 rounded-xl font-bold text-sm text-slate-500";
  };

  elements.guestBtn.onclick = () => {
    handleLoginSuccess("Guest_" + Math.floor(Math.random() * 9000 + 1000));
  };

  elements.startBtn.onclick = () => {
    const room = mode === "create" ? 
      Math.random().toString(36).substring(2, 6).toUpperCase() : 
      elements.roomInput.value.trim().toUpperCase();
    
    if (mode === "join" && !room) return alert("Enter room code");
    joinGame(room, window.myPlayerName);
  };

  elements.resetCam.onclick = () => {
    camera.x = 0; camera.y = 0; camera.zoom = 40;
    if (window.lastKnownState) renderCanvas(window.lastKnownState);
  };
};

const initGoogleIdentity = () => {
  // Define global callback for Google
  window.handleCredentialResponse = (response) => {
    const payload = JSON.parse(atob(response.credential.split('.')[1]));
    handleLoginSuccess(payload.given_name || payload.name);
  };

  // Check if library is ready, then render
  const interval = setInterval(() => {
    if (window.google) {
      clearInterval(interval);
      google.accounts.id.initialize({
        client_id: "840399228482-6dj06avf54hj9dlffhbdpf6k6fga2m7e.apps.googleusercontent.com",
        callback: window.handleCredentialResponse,
        use_fedcm_for_prompt: false
      });
      google.accounts.id.renderButton(elements.googleContainer, {
        theme: "outline", size: "large", width: "250", shape: "pill"
      });
    }
  }, 100);
};

const handleLoginSuccess = (name) => {
  window.myPlayerName = name;
  elements.userDisplayName.innerText = name;
  elements.authOverlay.style.display = 'none';

  // Trigger Explosion Animation
  ['.tl', '.tr', '.bl', '.br'].forEach(cls => {
    document.querySelector(cls).classList.add(`throw-${cls.replace('.', '')}`);
  });

  setTimeout(() => {
    elements.setupSection.classList.add('opacity-100', 'scale-100');
  }, 400);
};

// --- CORE GAME NETWORKING ---
function joinGame(room, name) {
  elements.startScreen.classList.add("hidden");
  elements.gameUI.classList.remove("hidden");

  const protocol = location.protocol === "https:" ? "wss" : "ws";
  globalWs = new WebSocket(`${protocol}://${location.host}/ws?room=${room}&name=${name}`);

  globalWs.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (!data.state) return;
    if (data.type === "INIT") window.myPlayerId = data.playerId;
    
    window.lastKnownState = data.state;
    renderCanvas(data.state);
    updateLeaderboard(data.state.players, window.myPlayerId);
  };
}

// Canvas Interaction
elements.canvas.addEventListener('click', (e) => {
  if (camera.wasDragging) return;
  const rect = elements.canvas.getBoundingClientRect();
  const worldPos = screenToWorld(e.clientX - rect.left, e.clientY - rect.top, rect);
  const char = prompt("Enter a letter:");
  
  if (char && char.length === 1 && globalWs?.readyState === WebSocket.OPEN) {
    globalWs.send(JSON.stringify({
      type: "PLACE", x: worldPos.tileX, y: worldPos.tileY, letter: char.toUpperCase()
    }));
  }
});

// Run Init
init();