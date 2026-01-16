import { multipliers } from './config.js';

export let boardState = [];
export let rackState = [];

export function setRackState(newState) {
    rackState = newState;
}

export function initBoard(initialLetters = []) {
    boardState = [];
    for (let y = 0; y < 15; y++) {
        boardState[y] = [];
        for (let x = 0; x < 15; x++) {
            const mult = multipliers[`${y},${x}`] || null;
            boardState[y][x] = {
                x, y,
                letter: null,
                multiplier: mult,
                points: 0
            };
        }
    }

    initialLetters.forEach(tile => {
        if (boardState[tile.y] && boardState[tile.y][tile.x]) {
            boardState[tile.y][tile.x].letter = tile.L;
            boardState[tile.y][tile.x].points = tile.P;
        }
    });
}
