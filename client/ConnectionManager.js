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
  guestBtn: document.getElementById("customGuestBtn"),
  // New Color Picker Elements
  colorPickerContainer: document.getElementById("color-picker-container"),
  hueSlider: document.getElementById("hue-slider"),
  colorPreview: document.getElementById("color-preview")
};

let globalWs;
let mode = "create";
let selectedColor = "#6366F1"; // Default primary color
window.myPlayerName = "Guest";

// --- STARTUP LOGIC ---
const init = async () => {
  // 1. Mirror the Card Pieces
  const template = document.getElementById('login-template').innerHTML;
  document.querySelectorAll('.card-content').forEach(el => el.innerHTML = template);

  setupUIEvents();

  // 3. Check for existing session (Automatic login)
  await checkExistingSession();

  // 4. Initialize Google Identity
  initGoogleIdentity();
};

const checkExistingSession = async () => {
  try {
    const response = await fetch('/auth/login/guest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: null })
    });
    const result = await response.json();
    if (response.ok && result.status === "success") {
      handleLoginSuccess(result.user, true);
    }
  } catch (error) {
    console.error("Session check failed:", error);
  }
};

const setupUIEvents = () => {
  elements.createTab.onclick = () => {
    mode = "create";
    elements.joinBox.classList.add("hidden");
    elements.createTab.className = "flex-1 py-2.5 rounded-xl font-bold text-sm bg-white shadow text-[#6366F1]";
    elements.joinTab.className = "flex-1 py-2.5 rounded-xl font-bold text-sm text-slate-400";
  };

  elements.joinTab.onclick = () => {
    mode = "join";
    elements.joinBox.classList.remove("hidden");
    elements.joinTab.className = "flex-1 py-2.5 rounded-xl font-bold text-sm bg-white dark:bg-slate-700 shadow text-[#6366F1]";
    elements.createTab.className = "flex-1 py-2.5 rounded-xl font-bold text-sm text-slate-500";
  };

  elements.guestBtn.onclick = async () => {
    try {
      const response = await fetch('/auth/login/guest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: null })
      });
      const result = await response.json();
      if (response.ok) {
        handleLoginSuccess(result.user, false);
      } else {
        alert("Guest login failed");
      }
    } catch (error) {
      console.error("Guest login error:", error);
    }
    elements.joinTab.className = "flex-1 py-2.5 rounded-xl font-bold text-sm bg-white shadow text-[#6366F1]";
    elements.createTab.className = "flex-1 py-2.5 rounded-xl font-bold text-sm text-slate-400";
  };

  elements.guestBtn.onclick = () => {
    handleLoginSuccess("Guest_" + Math.floor(Math.random() * 9000 + 1000), false);
  };

  // Color Picker Logic
  if (elements.hueSlider) {
    elements.hueSlider.oninput = (e) => {
      const hue = e.target.value;
      // We use HSL for easier color math; 70% saturation and 60% lightness keeps it vibrant
      selectedColor = `hsl(${hue}, 70%, 60%)`;
      elements.colorPreview.style.backgroundColor = selectedColor;
    };
  }

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

const initGoogleIdentity = async () => {
  // Define global callback for Google
  window.handleCredentialResponse = async (response) => {
    try {
      const backendResponse = await fetch('/auth/login/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: response.credential })
      });
      const result = await backendResponse.json();
      if (backendResponse.ok) {
        handleLoginSuccess(result.user, true);
      } else {
        console.error("Google login backend failure:", result);
      }
    } catch (error) {
      console.error("Google login error:", error);
    }
  };

  try {
    const configResponse = await fetch('/auth/config');
    const config = await configResponse.json();

    if (!config.google_client_id) return;

    const interval = setInterval(() => {
      if (window.google) {
        clearInterval(interval);
        google.accounts.id.initialize({
          client_id: config.google_client_id,
          callback: window.handleCredentialResponse,
          use_fedcm_for_prompt: false
        });
        google.accounts.id.renderButton(elements.googleContainer, {
          theme: "outline", size: "large", width: "250", shape: "pill"
        });
      }
    }, 100);
  } catch (error) {
    console.error("Failed to load Google config:", error);
  }
};

const handleLoginSuccess = (name, isAuthorized = false) => {
  window.myPlayerName = name;
  elements.userDisplayName.innerText = name;
  elements.authOverlay.style.display = 'none';

  // Show color picker ONLY if authorized via Google
  if (isAuthorized && elements.colorPickerContainer) {
    elements.colorPickerContainer.classList.remove("hidden");
  }

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
  document.getElementById("room-id-text").innerText = room;

  const protocol = location.protocol === "https:" ? "wss" : "ws";
  // Added 'color' parameter to the WebSocket handshake
  const colorParam = encodeURIComponent(selectedColor);
  globalWs = new WebSocket(`${protocol}://${location.host}/ws?room=${room}&name=${name}&color=${colorParam}`);

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

init();