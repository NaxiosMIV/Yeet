import { initBoard, setRackState } from './core/state.js';
import { initialRackState, toggleDarkMode } from './core/config.js';
import { renderBoard, renderRack } from './ui/render.js';
import { initEvents, initSocket } from './services/events.js';

const grid = document.getElementById('game-board');
const rackEl = document.getElementById('rack');
const activityLog = document.getElementById('activity-log');
const timerDisplay = document.getElementById('timer-display');

// Global helper for Dark Mode since it's used in HTML onclick
window.toggleDarkMode = toggleDarkMode;

function renderAll() {
    renderBoard(grid, dragHandlers);
    renderRack(rackEl, dragHandlers);
}

const dragHandlers = initEvents(renderAll);
const socket = initSocket();

// Initial Letters per reference
const initialLetters = [
    { y: 7, x: 5, L: 'C', P: 3 }, { y: 7, x: 6, L: 'H', P: 4 }, { y: 7, x: 7, L: 'O', P: 1 },
    { y: 7, x: 8, L: 'I', P: 1 }, { y: 7, x: 9, L: 'C', P: 3 }, { y: 7, x: 10, L: 'E', P: 1 }
];

// Socket Listeners logic
socket.on('new_activity', (data) => {
    const activityItem = document.createElement('div');
    activityItem.className = 'flex gap-2 animate-fadeIn';
    activityItem.innerHTML = `<span class="font-bold ${data.color || 'text-primary'}">${data.user}</span><span class="text-slate-600 dark:text-slate-400">${data.message}</span>`;
    activityLog.prepend(activityItem);
    while (activityLog.children.length > 20) activityLog.removeChild(activityLog.lastChild);
});

socket.on('timer_sync', (data) => {
    if (data.timeLeft !== undefined) {
        const min = Math.floor(data.timeLeft / 60);
        const sec = data.timeLeft % 60;
        timerDisplay.innerText = `Your turn ends in ${min}:${sec.toString().padStart(2, '0')}`;
        if (data.timeLeft < 15) timerDisplay.classList.add('text-red-500', 'animate-pulse');
        else timerDisplay.classList.remove('text-red-500', 'animate-pulse');
    }
});

// App Bootstrap
initBoard(initialLetters);
setRackState(initialRackState);
renderAll();
