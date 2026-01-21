import { globalWs } from "./ConnectionManager.js";
const canvas = document.getElementById("game-canvas");

let isDraggingFromRack = false;
let isMouseOverRack = false;

export const camera = {
  x: 20, y: 20, zoom: 40,
  isDragging: false, wasDragging: false,
  lastMouseX: 0, lastMouseY: 0,
  mouseX: 0, mouseY: 0
};

export const rackState = {
  tiles: Array(10).fill(null),
  draggingIndex: -1,
  hoveredIndex: -1,
  hoverOffsets: Array(10).fill(0), // Visual vertical offset for each tile
  dragX: 0,
  dragY: 0,
  dragOffsetX: 0,
  dragOffsetY: 0,
  lastTiles: Array(10).fill(null),
  arrivalAnimations: [], // Array of {index, startTime, duration}
  isHoveringDestroy: false,
  cooldownDuration: 3000,
  fullArrivalPending: false
};

let removalAnimations = [];
let jumpAnimations = [];
let trashAnimations = [];

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
      duration,
      // Fix: Copy screen space properties
      screenX: tile.screenX,
      screenY: tile.screenY,
      isScreenSpace: tile.isScreenSpace
    });
  });

  // Force an immediate start
  ensureAnimationLoop();
}

export function triggerTrashAnimation(tile) {
  trashAnimations.push({
    letter: tile.letter,
    color: tile.color || '#4f46e5',
    screenX: tile.screenX,
    screenY: tile.screenY,
    startTime: performance.now(),
    duration: 500,
    startAngle: Math.random() * Math.PI * 2
  });
  ensureAnimationLoop();
}

export function triggerWaveAnimation(tiles) {
  // Sort tiles by X coordinate (left to right) for wave effect
  const sorted = [...tiles].sort((a, b) => a.x - b.x);

  sorted.forEach((tile, index) => {
    // Add jump animation with delay based on index
    jumpAnimations.push({
      x: tile.x,
      y: tile.y,
      startTime: performance.now() + index * 100, // 100ms staggered delay
      duration: 400
    });
  });
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
  jumpAnimations = jumpAnimations.filter(anim => now < anim.startTime + anim.duration + 50);
  trashAnimations = trashAnimations.filter(anim => now < anim.startTime + anim.duration);

  if (rackState.arrivalAnimations) {
    rackState.arrivalAnimations = rackState.arrivalAnimations.filter(anim => now < anim.startTime + anim.duration);
  }

  // Handle Hover Animation Interpolation
  let needsMoreFrames = false;
  rackState.hoverOffsets = rackState.hoverOffsets.map((offset, i) => {
    const target = (i === rackState.hoveredIndex && rackState.draggingIndex === -1) ? -12 : 0;
    const diff = target - offset;
    if (Math.abs(diff) < 0.1) return target;
    needsMoreFrames = true;
    return offset + diff * 0.2; // Smooth damping
  });

  // Always render if there are active animations
  if (window.lastKnownState) {
    renderCanvas(window.lastKnownState);
  }

  const hasRemoval = removalAnimations.length > 0;
  const hasArrival = rackState.arrivalAnimations && rackState.arrivalAnimations.length > 0;
  const hasJump = jumpAnimations.length > 0;
  const hasTrash = trashAnimations.length > 0;

  if (hasRemoval || hasArrival || hasJump || hasTrash || needsMoreFrames) {
    requestAnimationFrame(animationLoop);
  } else {
    isLoopRunning = false;
  }
}

