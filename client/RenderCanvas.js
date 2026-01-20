import { globalWs } from "./ConnectionManager.js";
const canvas = document.getElementById("game-canvas");

let isDraggingFromRack = false;

export const camera = {
  x: 20, y: 20, zoom: 40,
  isDragging: false, wasDragging: false,
  lastMouseX: 0, lastMouseY: 0,
  mouseX: 0, mouseY: 0
};

export const rackState = {
  tiles: Array(10).fill(null),
  draggingIndex: -1,
  dragX: 0,
  dragY: 0,
  lastTiles: Array(10).fill(null),
  arrivalAnimations: [] // Array of {index, startTime, duration}
};

let removalAnimations = [];

export function triggerRemovalAnimation(tiles) {
  const startTime = performance.now();
  const duration = 800;

  tiles.forEach(tile => {
    removalAnimations.push({
      x: tile.x,
      y: tile.y,
      letter: tile.letter || "?",
      color: tile.color || "#ef4444", // Default to a "error/remove" red
      startTime,
      duration
    });
  });

  // Force an immediate start
  ensureAnimationLoop();
}

let isLoopRunning = false;
export function ensureAnimationLoop() {
  if (isLoopRunning) return;
  isLoopRunning = true;
  animationLoop();
}

function animationLoop() {
  const now = performance.now();

  // Filter out finished animations
  removalAnimations = removalAnimations.filter(anim => now < anim.startTime + anim.duration);
  if (rackState.arrivalAnimations) {
    rackState.arrivalAnimations = rackState.arrivalAnimations.filter(anim => now < anim.startTime + anim.duration);
  }

  // Always render if there are active animations
  if (window.lastKnownState) {
    renderCanvas(window.lastKnownState);
  }

  const hasRemoval = removalAnimations.length > 0;
  const hasArrival = rackState.arrivalAnimations && rackState.arrivalAnimations.length > 0;

  if (hasRemoval || hasArrival) {
    requestAnimationFrame(animationLoop);
  } else {
    isLoopRunning = false;
  }
}

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

  const startX = Math.floor((camera.x - viewW / 2) / cellSize);
  const endX = Math.ceil((camera.x + viewW / 2) / cellSize);
  const startY = Math.floor((camera.y - viewH / 2) / cellSize);
  const endY = Math.ceil((camera.y + viewH / 2) / cellSize);

  render_grid(ctx, startX, endX, startY, endY, cellSize);

  render_pending(ctx, state, startX, endX, startY, endY, cellSize);
  render_textbox(ctx, state, startX, endX, startY, endY, cellSize);

  // --- GHOST PREVIEW (Matches User Color) ---
  const ghost = screenToWorld(camera.mouseX, camera.mouseY, rect);
  // Read the CSS variable we set in ConnectionManager.js
  const userColor = getComputedStyle(document.documentElement).getPropertyValue('--user-color') || '#4f46e5';

  ctx.fillStyle = userColor;
  ctx.globalAlpha = 0.2; // Keep it faint
  ctx.fillRect(ghost.tileX * cellSize + 2, ghost.tileY * cellSize + 2, cellSize - 4, cellSize - 4);
  ctx.globalAlpha = 1.0;

  ctx.restore();

  render_rack(ctx, rect, userColor);
}

function render_rack(ctx, rect, userColor) {
  const tileCount = 10; // Fixed 10 slots
  const tileSize = 60;
  const gap = 12;
  const totalWidth = (tileCount * tileSize) + ((tileCount - 1) * gap);
  const startX = (rect.width - totalWidth) / 2;
  const rackY = rect.height - 100;

  // Draw Rack Background Container
  ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
  ctx.shadowColor = "rgba(0,0,0,0.1)";
  ctx.shadowBlur = 20;
  ctx.beginPath();
  ctx.roundRect(startX - 20, rackY - 20, totalWidth + 40, tileSize + 40, 24);
  ctx.fill();
  ctx.shadowBlur = 0;

  rackState.tiles.forEach((letter, i) => {
    const x = startX + i * (tileSize + gap);

    // Draw slot background (empty slot)
    ctx.fillStyle = "rgba(0, 0, 0, 0.05)";
    ctx.beginPath();
    ctx.roundRect(x, rackY, tileSize, tileSize, 10);
    ctx.fill();

    if (!letter || i === rackState.draggingIndex) return;

    // Arrival animation logic
    const anim = (rackState.arrivalAnimations || []).find(a => a.index === i);
    let scale = 1;
    let opacity = 1;

    if (anim) {
      const elapsed = performance.now() - anim.startTime;
      const progress = Math.min(elapsed / anim.duration, 1);

      // Stronger "Pop" Effect (Overshoot)
      // progress 0-1 matches scale 0-1.2-1.0
      if (progress < 0.7) {
        scale = (progress / 0.7) * 1.2;
      } else {
        scale = 1.2 - ((progress - 0.7) / 0.3) * 0.2;
      }
      opacity = progress;
    }

    ctx.save();
    if (anim) {
      ctx.translate(x + tileSize / 2, rackY + tileSize / 2);
      ctx.scale(scale, scale);
      ctx.globalAlpha = opacity;
      drawTile(ctx, -tileSize / 2, -tileSize / 2, tileSize, letter, false);
    } else {
      drawTile(ctx, x, rackY, tileSize, letter, false);
    }
    ctx.restore();
  });

  // Draw the tile currently being dragged
  if (rackState.draggingIndex !== -1) {
    drawTile(ctx, rackState.dragX - tileSize / 2, rackState.dragY - tileSize / 2, tileSize, rackState.tiles[rackState.draggingIndex], true);
  }
}

