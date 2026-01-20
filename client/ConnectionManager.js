import { renderCanvas, screenToWorld, camera, rackState, render_pending } from "./RenderCanvas.js";
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
  lobbyLogoutBtn: document.getElementById("lobbyLogoutBtn"),
  lobbyWaitMsg: document.getElementById("lobby-wait-msg"),
  lobbyStartBtn: document.getElementById("lobby-start-match-btn"),
  lobbyPlayerList: document.getElementById("lobby-player-list"),
  lobbyScreen: document.getElementById("lobby-screen"),
  // Chat Elements
  chatWidget: document.getElementById("chat-widget"),
  chatToggle: document.getElementById("chat-toggle"),
  chatContainer: document.getElementById("chat-container"),
  chatClose: document.getElementById("close-chat"),
  chatInput: document.getElementById("chat-input"),
  chatSend: document.getElementById("chat-send"),
  chatMessages: document.getElementById("chat-messages"),
  chatIcon: document.getElementById("chat-icon"),
  playerNickNameDisplay: document.getElementById("header-user-name"),
};

function updateLobbyUI(state) {
  elements.lobbyPlayerList.innerHTML = "";

  const playerIds = Object.keys(state.players);

  const isHost = playerIds[0] === window.myPlayerId;

  // Elements for toggling
  const modeSelect = document.getElementById("lobby-settings-mode");
  const modeText = document.getElementById("lobby-mode-text");
  const langSelect = document.getElementById("lobby-settings-lang");
  const langText = document.getElementById("lobby-lang-text");

  if (isHost) {
    // HOST VIEW: Show the interactive dropdown and start button
    elements.lobbyStartBtn.classList.remove("hidden");
    elements.lobbyWaitMsg.classList.add("hidden");

    modeSelect.classList.remove("hidden");
    modeText.classList.add("hidden");

    langSelect.classList.remove("hidden");
    langText.classList.add("hidden");
  } else {
    // GUEST VIEW: Show read-only text and waiting message
    elements.lobbyStartBtn.classList.add("hidden");
    elements.lobbyWaitMsg.classList.remove("hidden");

    modeSelect.classList.add("hidden");
    modeText.classList.remove("hidden");

    // Sync the text with whatever the host has currently selected (from state)
    const currentMode = state.settings?.mode || 'classic';
    modeText.innerText = currentMode.charAt(0).toUpperCase() + currentMode.slice(1);

    langSelect.classList.add("hidden");
    langText.classList.remove("hidden");

    const currentLang = state.settings?.lang || 'en';
    langText.innerText = currentLang === 'ko' ? '한국어' : 'English';
  }

  // Render player list...
  playerIds.forEach(id => {
    const p = state.players[id];
    const isThisPlayerHost = id === playerIds[0];
    const item = document.createElement("div");
    item.className = "flex items-center justify-between p-4 bg-slate-50 rounded-2xl border border-slate-100 transition-all";
    item.innerHTML = `
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl border-2 border-white shadow-sm" style="background-color: ${p.color || '#6366F1'}"></div>
                <div class="flex flex-col">
                    <span class="font-bold text-slate-700 text-sm">${p.name} ${id === window.myPlayerId ? '<span class="text-[10px] text-indigo-400 font-medium ml-1">(You)</span>' : ''}</span>
                    <span class="text-[10px] text-slate-400 font-bold uppercase tracking-tighter">${isThisPlayerHost ? 'Room Leader' : 'Player'}</span>
                </div>
            </div>
            ${isThisPlayerHost ? '<span class="material-icons-round text-amber-400 text-sm">stars</span>' : ''}
        `;
    elements.lobbyPlayerList.appendChild(item);
  });
}

