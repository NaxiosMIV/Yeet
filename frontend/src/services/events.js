import { boardState, rackState, setRackState } from '../core/state.js';

export function initEvents(renderAllCb) {
    const onDragStart = (e, tile, isPlaced, tileEl) => {
        e.dataTransfer.setData('tile', JSON.stringify(tile));
        if (isPlaced) {
            const parent = tileEl.parentElement;
            e.dataTransfer.setData('from', 'board');
            e.dataTransfer.setData('oldCoords', `${parent.dataset.y},${parent.dataset.x}`);
        } else {
            e.dataTransfer.setData('from', 'rack');
        }
        tileEl.classList.add('dragging');
    };

    const onDragEnd = (tileEl) => {
        tileEl.classList.remove('dragging');
    };

    const onDragOver = (e) => {
        e.preventDefault();
        const target = e.currentTarget;
        if (target.dataset.x !== undefined && !target.querySelector('.font-black')) {
            target.classList.add('drop-target');
        }
    };

    const onDragLeave = (e) => {
        e.currentTarget.classList.remove('drop-target');
    };

    const onDropToBoard = (e, x, y) => {
        e.preventDefault();
        const cellEl = e.currentTarget;
        cellEl.classList.remove('drop-target');
        if (boardState[y][x].letter) return;

        const tileData = JSON.parse(e.dataTransfer.getData('tile'));
        const from = e.dataTransfer.getData('from');

        if (from === 'rack') {
            setRackState(rackState.filter(t => t.id !== tileData.id));
        } else if (from === 'board') {
            const [oldY, oldX] = e.dataTransfer.getData('oldCoords').split(',').map(Number);
            boardState[oldY][oldX].letter = null;
            boardState[oldY][oldX].points = 0;
        }

        boardState[y][x].letter = tileData.letter;
        boardState[y][x].points = tileData.points;
        renderAllCb();
    };

    const onDropToRack = (e) => {
        e.preventDefault();
        if (e.dataTransfer.getData('from') === 'board') {
            const tileData = JSON.parse(e.dataTransfer.getData('tile'));
            const [oldY, oldX] = e.dataTransfer.getData('oldCoords').split(',').map(Number);
            boardState[oldY][oldX].letter = null;
            boardState[oldY][oldX].points = 0;
            rackState.push({ ...tileData, color: 'bg-tile-peach', id: 't' + Date.now() });
            renderAllCb();
        }
    };

    return {
        onDragStart,
        onDragEnd,
        onDragOver,
        onDragLeave,
        onDropToBoard,
        onDropToRack
    };
}

export function initSocket() {
    // Socket.io Placeholder
    const socket = { on: () => { }, emit: () => { } };
    try { if (typeof io !== 'undefined') socket = io(); } catch (e) { }
    return socket;
}
