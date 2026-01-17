import { renderCanvas, screenToWorld, camera } from "./RenderCanvas.js";
import { updateLeaderboard } from "./UIManager.js";

const startScreen = document.getElementById("start-screen");
const gameScreen = document.getElementById("game-ui");

const nameInput = document.getElementById("nameInput");
const roomInput = document.getElementById("roomInput");
const startBtn = document.getElementById("startBtn");

const createTab = document.getElementById("createTab");
const joinTab = document.getElementById("joinTab");
const joinBox = document.getElementById("joinBox");
const canvas = document.getElementById("game-canvas");

let mode = "create";

let globalWs; // Store the connection here

// Toggle UI
createTab.onclick = () => {
  mode = "create";
  createTab.classList.add("active");
  joinTab.classList.remove("active");
  joinBox.classList.add("hidden");
  startBtn.textContent = "＋ Create New Room";
};

joinTab.onclick = () => {
  mode = "join";
  joinTab.classList.add("active");
  createTab.classList.remove("active");
  joinBox.classList.remove("hidden");
  startBtn.textContent = "→ Join Room";
};

// Auto-join if URL has room
const params = new URLSearchParams(location.search);
if (params.get("room")) {
  joinGame(params.get("room"), params.get("name") || "Guest");
}

const triggerError = () => {
  const errorClasses = ["bg-red-500", "animate-shake", "shadow-red-200"];
  const originalClasses = ["bg-primary", "shadow-indigo-200"];

  startBtn.classList.remove(...errorClasses);
  startBtn.classList.add(...originalClasses);
  
  void startBtn.offsetWidth; 

  startBtn.classList.remove(...originalClasses);
  startBtn.classList.add(...errorClasses);

  setTimeout(() => {
    startBtn.classList.remove(...errorClasses);
    startBtn.classList.add(...originalClasses);
  }, 500);
};

// Start button
startBtn.onclick = () => {
  const name = nameInput.value.trim();

  // Validation
  if (!name) {
    triggerError();
    nameInput.focus();
    return;
  }

  let room;
  if (mode === "create") {
    room = Math.random().toString(36).substring(2, 6).toUpperCase();
  } else {
    room = roomInput.value.trim().toUpperCase();
  }
  if (!room) return alert("Enter room code");

  location.href = `/?room=${room}&name=${encodeURIComponent(name)}`;
};

document.getElementById('reset-cam').addEventListener('click', () => {
  camera.x = 0;
  camera.y = 0;
  camera.zoom = 40; // Default zoom level
  
  // Re-render to show changes
  renderCanvas(window.lastKnownState || { board: [] });
});

function joinGame(room, name) {
  let myPlayerId = null;
  startScreen.classList.add("hidden");
  gameScreen.classList.remove("hidden");

  const protocol = location.protocol === "https:" ? "wss" : "ws";
  globalWs = new WebSocket(
    `${protocol}://${location.host}/ws?room=${room}&name=${name}`
    );

  globalWs.onmessage = (e) => {
    
    const data = JSON.parse(e.data);
    // console.log(data);
    if (!data.state) return; 

    if (data.type === "INIT") {
      window.myPlayerId = data.playerId; 
      // console.log("Logged in as:", window.myPlayerId);
      myPlayerId = data.playerId;
    }

    window.lastKnownState = data.state;
    renderCanvas(window.lastKnownState);
    updateLeaderboard(window.lastKnownState.players, myPlayerId);
  };
}

canvas.addEventListener('click', (e) => {
  if (camera.wasDragging) return;

  // 1. Get tile coordinates
  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;
  const worldPos = screenToWorld(mouseX, mouseY, rect);

  // 2. Ask user for a letter
  const char = prompt("Enter a letter:");
  
  if (char && char.length === 1 && globalWs && globalWs.readyState === WebSocket.OPEN) {
    // 3. CONSTRUCT THE MESSAGE
    const message = {
      type: "PLACE",
      x: worldPos.tileX,
      y: worldPos.tileY,
      letter: char.toUpperCase()
    };

    // 4. SEND TO SERVER
    globalWs.send(JSON.stringify(message));
  }
});