export function renderCanvas(state) {
  if (!canvas || !state) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;

  // Use parent for sizing, but canvas rect for coordinates
  const parent = canvas.parentElement;
  const parentRect = parent.getBoundingClientRect();

  // Set canvas internal resolution (for high-DPI rendering)
  canvas.width = parentRect.width * dpr;
  canvas.height = parentRect.height * dpr;

  // CRITICAL: Set explicit CSS size to match parent dimensions
  canvas.style.width = parentRect.width + 'px';
  canvas.style.height = parentRect.height + 'px';

  // Now get the actual canvas rect (should match parent after sizing)
  const rect = canvas.getBoundingClientRect();

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

  render_pending(ctx, state, startX, endX, startY, endY, cellSize, rect);
  render_textbox(ctx, state, startX, endX, startY, endY, cellSize);

  // Read the CSS variable we set in ConnectionManager.js
  const userColor = getComputedStyle(document.documentElement).getPropertyValue('--user-color') || '#4f46e5';

  // --- GHOST PREVIEW (Matches User Color) ---
  // Only show ghost preview when NOT hovering over rack
  if (!isMouseOverRack) {
    const ghost = screenToWorld(camera.mouseX, camera.mouseY, rect);

    ctx.fillStyle = userColor;
    ctx.globalAlpha = 0.2; // Keep it faint

    ctx.beginPath();
    // Using 4px padding and 6px radius to match confirmed tiles
    ctx.roundRect(ghost.tileX * cellSize + 4, ghost.tileY * cellSize + 4, cellSize - 8, cellSize - 8, 6);
    ctx.fill();

    ctx.globalAlpha = 1.0;
  }

  ctx.restore();

  render_rack(ctx, rect, userColor);
  render_trash_anim(ctx); // Render trash animations on top of rack
}