// Event listener for the actual match start
elements.lobbyStartBtn.onclick = () => {
  if (globalWs && globalWs.readyState === WebSocket.OPEN) {
    globalWs.send(JSON.stringify({
      type: "START_GAME",
      settings: { mode: document.getElementById("lobby-settings-mode").value }
    }));
  } else {
    console.error("Cannot start game: WebSocket is not connected.");
    alert("Connection lost. Please refresh the page.");
  }
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

document.getElementById("lobby-settings-mode").onchange = (e) => {
  // Send a message to the server to update the room settings
  if (globalWs?.readyState === WebSocket.OPEN) {
    globalWs.send(JSON.stringify({
      type: "UPDATE_SETTINGS",
      settings: { mode: e.target.value }
    }));
  }
};

document.getElementById("lobby-settings-lang").onchange = (e) => {
  // Send language change to server
  if (globalWs?.readyState === WebSocket.OPEN) {
    globalWs.send(JSON.stringify({
      type: "UPDATE_SETTINGS",
      settings: { lang: e.target.value }
    }));
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

  // Chat Event Listeners
  const toggleChat = () => {
    const isExpanded = elements.chatContainer.classList.toggle("expanded");
    elements.chatIcon.innerText = isExpanded ? "keyboard_arrow_down" : "chat";
    if (isExpanded) {
      elements.chatInput.focus();
      elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    }
  };

  elements.chatToggle.onclick = toggleChat;
  elements.chatClose.onclick = toggleChat;

  const sendMessage = () => {
    const msg = elements.chatInput.value.trim();
    if (msg && globalWs?.readyState === WebSocket.OPEN) {
      globalWs.send(JSON.stringify({ type: "CHAT", message: msg }));
      elements.chatInput.value = "";
    }
  };

  elements.chatSend.onclick = sendMessage;
  elements.chatInput.onkeypress = (e) => {
    if (e.key === "Enter") sendMessage();
  };
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
  elements.playerNickNameDisplay.innerText = name;

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
  if (globalWs) {
    globalWs.close();
  }
  elements.startScreen.classList.add("hidden");
  elements.lobbyScreen.classList.remove("hidden"); // Show Lobby instead of Game UI
  document.getElementById("lobby-room-code").innerText = room;
  elements.gameUI.classList.remove("hidden");
  document.getElementById("room-id-text").innerText = room;

  const protocol = location.protocol === "https:" ? "wss" : "ws";
  // Added 'color' parameter to the WebSocket handshake
  const colorParam = encodeURIComponent(selectedColor);
  globalWs = new WebSocket(`${protocol}://${location.host}/ws?room=${room}&name=${name}&color=${colorParam}`);

  globalWs.onmessage = (e) => {
    const data = JSON.parse(e.data);

    if (data.type === "GAME_STARTED") {

      document.getElementById('round-timer-container').classList.remove('hidden');
      elements.lobbyScreen.classList.add("hidden");
      elements.gameUI.classList.remove("hidden");
      return;
    }

    // 2. Update Lobby Player List
    if (data.type === "UPDATE" || data.type === "INIT") {
      updateLobbyUI(data.state);
    }

    if (data.type === "DRAWN_TILES") {
      renderCanvas(data.state);
      return;
    }
    if (data.type === "TIMER") {
      updateInGameTimer(data.time);
    }

    if (data.type === "GAME_START_COUNTDOWN") {
      // Example trigger countdown UI
      startStartGameCountdown(data.seconds);
    }

    if (data.type === "CHAT") {
      appendChatMessage(data.sender, data.message, data.senderId === window.myPlayerId);
      return;
    }

    if (data.type === "GAME_OVER") {
      handleGameOver(data);
      return;
    }

    if (data.type === "TILE_REMOVED") {
      // TILE_REMOVED only contains tiles to remove, not full state
      // Don't overwrite lastKnownState here - UPDATE message will provide the correct state
      import("./RenderCanvas.js").then(m => {
        m.triggerRemovalAnimation(data.tiles);
      });
      return; // Don't process further - wait for UPDATE with correct state
    }

    if (data.type === "UPDATE") {
      window.lastKnownState = data;
    }

    if (!data.state) return;
    if (data.type === "INIT") window.myPlayerId = data.playerId;
    const currentState = data.state || data;
    if (currentState && currentState.players) {
      window.lastKnownState = currentState;

      // Update Lobby or Leaderboard
      updateLobbyUI(currentState);
      updateLeaderboard(currentState.players, window.myPlayerId);

      // Sync Rack/Hand
      const myPlayer = currentState.players[window.myPlayerId];
      if (myPlayer && myPlayer.hand) {
        // Detect additions for animation
        myPlayer.hand.forEach((newLetter, idx) => {
          if (newLetter && !rackState.tiles[idx]) {
            // New tile arrived in this empty slot
            rackState.arrivalAnimations.push({
              index: idx,
              startTime: performance.now(),
              duration: 800 // Snappy visible pop
            });
          }
        });

        rackState.tiles = [...myPlayer.hand];
        // Ensure animation loop is running if animations exist
        if (rackState.arrivalAnimations.length > 0) {
          import("./RenderCanvas.js").then(m => {
            m.ensureAnimationLoop();
          });
        }
      }
    }

    // 4. Trigger Rendering for standard updates
    renderCanvas(window.lastKnownState);
  };

  globalWs.onclose = () => {
    console.warn("WebSocket disconnected");
    elements.lobbyStartBtn.disabled = true;
    window.isGameActive = false;
  };
}

function handleGameOver(data) {
  const overlay = document.getElementById('winner-overlay');
  const winnerName = document.getElementById('winner-name');
  const winnerScore = document.getElementById('winner-score');
  const card = document.getElementById('winner-card');
  const countdownDisplay = document.getElementById('return-countdown');

  // 1. Find the winner from the final state
  const players = Object.values(data.state.players);
  const winner = players.reduce((prev, current) => (prev.score > current.score) ? prev : current);

  winnerName.innerText = winner.name;
  winnerName.style.color = winner.color;
  winnerScore.innerText = `${winner.score} pts`;

  // 2. Show UI with animations
  overlay.classList.remove('hidden');
  setTimeout(() => {
    overlay.classList.add('opacity-100');
    card.classList.add('scale-100');
  }, 50);

  // 3. Fire Confetti Cannon!
  const duration = 5 * 1000;
  const animationEnd = Date.now() + duration;
  const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 400 };

  const randomInRange = (min, max) => Math.random() * (max - min) + min;

  const interval = setInterval(function () {
    const timeLeft = animationEnd - Date.now();
    if (timeLeft <= 0) return clearInterval(interval);

    const particleCount = 50 * (timeLeft / duration);
    confetti({ ...defaults, particleCount, origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 } });
    confetti({ ...defaults, particleCount, origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 } });
  }, 250);

  // 4. Handle Return Countdown
  let timeLeft = 5;
  const countInterval = setInterval(() => {
    timeLeft--;
    countdownDisplay.innerText = timeLeft;
    if (timeLeft <= 0) {
      clearInterval(countInterval);
      // Return to Lobby
      overlay.classList.add('opacity-0');
      setTimeout(() => {
        overlay.classList.add('hidden');
        document.getElementById('game-ui').classList.add('hidden');
        document.getElementById('lobby-screen').classList.remove('hidden');
        // Reset state for next game
        location.reload(); // Simplest way to clear board/memory
      }, 700);
    }
  }, 1000);
}

