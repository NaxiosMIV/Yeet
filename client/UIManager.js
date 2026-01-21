const previousScores = {};

export function updateLeaderboard(playersObj) {
  const container = document.getElementById("leaderboard");
  if (!container || !playersObj) return;

  const sorted = Object.entries(playersObj)
    .map(([id, data]) => ({ id, ...data }))
    .sort((a, b) => b.score - a.score);

  sorted.forEach((player, index) => {
    const rowId = `player-${player.id}`;
    let row = document.getElementById(rowId);

    if (!row) {
      row = document.createElement('div');
      row.id = rowId;
      row.innerHTML = `
        <div class="flex flex-row items-center gap-2">
          <span class="player-name font-bold text-slate-900 text-[20px] truncate max-w-[130px]"></span>
        </div>
        
        <span class="player-score ml-auto text-[14px] text-slate-500 font-bold tracking-tighter"></span>
        <span class="player-rank text-[20px] font-black"></span>
      `;
      container.appendChild(row);
    }

    const isMe = String(player.id) === String(window.myPlayerId);

    // 1. Get the old score and cast to Number to be safe
    const oldScore = previousScores[player.id] !== undefined ? previousScores[player.id] : player.score;

    // Update Text Content
    row.querySelector('.player-name').textContent = isMe ? player.name + '(You)' : player.name;
    row.querySelector('.player-score').textContent = `${player.score} p`;
    row.querySelector('.player-rank').textContent = `#${index + 1}`;

    // Base Classes (Tailwind)
    row.className = `flex items-center gap-3 px-4 py-2 rounded-xl border duration-300 min-w-[140px] ${isMe ? 'bg-indigo-50 border-indigo-200 ring-2 ring-indigo-500/10' : 'bg-white border-slate-200'
      }`;
    row.style.order = index;

    // 2. CHECK FOR CHANGE
    if (player.score !== oldScore) {
      // Determine colors based on gain/loss
      const flashColor = player.score > oldScore ? '#83ffae' : '#ff8080'; // Light Green or Light Red

      // 3. TRIGGER WEB ANIMATION API
      row.animate(
        [
          { transform: 'scale(1)', backgroundColor: isMe ? '#EEF2FF' : '#FFFFFF' },
          { transform: 'scale(1.05)', backgroundColor: flashColor, borderColor: player.score > oldScore ? '#10B981' : '#EF4444' },
          { transform: 'scale(1)', backgroundColor: isMe ? '#EEF2FF' : '#FFFFFF' }
        ],
        {
          duration: 800,
          fill: 'forwards'
        }
      );
    }

    // 4. IMPORTANT: Update the tracker for THIS player before moving to the next
    previousScores[player.id] = player.score;
  });
}