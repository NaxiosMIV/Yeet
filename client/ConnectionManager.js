import { renderCanvas, screenToWorld, camera, rackState } from "./RenderCanvas.js";
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
  colorPreview: document.getElementById("color-preview"),
  logoutBtn: document.getElementById("logoutBtn"),
  lobbyLogoutBtn: document.getElementById("lobbyLogoutBtn")
};

export let globalWs;
let mode = "create";
let selectedColor = "#6366F1"; // Default primary color
window.myPlayerName = "Guest";

function hslToHex(h, s, l) {
  l /= 100;
  const a = s * Math.min(l, 1 - l) / 100;
  const f = n => {
    const k = (n + h / 30) % 12;
    const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color).toString(16).padStart(2, '0');
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}

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
    const response = await fetch('/auth/me');
    const result = await response.json();
    if (response.ok && result.status === "success") {
      handleLoginSuccess(result.user.name, true, result.user.color_hue);
    }
  } catch (error) {
    console.error("Session check failed:", error);
  }
};

const setupUIEvents = () => {
  elements.createTab.onclick = () => {
    mode = "create";
    elements.joinBox.classList.add("hidden");
    elements.createTab.className = "flex-1 py-2.5 rounded-xl font-bold text-sm bg-white shadow text-[var(--user-color)]";
    elements.joinTab.className = "flex-1 py-2.5 rounded-xl font-bold text-sm text-slate-400";
  };

  elements.joinTab.onclick = () => {
    mode = "join";
    elements.joinBox.classList.remove("hidden");
    elements.joinTab.className = "flex-1 py-2.5 rounded-xl font-bold text-sm bg-white shadow text-[var(--user-color)]";
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
        // Guest also gets a hue (your backend generates a random one for them)
        handleLoginSuccess(result.user.name, false, result.user.color_hue);
      } else {
        alert("Guest login failed");
      }
    } catch (error) {
      console.error("Guest login error:", error);
    }
  };

  // Color Picker Logic
  // 1. Local UI Updates (Fast & Smooth)
  elements.hueSlider.oninput = (e) => {
    const hue = e.target.value;
    const hexColor = hslToHex(hue, 70, 60);

    // Update UI instantly via CSS Variables
    document.documentElement.style.setProperty('--user-color', hexColor);

    selectedColor = `hsl(${hue}, 70%, 60%)`;
    elements.colorPreview.style.backgroundColor = selectedColor;
    elements.userDisplayName.style.color = selectedColor;

    // Update Button and Tabs
    elements.startBtn.className = "w-full bg-[var(--user-color)] text-white py-4 rounded-2xl font-bold shadow-lg";

    if (mode === "create") {
      elements.createTab.className = "flex-1 py-2.5 rounded-xl font-bold text-sm bg-white shadow text-[var(--user-color)]";
    } else if (mode === "join") {
      elements.joinTab.className = "flex-1 py-2.5 rounded-xl font-bold text-sm bg-white shadow text-[var(--user-color)]";
    }
  };

  // 2. Persistent Backend Update (Saves to DB/Session)
  elements.hueSlider.onchange = async (e) => {
    const hueValue = parseInt(e.target.value);

    console.log(`Syncing hue ${hueValue} to backend...`);

    try {
      const response = await fetch('/auth/color-hue', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        // Matches your FastAPI: color_hue: int = Body(..., embed=True)
        body: JSON.stringify({ color_hue: hueValue })
      });

      if (!response.ok) {
        const error = await response.json();
        console.error("Backend color sync failed:", error.detail);
      } else {
        console.log("Backend color sync success!");
      }
    } catch (err) {
      console.error("Network error during color sync:", err);
    }
  };

  // 2. Persistent Backend Update (Saves to DB/Session)
  elements.hueSlider.onchange = async (e) => {
    const hueValue = parseInt(e.target.value);

    console.log(`Syncing hue ${hueValue} to backend...`);

    try {
      const response = await fetch('/auth/color-hue', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        // Matches your FastAPI: color_hue: int = Body(..., embed=True)
        body: JSON.stringify({ color_hue: hueValue })
      });

      if (!response.ok) {
        const error = await response.json();
        console.error("Backend color sync failed:", error.detail);
      } else {
        console.log("Backend color sync success!");
      }
    } catch (err) {
      console.error("Network error during color sync:", err);
    }
  };

  elements.startBtn.onclick = () => {
    const room = mode === "create" ?
      Math.random().toString(36).substring(2, 6).toUpperCase() :
      elements.roomInput.value.trim().toUpperCase();

    if (mode === "join" && !room) return alert("Enter room code");
    joinGame(room, window.myPlayerName);
  };

  elements.resetCam.onclick = () => {
    camera.x = 20; camera.y = 20; camera.zoom = 40;
    if (window.lastKnownState) renderCanvas(window.lastKnownState);
  };

  if (elements.lobbyLogoutBtn) {
    elements.lobbyLogoutBtn.onclick = handleLogout;
  }
  if (elements.logoutBtn) {
    elements.logoutBtn.onclick = handleLogout;
  }
};

const handleLogout = async () => {
  try {
    const response = await fetch('/auth/logout', { method: 'POST' });
    if (response.ok) {
      location.reload(); // Refresh to clear state and show login screen
    } else {
      console.error("Logout failed");
    }
  } catch (error) {
    console.error("Logout error:", error);
  }
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
        // Pass hue from Google login response
        handleLoginSuccess(result.user.name, true, result.user.color_hue);
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
          use_fedcm_for_prompt: true
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

const handleLoginSuccess = (name, isAuthorized = false, savedHue = 231) => {
  window.myPlayerName = name;
  elements.userDisplayName.innerText = name;
  elements.authOverlay.style.display = 'none';

  // 1. APPLY THE LOADED HUE IMMEDIATELY
  if (elements.hueSlider) {
    elements.hueSlider.value = savedHue;

    // Manually trigger the visual update logic
    const hexColor = hslToHex(savedHue, 70, 60);
    document.documentElement.style.setProperty('--user-color', hexColor);

    selectedColor = `hsl(${savedHue}, 70%, 60%)`;
    elements.colorPreview.style.backgroundColor = selectedColor;
    elements.userDisplayName.style.color = selectedColor;

    elements.startBtn.className = "w-full bg-[var(--user-color)] text-white py-4 rounded-2xl font-bold shadow-lg";

    const activeTabClass = "flex-1 py-2.5 rounded-xl font-bold text-sm bg-white shadow text-[var(--user-color)]";
    if (mode === "create") elements.createTab.className = activeTabClass;
    else elements.joinTab.className = activeTabClass;
  }

  if (isAuthorized && elements.colorPickerContainer) {
    elements.colorPickerContainer.classList.remove("hidden");
  }

  // Animation and Section display
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

    if (data.type === "TILE_REMOVED" && data.coords) {
      import("./RenderCanvas.js").then(module => {
        module.triggerRemovalAnimation(data.coords);
      });
      return;
    }

    if (data.type === "DRAWN_TILES") {
      // Handled by state updates mostly, but can be used for animations later
      return;
    }

    if (!data.state) return;
    if (data.type === "INIT") window.myPlayerId = data.playerId;

    window.lastKnownState = data.state;

    // Sync Rack from Player State
    const myPlayer = data.state.players[window.myPlayerId];
    if (myPlayer && myPlayer.hand) {
      import("./RenderCanvas.js").then(module => {
        module.rackState.tiles = myPlayer.hand;
        module.renderCanvas(data.state);
      });
    } else {
      renderCanvas(data.state);
    }
    updateLeaderboard(data.state.players, window.myPlayerId);
  };
}



init();