function render_trash_anim(ctx) {
  trashAnimations.forEach(anim => {
    const elapsed = performance.now() - anim.startTime;
    const progress = Math.min(elapsed / anim.duration, 1);

    // Ease In Back (anticipation) then suck in
    const ease = progress < 0.5
      ? 2 * progress * progress
      : 1 - Math.pow(-2 * progress + 2, 2) / 2;

    const scale = 1 - ease;
    const opacity = 1 - progress;
    const rotation = anim.startAngle + progress * Math.PI * 4; // Spin 2 times

    ctx.save();
    ctx.translate(anim.screenX, anim.screenY);
    ctx.rotate(rotation);
    ctx.scale(scale, scale);

    // Draw Tile
    const size = 60; // Same as rack tile
    ctx.fillStyle = anim.color;
    ctx.beginPath();
    ctx.roundRect(-size / 2, -size / 2, size, size, 10);
    ctx.fill();

    ctx.fillStyle = "white";
    ctx.font = `bold ${size * 0.5}px Lexend, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(anim.letter, 0, 0);

    ctx.restore();
  });
}
function render_rack(ctx, rect, userColor) {
  const tileCount = 10;
  const tileSize = 60;
  const gap = 12;
  const totalWidth = (tileCount * tileSize) + ((tileCount - 1) * gap);
  const startX = (rect.width - totalWidth) / 2;
  const rackY = rect.height - 100;

  // --- BUTTON POSITIONS ---
  const buttonsX = startX + totalWidth + 50; // Offset slightly to the right
  const destroyY = rackY + 15;
  const rerollY = rackY + 65;

  // 1. Draw Extended Rack Background
  ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
  ctx.shadowColor = "rgba(0,0,0,0.1)";
  ctx.shadowBlur = 20;
  ctx.beginPath();
  // Width extended to house repositioned buttons
  ctx.roundRect(startX - 20, rackY - 20, totalWidth + 110, tileSize + 70, 24);
  ctx.fill();
  ctx.shadowBlur = 0;

  // 2. Render Slots & Tiles
  rackState.tiles.forEach((letter, i) => {
    const x = startX + i * (tileSize + gap);
    ctx.fillStyle = "rgba(0, 0, 0, 0.05)";
    ctx.beginPath();
    ctx.roundRect(x, rackY, tileSize, tileSize, 10);
    ctx.fill();

    if (!letter || i === rackState.draggingIndex) return;

    const yOffset = rackState.hoverOffsets[i] || 0;

    // --- Appearance Animation ---
    const anim = (rackState.arrivalAnimations || []).find(a => a.index === i);
    let scale = 1;
    if (anim) {
      const elapsed = performance.now() - anim.startTime;
      const progress = Math.min(elapsed / anim.duration, 1);

      if (progress < 0) {
        scale = 0;
      } else {
        // Snappy Elastic ease out
        const c4 = (2 * Math.PI) / 3;
        scale = progress === 0 ? 0 : progress === 1 ? 1 :
          Math.pow(2, -10 * progress) * Math.sin((progress * 10 - 0.75) * c4) + 1;
      }
    }

    drawTile(ctx, x, rackY + yOffset, tileSize, letter, false, scale);
  });

  // 3. Draw DESTROY Button (Trash)
  ctx.save();
  // Fixed color as requested (no hover effect)
  ctx.fillStyle = "#fee2e2";
  ctx.beginPath();
  ctx.arc(buttonsX, destroyY, 18, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "#ef4444";
  ctx.font = "18px 'Material Icons Round'";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("delete", buttonsX, destroyY);
  ctx.restore();

  // 4. Draw REROLL Button (Refresh)
  // Highlight if hovered
  ctx.fillStyle = rackState.isHoveringReroll ? "rgba(99, 102, 241, 0.2)" : "rgba(0,0,0,0.05)";
  ctx.beginPath();
  ctx.arc(buttonsX, rerollY, 20, 0, Math.PI * 2);
  ctx.fill();

  if (rackState.isRerollLocked) {
    ctx.fillStyle = "rgba(99, 102, 241, 0.3)"; // Indigo tint
    ctx.beginPath();
    ctx.moveTo(buttonsX, rerollY);
    // Draw the pie slice representing remaining time
    ctx.arc(
      buttonsX,
      rerollY,
      18,
      -Math.PI / 2,
      -Math.PI / 2 + (Math.PI * 2 * rackState.rerollCooldownPercent),
      false
    );
    ctx.lineTo(buttonsX, rerollY);
    ctx.fill();
  }

  // Icon
  ctx.fillStyle = rackState.isRerollLocked ? "#94a3b8" : (rackState.isHoveringReroll ? "#4f46e5" : "#6366f1");
  ctx.font = "18px 'Material Icons Round'";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("autorenew", buttonsX, rerollY);
  ctx.restore();

  // 5. Dragged Tile
  if (rackState.draggingIndex !== -1) {
    drawTile(
      ctx,
      rackState.dragX - rackState.dragOffsetX,
      rackState.dragY - rackState.dragOffsetY,
      tileSize,
      rackState.tiles[rackState.draggingIndex],
      true,
      1.1, // Slight pop scale while dragging
      rackState.isHoveringDestroy // Pass hover state to change color
    );
  }
}

function triggerRerollCooldown() {
  rackState.isRerollLocked = true;
  const startTime = performance.now();

  function animate() {
    const now = performance.now();
    const elapsed = now - startTime;
    const progress = elapsed / rackState.cooldownDuration;

    if (progress < 1) {
      // progress 0 (start) -> 1 (end)
      // We want the overlay to disappear, so we track 1 down to 0
      rackState.rerollCooldownPercent = 1 - progress;
      renderCanvas(window.lastKnownState);
      requestAnimationFrame(animate);
    } else {
      // Cooldown finished
      rackState.isRerollLocked = false;
      rackState.rerollCooldownPercent = 0;
      renderCanvas(window.lastKnownState);
    }
  }
  animate();
}

function drawTile(ctx, x, y, size, letter, isDragging, scale = 1, isHoveringDestroy = false) {
  const userColor = getComputedStyle(document.documentElement).getPropertyValue('--user-color') || '#4f46e5';

  ctx.save();

  // Apply external scale and center point adjustment
  if (scale !== 1) {
    ctx.translate(x + size / 2, y + size / 2);
    ctx.scale(scale, scale);
    ctx.translate(-(x + size / 2), -(y + size / 2));
  }

  if (isDragging) {
    ctx.shadowColor = "rgba(0,0,0,0.3)";
    ctx.shadowBlur = 15;
  }

  // Use red color when hovering over destroy button
  ctx.fillStyle = isHoveringDestroy ? "#ef4444" : userColor;
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

      // --- CHECK JUMP ANIMATION (Wiggle) ---
      let jumpOffset = 0;
      let rotation = 0;
      const jumpAnim = jumpAnimations.find(a => a.x === cell.x && a.y === cell.y);
      if (jumpAnim) {
        const now = performance.now();
        if (now >= jumpAnim.startTime) {
          const elapsed = now - jumpAnim.startTime;
          const progress = Math.min(elapsed / jumpAnim.duration, 1);

          // Jump: Up and Down
          // Jump: Minimal vertical motion
          jumpOffset = -5 * Math.sin(progress * Math.PI);

          // Wiggle: Tilt left and right (More intense)
          // fast wiggle: sin(progress * 8PI)
          rotation = 0.3 * Math.sin(progress * Math.PI * 8) * (1 - progress);
        }
      }

      // --- DYNAMIC COLOR LOGIC ---
      // Use cell.color (sent from server) or fallback to primary indigo
      const tileColor = cell.color || "#4f46e5";

      ctx.save();
      // Apply jump & wiggle transform
      if (jumpOffset !== 0 || rotation !== 0) {
        ctx.translate(cx, cy); // Move to center
        ctx.translate(0, jumpOffset);
        ctx.rotate(rotation);
        ctx.translate(-cx, -cy); // Move back
      }

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

      ctx.restore();
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

export function render_pending(ctx, state, startX, endX, startY, endY, cellSize, rect) {

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
      ctx.restore();
    }
  });
  // Inside render_textbox, Section 3: Removal Animations
  removalAnimations.forEach((anim) => {
    const elapsed = performance.now() - anim.startTime;
    const progress = Math.min(elapsed / anim.duration, 1);

    const easeOut = 1 - Math.pow(1 - progress, 3);
    const opacity = 1 - progress;

    let cx, cy, halfSize, explodeDist;

    if (anim.isScreenSpace) {
      // Special handling for screen-space animations (e.g., trash button)
      // We need to work in screen coordinates, so save/restore the transform
      ctx.restore(); // Exit world space
      ctx.save(); // Enter screen space

      cx = anim.screenX;
      cy = anim.screenY;
      halfSize = 30; // Fixed size for screen space
      explodeDist = 40 * easeOut;
    } else {
      // Normal world-space animation for board tiles
      halfSize = (cellSize - 8) / 2;
      explodeDist = cellSize * 0.8 * easeOut;
      cx = anim.x * cellSize + cellSize / 2;
      cy = anim.y * cellSize + cellSize / 2;
    }

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
      const fontSize = anim.isScreenSpace ? 24 : cellSize * 0.4;
      ctx.font = `bold ${fontSize}px Lexend, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(anim.letter, 0, 0);
      ctx.restore(); // Restore per quadrant
    });

    if (anim.isScreenSpace) {
      ctx.restore(); // Exit screen space
      ctx.save(); // Re-enter world space
      ctx.translate(rect.width / 2, rect.height / 2);
      ctx.scale(camera.zoom / 40, camera.zoom / 40);
      ctx.translate(-camera.x, -camera.y);
    }
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
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  // Update global camera mouse tracking for the "ghost" tile
  camera.mouseX = mouseX;
  camera.mouseY = mouseY;

  // --- RECALCULATE RACK CONSTANTS ---
  // (Must match render_rack to align hitboxes)
  const tileCount = 10;
  const tileSize = 60;
  const gap = 12;
  const totalWidth = (tileCount * tileSize) + ((tileCount - 1) * gap);
  const startX = (rect.width - totalWidth) / 2;
  const rackY = rect.height - 100;
  const buttonsX = startX + totalWidth + 50;
  const destroyY = rackY + 15;
  const rerollY = rackY + 65;

  // --- CHECK IF MOUSE IS OVER RACK AREA ---
  isMouseOverRack = mouseX >= startX - 20 &&
    mouseX <= startX + totalWidth + 110 &&
    mouseY >= rackY - 20 &&
    mouseY <= rackY + tileSize + 60;

  // --- TILE HOVER DETECTION FOR LIFT ANIMATION ---
  let newHoveredIndex = -1;
  if (!isDraggingFromRack && isMouseOverRack) {
    rackState.tiles.forEach((letter, i) => {
      if (!letter) return;
      const x = startX + i * (tileSize + gap);
      if (mouseX >= x && mouseX <= x + tileSize && mouseY >= rackY - 20 && mouseY <= rackY + tileSize + 20) {
        newHoveredIndex = i;
      }
    });
  }

  // Update hovered index and trigger animation loop if changed
  if (rackState.hoveredIndex !== newHoveredIndex) {
    rackState.hoveredIndex = newHoveredIndex;
    ensureAnimationLoop(); // Start animation loop for smooth hover transition
  }

  if (isDraggingFromRack) {
    rackState.dragX = mouseX;
    rackState.dragY = mouseY;

    // Check distance to buttons for hover effect
    const distToDestroy = Math.hypot(mouseX - buttonsX, mouseY - destroyY);
    const distToReroll = Math.hypot(mouseX - buttonsX, mouseY - rerollY);
    rackState.isHoveringDestroy = distToDestroy < 25;
    rackState.isHoveringReroll = distToReroll < 20;

  }
  else if (camera.isDragging) {
    camera.wasDragging = true;
    const factor = 40 / camera.zoom;
    camera.x -= (e.clientX - camera.lastMouseX) * factor;
    camera.y -= (e.clientY - camera.lastMouseY) * factor;
    camera.lastMouseX = e.clientX;
    camera.lastMouseY = e.clientY;
  }


  if (isDraggingFromRack || camera.isDragging) {
    // STAY CLOSED WHILE DRAGGING
    canvas.style.cursor = "url('/static/hand_small_closed.png') 8 8, grabbing";
  }
  else {
    // Check for hover targets
    const distToReroll = Math.hypot(mouseX - buttonsX, mouseY - rerollY);
    const distToDestroy = Math.hypot(mouseX - buttonsX, mouseY - destroyY);

    rackState.isHoveringReroll = distToReroll < 20;
    rackState.isHoveringDestroy = distToDestroy < 25;

    if (rackState.isHoveringReroll || rackState.isHoveringDestroy) {
      // Hovering buttons: Pointing Hand
      canvas.style.cursor = "url('/static/hand_small_point.png') 8 8, pointer";
    } else {
      // Default: Open Hand
      canvas.style.cursor = "url('/static/hand_small_open.png') 8 8, default";
    }
  }
  // Single render call to keep performance high
  renderCanvas(window.lastKnownState || { board: [], players: {} });
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

  // Check if mouse is over entire rack area (including buttons)
  const isOverRackArea = mouseX >= startX - 20 &&
    mouseX <= startX + totalWidth + 110 &&
    mouseY >= rackY - 20 &&
    mouseY <= rackY + tileSize + 60;

  rackState.tiles.forEach((letter, i) => {
    if (!letter) return; // Can't drag empty slot
    const x = startX + i * (tileSize + gap);

    // Expanded hitbox for easier dragging - add padding around the tile
    const hitboxPadding = 10;
    const hitboxX = x - hitboxPadding;
    const hitboxY = rackY - 20; // Use fixed position, ignore hover offset for hitbox
    const hitboxWidth = tileSize + hitboxPadding * 2;
    const hitboxHeight = tileSize + 40; // Extended vertical region

    if (mouseX >= hitboxX && mouseX <= hitboxX + hitboxWidth &&
      mouseY >= hitboxY && mouseY <= hitboxY + hitboxHeight) {
      rackState.draggingIndex = i;
      rackState.dragOffsetX = mouseX - x;
      rackState.dragOffsetY = mouseY - (rackY + (rackState.hoverOffsets[i] || 0));
      isDraggingFromRack = true;
      rackState.dragX = mouseX;
      rackState.dragY = mouseY;
    }
  });

  // Only enable camera drag if NOT over rack area at all
  if (!isDraggingFromRack && !isOverRackArea) {
    camera.isDragging = true;
    camera.wasDragging = false;
    camera.lastMouseX = e.clientX;
    camera.lastMouseY = e.clientY;
  }
});

