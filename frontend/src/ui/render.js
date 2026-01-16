import { boardState, rackState } from '../core/state.js';
import { multiplierColors } from '../core/config.js';
import { createTileElement } from './tile.js';

export function renderBoard(gridContainer, dragHandlers) {
    gridContainer.innerHTML = '';
    for (let y = 0; y < 15; y++) {
        for (let x = 0; x < 15; x++) {
            const cell = boardState[y][x];
            const cellEl = document.createElement('div');
            cellEl.className = 'w-full aspect-square rounded-sm flex items-center justify-center text-[10px] font-bold transition-all relative';
            cellEl.dataset.x = x;
            cellEl.dataset.y = y;

            if (cell.letter) {
                const tileEl = createTileElement(
                    { letter: cell.letter, points: cell.points, id: `placed-${y}-${x}` },
                    true,
                    dragHandlers.onDragStart,
                    dragHandlers.onDragEnd
                );
                cellEl.appendChild(tileEl);
            } else if (cell.multiplier) {
                cellEl.className += ` ${multiplierColors[cell.multiplier]}`;
                cellEl.textContent = cell.multiplier;
            } else {
                cellEl.className += ' bg-slate-50 dark:bg-slate-800/50 text-slate-400/20';
            }

            cellEl.addEventListener('dragover', dragHandlers.onDragOver);
            cellEl.addEventListener('dragleave', dragHandlers.onDragLeave);
            cellEl.addEventListener('drop', (e) => dragHandlers.onDropToBoard(e, x, y));

            gridContainer.appendChild(cellEl);
        }
    }
}

export function renderRack(rackContainer, dragHandlers) {
    rackContainer.innerHTML = '';
    rackState.forEach(tile => {
        rackContainer.appendChild(
            createTileElement(tile, false, dragHandlers.onDragStart, dragHandlers.onDragEnd)
        );
    });

    rackContainer.addEventListener('dragover', dragHandlers.onDragOver);
    rackContainer.addEventListener('drop', (e) => dragHandlers.onDropToRack(e));
}
