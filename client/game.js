// 1. Read room from URL
function getRoom() {
  const params = new URLSearchParams(location.search);
  return params.get("room") || "TEST";
}

const room = getRoom();
document.getElementById("room").textContent = room;

// 2. Connect WebSocket
const protocol = location.protocol === "https:" ? "wss" : "ws";
const ws = new WebSocket(
  `${protocol}://${location.host}/ws?room=${room}`
);

// 3. Handle messages
ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  document.getElementById("state").textContent =
    JSON.stringify(data, null, 2);
};

ws.onopen = () => {
  console.log("Connected to room", room);
};

ws.onerror = (e) => {
  console.error("WebSocket error", e);
};