window.addEventListener('mouseup', (e) => {
  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  // Rack & Button Calculation constants
  const tileCount = 10;
  const tileSize = 60;
  const gap = 12;
  const totalWidth = (tileCount * tileSize) + ((tileCount - 1) * gap);
  const startX = (rect.width - totalWidth) / 2;
  const rackY = rect.height - 100;
  const buttonsX = startX + totalWidth + 50;
  const destroyY = rackY + 15;
  const rerollY = rackY + 65;

  if (isDraggingFromRack) {
    // Check if dropped on Destroy button
    const distToDestroy = Math.hypot(mouseX - buttonsX, mouseY - destroyY);

    if (distToDestroy < 25) {
      // ACTION: DESTROY - Trigger sucking animation
      const letter = rackState.tiles[rackState.draggingIndex];
      const userColor = getComputedStyle(document.documentElement).getPropertyValue('--user-color') || '#4f46e5';

      // Create a fake tile at destroy button position for animation
      import("./RenderCanvas.js").then(m => {
        m.triggerTrashAnimation({
          letter: letter,
          color: userColor,
          screenX: buttonsX,
          screenY: destroyY
        });
      });

      if (globalWs?.readyState === WebSocket.OPEN) {
        globalWs.send(JSON.stringify({
          type: "DESTROY_TILE",
          hand_index: rackState.draggingIndex
        }));
      }

      // --- OPTIMISTIC UI: Remove tile immediately to prevent flicker ---
      rackState.tiles[rackState.draggingIndex] = null;
    } else {
      // Check if dropped back on Rack (to cancel)
      const isOverRack = mouseX >= startX - 20 &&
        mouseX <= startX + totalWidth + 110 &&
        mouseY >= rackY - 20;

      if (!isOverRack) {
        // ACTION: PLACE ON BOARD
        const worldPos = screenToWorld(mouseX, mouseY, rect);
        const letter = rackState.tiles[rackState.draggingIndex];

        // --- CHECK IF POSITION IS VALID (not occupied) ---
        const state = window.lastKnownState || { board: [], pending_tiles: [] };
        const isOccupied = (state.board || []).some(cell => cell.x === worldPos.tileX && cell.y === worldPos.tileY) ||
          (state.pending_tiles || []).some(cell => cell.x === worldPos.tileX && cell.y === worldPos.tileY);

        if (!isOccupied) {
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

          // --- OPTIMISTIC UI: Remove tile immediately to prevent flicker ---
          rackState.tiles[rackState.draggingIndex] = null;
        }
        // If occupied, tile stays in hand (no action taken)
      }
    }
  } else {
    // ACTION: REROLL CLICK (Check if clicking reroll when NOT dragging)
    const distToReroll = Math.hypot(mouseX - buttonsX, mouseY - rerollY);
    if (distToReroll < 20) {
      if (!rackState.isRerollLocked) {
        if (globalWs?.readyState === WebSocket.OPEN) {
          globalWs.send(JSON.stringify({ type: "REROLL_HAND" }));
          rackState.fullArrivalPending = true;
          triggerRerollCooldown();
        }
      }

    }
  }

  // Reset State
  rackState.draggingIndex = -1;
  isDraggingFromRack = false;
  rackState.isHoveringDestroy = false;
  renderCanvas(window.lastKnownState);
  camera.isDragging = false;
});

canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  const delta = e.deltaY > 0 ? 0.9 : 1.1;
  camera.zoom = Math.min(Math.max(camera.zoom * delta, 15), 200);
  renderCanvas(window.lastKnownState || { board: [] });
}, { passive: false });
