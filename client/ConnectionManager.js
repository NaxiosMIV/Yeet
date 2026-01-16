import { renderCanvas } from "./RenderCanvas.js";

const startScreen = document.getElementById("start-screen");
const gameScreen = document.getElementById("game-ui");

const nameInput = document.getElementById("nameInput");
const roomInput = document.getElementById("roomInput");
const startBtn = document.getElementById("startBtn");

const createTab = document.getElementById("createTab");
const joinTab = document.getElementById("joinTab");
const joinBox = document.getElementById("joinBox");

let mode = "create";

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

// Start button
startBtn.onclick = () => {
  const name = nameInput.value.trim();
  if (!name) return alert("Enter your name");

  let room;
  if (mode === "create") {
    room = Math.random().toString(36).substring(2, 6).toUpperCase();
  } else {
    room = roomInput.value.trim().toUpperCase();
    if (!room) return alert("Enter room code");
  }

  location.href = `/?room=${room}&name=${encodeURIComponent(name)}`;
};

function joinGame(room, name) {
  startScreen.classList.add("hidden");
  gameScreen.classList.remove("hidden");

  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(
    `${protocol}://${location.host}/ws?room=${room}&name=${name}`
  );

  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    console.log(data);
    if (!data.state) return; // safety check
    const state = data.state;

    const boardData = state.board; // array of {x, y, letter}
    const boardSize = 15; // or calculate dynamically if needed
    
    renderCanvas(boardData, 15);
  };
}
