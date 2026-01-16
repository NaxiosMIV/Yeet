export const multipliers = {
    '0,0': '3W', '0,7': '3W', '0,14': '3W',
    '7,0': '3W', '7,14': '3W',
    '14,0': '3W', '14,7': '3W', '14,14': '3W',
    '1,1': '2W', '2,2': '2W', '3,3': '2W', '4,4': '2W',
    '1,13': '2W', '2,12': '2W', '3,11': '2W', '4,10': '2W',
    '13,1': '2W', '12,2': '2W', '11,3': '2W', '10,4': '2W',
    '13,13': '2W', '12,12': '2W', '11,11': '2W', '10,10': '2W',
    '7,7': '★',
    '1,5': '3L', '1,9': '3L', '5,1': '3L', '5,5': '3L', '5,9': '3L', '5,13': '3L',
    '9,1': '3L', '9,5': '3L', '9,9': '3L', '9,13': '3L', '13,5': '3L', '13,9': '3L',
    '0,3': '2L', '0,11': '2L', '2,6': '2L', '2,8': '2L', '3,0': '2L', '3,7': '2L', '3,14': '2L',
    '6,2': '2L', '6,6': '2L', '6,8': '2L', '6,12': '2L', '7,3': '2L', '7,11': '2L',
    '8,2': '2L', '8,6': '2L', '8,8': '2L', '8,12': '2L', '11,0': '2L', '11,7': '2L', '11,14': '2L',
    '12,6': '2L', '12,8': '2L', '14,3': '2L', '14,11': '2L'
};

export const multiplierColors = {
    '3W': 'bg-orange-100 dark:bg-orange-900/30 text-orange-500',
    '2W': 'bg-pink-50 dark:bg-pink-900/20 text-pink-400',
    '3L': 'bg-blue-100 dark:bg-blue-900/30 text-blue-500',
    '2L': 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-500',
    '★': 'bg-pink-100 dark:bg-pink-900/30 text-pink-500'
};

export function toggleDarkMode() {
    document.documentElement.classList.toggle('dark');
}

export const initialRackState = [
    { id: 't1', letter: 'A', points: 1, color: 'bg-tile-peach' },
    { id: 't2', letter: 'S', points: 1, color: 'bg-tile-mint' },
    { id: 't3', letter: 'P', points: 3, color: 'bg-tile-lavender' },
    { id: 't4', letter: 'L', points: 1, color: 'bg-tile-blue' },
    { id: 't5', letter: 'Y', points: 4, color: 'bg-tile-peach' },
    { id: 't6', letter: 'T', points: 1, color: 'bg-tile-mint' },
];