function appendChatMessage(sender, message, isMine) {
  const msgWrapper = document.createElement("div");
  msgWrapper.className = "flex flex-col";
  msgWrapper.style.alignItems = isMine ? "flex-end" : "flex-start";

  if (!isMine) {
    const senderDiv = document.createElement("div");
    senderDiv.className = "chat-sender";
    senderDiv.innerText = sender;
    msgWrapper.appendChild(senderDiv);
  }

  const msgDiv = document.createElement("div");
  msgDiv.className = `chat-message ${isMine ? "mine" : "other"}`;
  msgDiv.innerText = message;

  msgWrapper.appendChild(msgDiv);
  elements.chatMessages.appendChild(msgWrapper);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;

  // Visual feedback if chat is collapsed
  if (!elements.chatContainer.classList.contains("expanded")) {
    elements.chatToggle.classList.add("bg-red-500");
    elements.chatToggle.classList.remove("bg-indigo-500");
    setTimeout(() => {
      elements.chatToggle.classList.remove("bg-red-500");
      elements.chatToggle.classList.add("bg-indigo-500");
    }, 1000);
  }
}


function startStartGameCountdown(seconds, callback) {
  const overlay = document.getElementById('start-countdown-overlay');
  const display = document.getElementById('countdown-number');

  // Ensure overlay is visible and opaque using Tailwind classes
  overlay.classList.remove('hidden', 'opacity-0');
  overlay.classList.add('flex', 'opacity-100');

  let count = seconds;

  const triggerWobble = (text) => {
    display.innerText = text;
    // Restart Tailwind animation
    display.classList.remove('animate-wobble-pop');
    void display.offsetWidth; // Force browser reflow
    display.classList.add('animate-wobble-pop');
  };

  triggerWobble(count);

  const interval = setInterval(() => {
    count--;
    if (count > 0) {
      triggerWobble(count);
    } else {
      clearInterval(interval);
      triggerWobble("GO!");

      // Wait for "GO!" to be seen, then fade out
      setTimeout(() => {
        overlay.classList.add('duration-500', 'opacity-0');
        setTimeout(() => {
          overlay.classList.add('hidden');
          overlay.classList.remove('flex', 'opacity-0', 'duration-500');
          if (callback) callback();
        }, 500);
      }, 800);
    }
  }, 1000);
}

function updateInGameTimer(secondsRemaining) {
  const container = document.getElementById('round-timer-container');
  const display = document.getElementById('game-timer-display');

  // 1. Show/Hide logic
  if (secondsRemaining <= 0) {
    container.classList.add('hidden');
    return;
  }
  container.classList.remove('hidden');

  // 2. Format the numbers
  const mins = Math.floor(secondsRemaining / 60);
  const secs = secondsRemaining % 60;
  display.innerText = `${mins}:${secs.toString().padStart(2, '0')}`;

  // 4. Dynamic Styling (The "Warning" State)
  if (secondsRemaining <= 10) {
    display.classList.add('text-red-600', 'scale-110');
    // Optional: Trigger a small shake every second when low
    container.classList.add('animate-bounce');
  } else {
    display.classList.remove('text-red-600', 'scale-110');
    container.classList.remove('animate-bounce');
  }
}

init();