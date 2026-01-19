const canvas = document.getElementById("game-canvas");

export const camera = {
  x: 20, y: 20, zoom: 40,
  isDragging: false, wasDragging: false,
  lastMouseX: 0, lastMouseY: 0,
  mouseX: 0, mouseY: 0 // Track mouse for the ghost letter
};

export function renderCanvas(state) {
  if (!canvas || !state) return;
  const ctx = canvas.getContext("2d");
  const parent = canvas.parentElement;
  const dpr = window.devicePixelRatio || 1;
  const rect = parent.getBoundingClientRect();

  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  // Background
  ctx.fillStyle = "#f1f5f9";
  ctx.fillRect(0, 0, rect.width, rect.height);

  ctx.save();
  ctx.translate(rect.width / 2, rect.height / 2);
  ctx.scale(camera.zoom / 40, camera.zoom / 40);
  ctx.translate(-camera.x, -camera.y);

  const cellSize = 40;
  const viewW = rect.width * (40 / camera.zoom);
  const viewH = rect.height * (40 / camera.zoom);

  // Calculate grid bounds (works for negative values)
  const startX = Math.floor((camera.x - viewW / 2) / cellSize);
  const endX = Math.ceil((camera.x + viewW / 2) / cellSize);
  const startY = Math.floor((camera.y - viewH / 2) / cellSize);
  const endY = Math.ceil((camera.y + viewH / 2) / cellSize);

  render_grid(ctx, startX, endX, startY, endY, cellSize);
  render_textbox(ctx, state, startX, endX, startY, endY, cellSize);

  // --- GHOST PREVIEW ---
  const ghost = screenToWorld(camera.mouseX, camera.mouseY, rect);
  ctx.fillStyle = "rgba(79, 70, 229, 0.1)";
  ctx.fillRect(ghost.tileX * cellSize, ghost.tileY * cellSize, cellSize, cellSize);

  ctx.restore();
}

function render_grid(ctx, startX, endX, startY, endY, cellSize) {
  for (let x = startX; x <= endX; x++) {
    for (let y = startY; y <= endY; y++) {
      const px = x * cellSize;
      const py = y * cellSize;

      // 1. Draw Tile Background
      ctx.fillStyle = "white";
      ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2);

      // 2. Draw Tile Border
      // Highlight the Axes (0,y and x,0) with a slightly darker color
      ctx.strokeStyle = "#e2e8f0";
      ctx.lineWidth = 1
      ctx.strokeRect(px, py, cellSize, cellSize);
    }
  }
}

function render_textbox(ctx, state, startX, endX, startY, endY, cellSize) {
  ctx.font = `bold ${cellSize * 0.5}px Lexend, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  (state.board || []).forEach(cell => {
    // Basic culling: only draw if in view
    if (cell.x >= startX && cell.x <= endX && cell.y >= startY && cell.y <= endY) {
      const cx = cell.x * cellSize + cellSize / 2;
      const cy = cell.y * cellSize + cellSize / 2;

      // Draw Letter Tile
      ctx.fillStyle = "#928dfa";
      ctx.shadowColor = "rgba(0,0,0,0.15)";
      ctx.shadowBlur = 5;
      ctx.fillRect(cell.x * cellSize + 4, cell.y * cellSize + 4, cellSize - 8, cellSize - 8);
      ctx.shadowBlur = 0;

      ctx.fillStyle = "#4f46e5";
      ctx.fillText(cell.letter.toUpperCase(), cx, cy);
    }
  });
}

// Helper to convert screen pixels to tile coordinates
export function screenToWorld(screenX, screenY, rect) {
  let x = (screenX - rect.width / 2) * (40 / camera.zoom) + camera.x;
  let y = (screenY - rect.height / 2) * (40 / camera.zoom) + camera.y;
  return {
    tileX: Math.floor(x / 40),
    tileY: Math.floor(y / 40)
  };
}


// Update mouse position for the ghost letter
canvas.addEventListener('mousemove', (e) => {
  const rect = canvas.getBoundingClientRect();
  camera.mouseX = e.clientX - rect.left;
  camera.mouseY = e.clientY - rect.top;

  if (camera.isDragging) {
    camera.wasDragging = true;
    const factor = 40 / camera.zoom;
    camera.x -= (e.clientX - camera.lastMouseX) * factor;
    camera.y -= (e.clientY - camera.lastMouseY) * factor;
    camera.lastMouseX = e.clientX;
    camera.lastMouseY = e.clientY;
  }

  // Re-render every time the mouse moves (to update drag or ghost letter)
  renderCanvas(window.lastKnownState || { board: [] });
});

canvas.addEventListener('mousedown', (e) => {
  camera.isDragging = true;
  camera.wasDragging = false;
  camera.lastMouseX = e.clientX;
  camera.lastMouseY = e.clientY;
});

window.addEventListener('mouseup', () => {
  camera.isDragging = false;
});

canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  const delta = e.deltaY > 0 ? 0.9 : 1.1;
  camera.zoom = Math.min(Math.max(camera.zoom * delta, 15), 200);
  renderCanvas(window.lastKnownState || { board: [] });
}, { passive: false });
