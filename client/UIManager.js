let previousScores = {};

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
      row.className = "leaderboard-row flex items-center justify-between p-4 rounded-2xl border transition-all duration-500";
      container.appendChild(row);
    }

    container.appendChild(row); // Maintain DOM order for flex layout
    row.style.order = index;

    const isMe = String(player.id) === String(window.myPlayerId);
    const oldScore = previousScores[player.id] || 0;
    const isIncrease = player.score > oldScore;

    row.className = `leaderboard-row flex items-center justify-between p-4 rounded-2xl border transition-all duration-500 ${
      isMe ? 'bg-indigo-50 border-indigo-200 ring-1 ring-indigo-500/20' : 'bg-transparent border-transparent'
    }`;

    row.innerHTML = `
      <div class="flex items-center gap-4">
        <div class="relative">
          ${isMe ? '<span class="absolute -top-1 -right-1 w-3 h-3 bg-green-500 border-2 border-white rounded-full"></span>' : ''}
        </div>
        <div>
          <span class="font-bold text-slate-900 block leading-tight">${isMe ? player.name+'(You)' : player.name}</span>
          <span class="text-[11px] text-slate-500 font-bold uppercase">${player.score} pts</span>
        </div>
      </div>
      <span class="text-xl font-black ${index === 0 ? 'text-indigo-600' : 'text-slate-300'}">#${index + 1}</span>
    `;

    previousScores[player.id] = player.score;
  });
}