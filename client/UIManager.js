let previousScores = {};

export function updateLeaderboard(playersObj) {
  const container = document.getElementById("leaderboard");
  if (!container || !playersObj) return;

  // 1. Sort players by score (DESC)
  const sortedPlayers = Object.entries(playersObj)
    .map(([id, data]) => ({ id, ...data }))
    .sort((a, b) => b.score - a.score);

  sortedPlayers.forEach((player, index) => {
    const rowId = `player-${player.id}`;
    let row = document.getElementById(rowId);

    const oldScore = previousScores[player.id] || 0;
    const isIncrease = player.score > oldScore;

    const isMe = player.id === window.myPlayerId;
    const isFirst = index === 0 && player.score > 0;

    // Create row if it doesn't exist
    if (!row) {
      row = document.createElement("div");
      row.id = rowId;
      row.className = "leaderboard-item flex items-center justify-between p-3 rounded-xl border bg-white dark:bg-slate-800 shadow-sm";
      container.appendChild(row);
    }

    // Update classes based on current state
    row.className = `
      leaderboard-item
      flex items-center justify-between p-3 rounded-xl border
      bg-white dark:bg-slate-800 shadow-sm
      ${isFirst ? "border-yellow-400" : "border-slate-200 dark:border-slate-700"}
      ${isMe ? "ring-2 ring-primary ring-offset-0" : ""}
    `;

    // Set order for flex reordering animation
    row.style.order = index;

    row.innerHTML = `
      <div class="flex items-center gap-3 flex-1 min-w-0">
        <div class="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-indigo-600 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
          ${player.name.charAt(0).toUpperCase()}
        </div>
        <div class="flex-1 min-w-0">
          <div class="font-medium text-sm ${isMe ? "text-primary font-bold" : "dark:text-slate-200"} truncate">
            ${player.name + (isMe ? " (You)" : "")}
          </div>
          ${isMe ? '<span class="inline-block text-xs px-2 py-0.5 bg-primary text-white rounded-full font-semibold whitespace-nowrap">PLAYING</span>' : ''}
        </div>
      </div>  
      <div class="text-right flex-shrink-0 ml-2">
        <div class="font-bold text-lg" data-score-element="true">
          ${player.score} pts
        </div>
        <span class="font-bold text-sm text-slate-400">
          #${index + 1}
        </span>
      </div>
    `;
    
    // Trigger animation on score increase
    if (isIncrease) {
      const scoreElement = row.querySelector('[data-score-element="true"]');
      requestAnimationFrame(() => {
        scoreElement.classList.add('score-bump');
      });
    }
    
    previousScores[player.id] = player.score;
  });

  // Remove players that are no longer in the game
  const existingRows = container.querySelectorAll('.leaderboard-item');
  existingRows.forEach(row => {
    const playerId = row.id.replace('player-', '');
    if (!playersObj[playerId]) {
      row.remove();
    }
  });
}
