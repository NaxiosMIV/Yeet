export function createTileElement(tile, isPlaced, onDragStart, onDragEnd) {
    const tileEl = document.createElement('div');
    const colorClass = tile.color || (isPlaced ? 'bg-yellow-400' : 'bg-tile-peach');

    tileEl.className = `${colorClass} rounded-xl tile-shadow flex flex-col items-center justify-center text-slate-800 relative cursor-grab active:cursor-grabbing transition-transform`;

    if (isPlaced) {
        tileEl.className = `w-full h-full rounded shadow-sm flex flex-col items-center justify-center bg-yellow-400 text-slate-900 relative cursor-grab active:cursor-grabbing scale-100 hover:scale-105 transition-transform`;
    } else {
        tileEl.className += ' w-12 h-14 hover:-translate-y-1';
    }

    tileEl.draggable = true;
    tileEl.innerHTML = `
        <span class="${isPlaced ? 'text-lg' : 'text-2xl'} font-display font-black leading-none">${tile.letter}</span>
        <span class="absolute bottom-1 right-1.5 text-[10px] font-bold">${tile.points}</span>
    `;

    tileEl.addEventListener('dragstart', (e) => onDragStart(e, tile, isPlaced, tileEl));
    tileEl.addEventListener('dragend', () => onDragEnd(tileEl));

    return tileEl;
}