function drawTile(ctx, x, y, size, letter, isDragging) {
  const userColor = getComputedStyle(document.documentElement).getPropertyValue('--user-color') || '#4f46e5';

  ctx.save();
  if (isDragging) {
    ctx.shadowColor = "rgba(0,0,0,0.3)";
    ctx.shadowBlur = 15;
    ctx.scale(1.1, 1.1); // Make it pop while dragging
  }

  ctx.fillStyle = userColor; // Use the passed userColor
  ctx.beginPath();
  ctx.roundRect(x, y, size, size, 10);
  ctx.fill();

  ctx.font = `bold ${size * 0.5}px Lexend, sans-serif`;
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(letter, x + size / 2, y + size / 2);

  ctx.restore();
}

function render_grid(ctx, startX, endX, startY, endY, cellSize) {
  for (let x = startX; x <= endX; x++) {
    for (let y = startY; y <= endY; y++) {
      const px = x * cellSize;
      const py = y * cellSize;

      // 1. Subtle Tile Background
      // Using a very slight off-white/gray for a paper-like feel
      ctx.fillStyle = "#f8fafc";

      // Draw rounded background for the grid slot
      ctx.beginPath();
      ctx.roundRect(px + 1.5, py + 1.5, cellSize - 3, cellSize - 3, 6);
      ctx.fill();
    }
  }
}

