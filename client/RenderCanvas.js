// --- Global Camera & Game State ---
const canvas = document.getElementById("game-canvas");

export const camera = {
  x: 0, zoom: 40, isDragging: false,
  lastMouseX: 0, lastMouseY: 0
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

  ctx.fillStyle = "#f1f5f9"; // Background color
  ctx.fillRect(0, 0, rect.width, rect.height);

  ctx.save();
  ctx.translate(rect.width / 2, rect.height / 2);
  ctx.scale(camera.zoom / 40, camera.zoom / 40); 
  ctx.translate(-camera.x, -camera.y);

  const cellSize = 40; 
  // Calculate view bounds in world space
  const viewW = rect.width * (40 / camera.zoom);
  const viewH = rect.height * (40 / camera.zoom);
  const startX = Math.floor((camera.x - viewW / 2) / cellSize);
  const endX = Math.ceil((camera.x + viewW / 2) / cellSize);
  const startY = Math.floor((camera.y - viewH / 2) / cellSize);
  const endY = Math.ceil((camera.y + viewH / 2) / cellSize);

  // --- DRAW TILES ---
  for (let x = startX; x <= endX; x++) {
    for (let y = startY; y <= endY; y++) {
      const px = x * cellSize;
      const py = y * cellSize;

      // The "Grey Squares"
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
      
      ctx.strokeStyle = "#e2e8f0";
      ctx.lineWidth = 1;
      ctx.strokeRect(px, py, cellSize, cellSize);
    }
  }

  // --- DRAW LETTERS ---
  ctx.font = `bold ${cellSize * 0.5}px Lexend, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  
  (state.board || []).forEach(cell => {
    ctx.fillStyle = "#4f46e5";
    ctx.fillText(cell.letter.toUpperCase(), cell.x * cellSize + cellSize/2, cell.y * cellSize + cellSize/2);
  });

  ctx.restore();
}

canvas.addEventListener('click', (e) => {
  // Only place if we weren't just dragging the map
  if (camera.wasDragging) return;

  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  // --- REVERSE TRANSFORMATION ---
  // 1. Center the coordinates (inverse of translate(w/2, h/2))
  let worldX = mouseX - rect.width / 2;
  let worldY = mouseY - rect.height / 2;

  // 2. Scale for zoom (inverse of scale(zoom/40))
  const zoomFactor = 40 / camera.zoom;
  worldX *= zoomFactor;
  worldY *= zoomFactor;

  // 3. Add camera position (inverse of translate(-camX, -camY))
  worldX += camera.x;
  worldY += camera.y;

  // 4. Find tile index
  const tileX = Math.floor(worldX / 40);
  const tileY = Math.floor(worldY / 40);

  console.log(`Placed at: ${tileX}, ${tileY}`);
  
  // TRIGGER YOUR GAME LOGIC HERE
  // Example: emitPlaceLetter(tileX, tileY, "A");
});

// Update the Mousedown/Move to track if it was a drag or a click
canvas.addEventListener('mousedown', () => { camera.wasDragging = false; });
window.addEventListener('mousemove', () => { 
    if(camera.isDragging) camera.wasDragging = true; 
});