function render_textbox(ctx, state, startX, endX, startY, endY, cellSize) {
  ctx.font = `bold ${cellSize * 0.5}px Lexend, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  // 1. Render Confirmed Board Tiles
  (state.board || []).forEach(cell => {
    if (cell.x >= startX && cell.x <= endX && cell.y >= startY && cell.y <= endY) {
      const cx = cell.x * cellSize + cellSize / 2;
      const cy = cell.y * cellSize + cellSize / 2;

      // --- DYNAMIC COLOR LOGIC ---
      // Use cell.color (sent from server) or fallback to primary indigo
      const tileColor = cell.color || "#4f46e5";

      // Draw Letter Tile Background
      ctx.fillStyle = tileColor;
      ctx.shadowColor = "rgba(0,0,0,0.1)";
      ctx.shadowBlur = 4;
      ctx.beginPath();
      ctx.roundRect(cell.x * cellSize + 4, cell.y * cellSize + 4, cellSize - 8, cellSize - 8, 6);
      ctx.fill();
      ctx.shadowBlur = 0;

      // Draw Letter Text (White looks best on colored backgrounds)
      ctx.fillStyle = "white";
      ctx.fillText(cell.letter.toUpperCase(), cx, cy);
    }
  });

  // 2. Render Pending Tiles (Optimistic or from Server)
  (state.pending_tiles || []).forEach(cell => {
    if (cell.x >= startX && cell.x <= endX && cell.y >= startY && cell.y <= endY) {
      const cx = cell.x * cellSize + cellSize / 2;
      const cy = cell.y * cellSize + cellSize / 2;

      // Render pending tiles with lower opacity and possibly a dashed border
      const tileColor = cell.color || "#4f46e5";
      ctx.save();
      ctx.globalAlpha = 0.5; // Lower opacity for pending
      ctx.fillStyle = tileColor;
      ctx.beginPath();
      ctx.roundRect(cell.x * cellSize + 4, cell.y * cellSize + 4, cellSize - 8, cellSize - 8, 6);
      ctx.fill();

      ctx.globalAlpha = 1.0;
      ctx.fillStyle = "white";
      ctx.fillText(cell.letter.toUpperCase(), cx, cy);
      ctx.restore();
    }
  });
}

export function render_pending(ctx, state, startX, endX, startY, endY, cellSize) {

  // RenderCanvas.js - inside render_textbox
  (state.pending_tiles || []).forEach(cell => {
    if (cell.x >= startX && cell.x <= endX && cell.y >= startY && cell.y <= endY) {
      const cx = cell.x * cellSize + cellSize / 2;
      const cy = cell.y * cellSize + cellSize / 2;

      const tileColor = cell.color || "#4f46e5";
      ctx.save();

      // Make pending tiles slightly "pulsing" or semi-transparent
      ctx.globalAlpha = 0.2;
      ctx.fillStyle = tileColor;

      ctx.beginPath();
      // Use a slightly different shape (rounded) to distinguish from confirmed tiles
      ctx.roundRect(cell.x * cellSize + 4, cell.y * cellSize + 4, cellSize - 8, cellSize - 8, 8);
      ctx.fill();

      // Add a small border to make it pop since it's transparent
      ctx.strokeStyle = "rgba(255,255,255,0.5)";
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.globalAlpha = 1.0;
      ctx.fillStyle = "white";
      ctx.fillText(cell.letter.toUpperCase(), cx, cy);
      ctx.restore();
    }
  });
  // Inside render_textbox, Section 3: Removal Animations
  removalAnimations.forEach((anim) => {
    const elapsed = performance.now() - anim.startTime;
    const progress = Math.min(elapsed / anim.duration, 1);

    const easeOut = 1 - Math.pow(1 - progress, 3);
    const opacity = 1 - progress;
    const explodeDist = cellSize * 0.8 * easeOut;
    const halfSize = (cellSize - 8) / 2;
    const cx = anim.x * cellSize + cellSize / 2;
    const cy = anim.y * cellSize + cellSize / 2;

    const quadrants = [
      { dx: -1, dy: -1, rot: -0.5 },
      { dx: 1, dy: -1, rot: 0.5 },
      { dx: -1, dy: 1, rot: -0.8 },
      { dx: 1, dy: 1, rot: 0.8 }
    ];

    quadrants.forEach((q) => {
      ctx.save();
      ctx.globalAlpha = opacity;
      ctx.translate(cx + q.dx * explodeDist, cy + q.dy * explodeDist);
      ctx.rotate(q.rot * easeOut);

      ctx.fillStyle = anim.color;
      ctx.beginPath();
      // Draw the shard
      ctx.roundRect(
        q.dx < 0 ? -halfSize : 0,
        q.dy < 0 ? -halfSize : 0,
        halfSize - 1,
        halfSize - 1,
        2
      );
      ctx.fill();

      // Draw fragment of the letter
      ctx.fillStyle = "white";
      ctx.font = `bold ${cellSize * 0.4}px Lexend, sans-serif`;
      ctx.fillText(anim.letter, 0, 0);
      ctx.restore(); // Restore per quadrant
    });
  });

}
export function screenToWorld(screenX, screenY, rect) {
  let x = (screenX - rect.width / 2) * (40 / camera.zoom) + camera.x;
  let y = (screenY - rect.height / 2) * (40 / camera.zoom) + camera.y;
  return {
    tileX: Math.floor(x / 40),
    tileY: Math.floor(y / 40)
  };
}

// ... (Mouse listeners remain the same)
// Update mouse position for the ghost letter
canvas.addEventListener('mousemove', (e) => {
  const rect = canvas.getBoundingClientRect();
  camera.mouseX = e.clientX - rect.left;
  camera.mouseY = e.clientY - rect.top;

  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;
  if (isDraggingFromRack) {
    rackState.dragX = mouseX;
    rackState.dragY = mouseY;
    renderCanvas(window.lastKnownState);
  }
  else if (camera.isDragging) {
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
  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  // Check if clicking a tile in the rack
  const tileCount = rackState.tiles.length;
  const tileSize = 60;
  const gap = 12;
  const totalWidth = (tileCount * tileSize) + ((tileCount - 1) * gap);
  const startX = (rect.width - totalWidth) / 2;
  const rackY = rect.height - 100;

  rackState.tiles.forEach((letter, i) => {
    if (!letter) return; // Can't drag empty slot
    const x = startX + i * (tileSize + gap);
    if (mouseX >= x && mouseX <= x + tileSize && mouseY >= rackY && mouseY <= rackY + tileSize) {
      rackState.draggingIndex = i;
      isDraggingFromRack = true;
    }
  });

  // If not rack, handle camera drag
  if (!isDraggingFromRack) {
    camera.isDragging = true;
    camera.wasDragging = false;
    camera.lastMouseX = e.clientX;
    camera.lastMouseY = e.clientY;
  }
});

window.addEventListener('mouseup', (e) => {
  if (isDraggingFromRack) {
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Convert release point to world coordinates
    const worldPos = screenToWorld(mouseX, mouseY, rect);
    const letter = rackState.tiles[rackState.draggingIndex];

    // Send to Server
    if (globalWs?.readyState === WebSocket.OPEN) {
      globalWs.send(JSON.stringify({
        type: "PLACE",
        x: worldPos.tileX,
        y: worldPos.tileY,
        letter: letter.toUpperCase(),
        color: getComputedStyle(document.documentElement).getPropertyValue('--user-color') || '#4f46e5',
        hand_index: rackState.draggingIndex
      }));
    }

    // Reset state
    rackState.draggingIndex = -1;
    isDraggingFromRack = false;
    renderCanvas(window.lastKnownState);
  }
  camera.isDragging = false;
});

canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  const delta = e.deltaY > 0 ? 0.9 : 1.1;
  camera.zoom = Math.min(Math.max(camera.zoom * delta, 15), 200);
  renderCanvas(window.lastKnownState || { board: [] });
}, { passive: false });
