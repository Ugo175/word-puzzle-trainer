'use strict';
const $ = id => document.getElementById(id);
const POINTS = { a: 1, b: 3, c: 3, d: 2, e: 1, f: 4, g: 2, h: 4, i: 1, j: 8, k: 5, l: 1, m: 3, n: 1, o: 1, p: 3, q: 10, r: 1, s: 1, t: 1, u: 1, v: 4, w: 4, x: 8, y: 4, z: 10, '?': 0 };
const STORAGE = 'tile-club-history-v1';
const racks = ['react?', 'carets', 'planet', 'garden', 'stream', 'train?'];
const state = { mode: 'practice', round: null, active: false, pending: false, finishing: false, finishAfter: false, deadline: 0, ticker: null, words: [], found: new Set(), revealed: false, history: [], storage: true, version: 0 };
function el(tag, cls, text) { const n = document.createElement(tag); if (cls)
    n.className = cls; if (text !== undefined)
    n.textContent = text; return n; }
function error(text = '') { $('error').textContent = text; $('error').hidden = !text; }
function feedback(text, success = false) { $('feedback').textContent = text; $('feedback').classList.toggle('success', success); }
function rack() { return $('rack').value.trim().toLowerCase(); }
function announce(text) { $('announcement').textContent = text; }
function formatTime(seconds) { return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`; }
function renderTiles(letters = rack()) {
    $('tiles').replaceChildren(...Array.from(letters).filter(c => c in POINTS).map(letter => {
        const tile = el('button', 'tile' + (letter === '?' ? ' blank' : ''), letter === '?' ? '?' : letter.toUpperCase());
        tile.type = 'button';
        tile.append(el('small', '', String(POINTS[letter])));
        tile.setAttribute('aria-label', letter === '?' ? 'Blank tile, zero points' : `${letter.toUpperCase()}, ${POINTS[letter]} points`);
        tile.addEventListener('click', () => { if (!state.active)
            return; if (letter !== '?')
            $('guess').value = ($('guess').value + letter).slice(0, 12);
        else
            feedback('Type any letter for the blank tile. It scores zero.'); $('guess').focus(); });
        return tile;
    }));
}
function lock() {
    for (const id of ['rack', 'duration', 'minimum', 'new-rack', 'practice-tab', 'solver-tab', 'start', 'solve'])
        $(id).disabled = state.active || state.pending;
    $('submit-guess').disabled = state.pending || !state.active;
    $('finish').disabled = state.finishing;
}
function validHistory(record) { return record && typeof record.id === 'string' && typeof record.rack === 'string' && /^[a-z?]{1,12}$/.test(record.rack) && Number.isInteger(record.score) && record.score >= 0 && record.score < 10000000 && [30, 60, 120].includes(record.seconds) && Array.isArray(record.words) && record.words.every(w => typeof w === 'string' && /^[a-z]{1,12}$/.test(w)) && typeof record.date === 'string' && !Number.isNaN(Date.parse(record.date)); }
function readHistory() { try {
    const raw = localStorage.getItem(STORAGE);
    const records = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(records) || !records.every(validHistory))
        throw Error();
    state.history = records.slice(-200);
}
catch {
    state.storage = false;
    $('storage-note').textContent = 'Saved history unavailable. Progress stays in this session; export it to keep a copy.';
} }
function renderHistory() {
    $('best-score').textContent = state.history.length ? Math.max(...state.history.map(r => r.score)) : '—';
    $('total-rounds').textContent = state.history.length;
    $('total-words').textContent = state.history.reduce((total, r) => total + r.words.length, 0);
    $('export').disabled = !state.history.length;
    $('history').replaceChildren(...state.history.slice(-4).reverse().map(record => { const row = el('div', 'history-row'); const info = el('div'); info.append(el('span', 'history-rack', record.rack.toUpperCase()), el('small', '', `${record.seconds}s · ${record.words.length} words · ${new Date(record.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`)); const score = el('span', 'history-score', String(record.score)); score.append(el('small', '', 'pts')); row.append(info, score); return row; }));
    if (!state.history.length)
        $('history').append(el('p', '', 'Your first round is waiting.'));
}
function remember(result) {
    if (state.history.some(record => record.id === result.id))
        return;
    state.history.push({ id: result.id, rack: result.rack, seconds: result.seconds, minimum: result.minimum, score: result.score, words: result.found.map(item => item.word), possible_words: result.possible_words, date: result.date });
    state.history = state.history.slice(-200);
    if (state.storage) {
        try {
            localStorage.setItem(STORAGE, JSON.stringify(state.history));
        }
        catch {
            state.storage = false;
            $('storage-note').textContent = 'Browser storage is full or unavailable. Export your progress to keep it.';
        }
    }
    renderHistory();
}
async function api(path, payload) { const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); const result = await response.json(); if (!response.ok)
    throw Error(result.error || 'Something went wrong. Try again.'); return result; }
function failure(fail) { error(fail instanceof TypeError ? 'Cannot reach the game server. Start python3 server.py and try again.' : fail.message); }
function renderWords() {
    let words = state.words.slice();
    const filter = $('word-filter').value;
    if (filter === 'found')
        words = words.filter(item => state.found.has(item.word));
    if (filter === 'missed')
        words = words.filter(item => !state.found.has(item.word));
    const sort = $('sort').value;
    words.sort((a, b) => sort === 'az' ? a.word.localeCompare(b.word) : sort === 'length' ? b.word.length - a.word.length || a.word.localeCompare(b.word) : b.score - a.score || a.word.localeCompare(b.word));
    $('words-total').textContent = `${words.length} WORD${words.length === 1 ? '' : 'S'}`;
    $('word-list').replaceChildren(...words.map(item => { const button = el('button', 'word-button' + (state.found.has(item.word) ? ' found' : '')); button.type = 'button'; button.setAttribute('aria-pressed', 'false'); button.setAttribute('aria-label', `${item.word}, ${item.score} points${state.found.has(item.word) ? ', found' : ''}`); button.append(el('span', '', item.word), el('small', '', `${state.found.has(item.word) ? '✓ ' : ''}${item.score}`)); button.addEventListener('click', () => { document.querySelectorAll('.word-button').forEach(b => b.setAttribute('aria-pressed', 'false')); button.setAttribute('aria-pressed', 'true'); showWord(item); }); return button; }));
    if (!words.length) {
        const empty = el('div', 'empty-words');
        empty.append(el('span', '', 'a b c'), el('p', '', state.active ? 'Your next word is waiting.' : state.revealed ? 'No words in this view.' : 'A fresh rack. A blank page.'), el('small', '', state.active ? 'Type a word above to get started.' : state.revealed ? 'Try another filter, rack, or minimum length.' : 'Your words will collect here as you play.'));
        $('word-list').append(empty);
    }
}
function showWord(item) {
    const detail = $('word-detail');
    detail.hidden = false;
    detail.replaceChildren(el('h4', '', `${item.word} · ${item.score} points`));
    const row = el('div', 'score-tiles');
    for (const tile of item.tiles) {
        const piece = el('span', 'score-tile' + (tile.blank ? ' blank' : ''), tile.letter);
        piece.append(el('small', '', `${tile.points}${tile.blank ? ' blank' : ''}`));
        row.append(piece);
    }
    detail.append(row, el('p', '', 'Real tiles score their letter value. A letter supplied by a blank scores zero.'));
}
function resetResults() { state.words = []; state.found = new Set(); state.revealed = false; $('word-detail').hidden = true; $('round-summary').hidden = true; $('word-toolbar').hidden = true; $('word-filter').value = 'all'; renderWords(); }
function setMode(mode, focus = false) { if (state.active || state.pending)
    return; for (const value of ['found', 'missed'])
    $('word-filter').querySelector(`[value=${value}]`).disabled = mode === 'solver'; state.mode = mode; state.version++; error(); resetResults(); for (const name of ['practice', 'solver']) {
    $(name + '-tab').setAttribute('aria-selected', String(mode === name));
    $(name + '-tab').tabIndex = mode === name ? 0 : -1;
} $('game-content').setAttribute('aria-labelledby', mode + '-tab'); $('practice-controls').hidden = mode !== 'practice'; $('solver-controls').hidden = mode !== 'solver'; $('duration').parentElement.hidden = mode === 'solver'; $('mode-caption').textContent = mode === 'practice' ? 'A LITTLE FRIENDLY PRESSURE' : 'LOOK AT YOUR LETTERS DIFFERENTLY'; $('board-title').textContent = mode === 'practice' ? 'How many words can you find?' : 'There’s more in your rack.'; $('board-copy').textContent = mode === 'practice' ? 'One rack. Your clock. All the words you can spot.' : 'Explore the possibilities, one good word at a time.'; $('words-title').textContent = mode === 'practice' ? 'Your discoveries' : 'The possibilities'; $('words-subtitle').textContent = mode === 'practice' ? 'Good words deserve a little space.' : 'Choose a word to see how its tiles add up.'; $('round-status').textContent = mode === 'practice' ? 'READY TO PLAY' : 'UNTIMED'; $('round-status').classList.remove('active'); feedback(mode === 'practice' ? 'No pressure to be perfect. Just make a start.' : 'Blank tiles can stand in for any missing letter.'); if (focus)
    $(mode + '-tab').focus(); }
function tick() { if (!state.active)
    return; const left = Math.max(0, Math.ceil((state.deadline - performance.now()) / 1000)); $('timer').textContent = formatTime(left); $('timer-fill').style.width = `${Math.min(100, left / state.round.seconds * 100)}%`; if (!left)
    finishRound(); }
function updateRound(result) { state.round = result; state.found = new Set(result.found.map(item => item.word)); state.words = result.found; $('score').replaceChildren(document.createTextNode(String(result.score)), el('small', '', 'pts')); $('found-count').textContent = result.found.length; renderWords(); }
function complete(result) { state.active = false; state.finishing = false; clearInterval(state.ticker); updateRound(result); state.revealed = true; state.words = result.solutions; $('word-toolbar').hidden = false; $('guess-form').hidden = true; $('finish').hidden = true; $('start').hidden = false; $('start').replaceChildren(document.createTextNode('Play another round '), el('span', '', '↗')); $('round-status').textContent = 'ROUND COMPLETE'; $('round-status').classList.remove('active'); $('timer').textContent = '0:00'; $('timer-fill').style.width = '0%'; $('round-summary').hidden = false; $('round-summary').textContent = `${result.score} points · ${result.found.length} of ${result.possible_words} possible words found. Explore the missed words below, then try another round.`; $('words-subtitle').textContent = 'Your finds are marked with a check. What will you spot next time?'; feedback('Round complete. Your progress is saved for this browser.'); remember(result); renderWords(); announce(`Round complete. ${result.score} points, ${result.found.length} words found.`); lock(); }
async function startRound() { if (state.active || state.pending)
    return; error(); state.pending = true; lock(); try {
    const result = await api('/api/round/start', { rack: rack(), seconds: Number($('duration').value), minimum: Number($('minimum').value) });
    resetResults();
    state.round = result;
    state.active = true;
    state.deadline = performance.now() + result.remaining * 1000;
    $('guess').value = '';
    $('guess-form').hidden = false;
    $('finish').hidden = false;
    $('start').hidden = true;
    $('round-status').textContent = 'ON THE CLOCK';
    $('round-status').classList.add('active');
    updateRound(result);
    feedback('You’re on. Find a word and press Enter.');
    state.ticker = setInterval(tick, 200);
    tick();
    $('guess').focus();
    announce('Round started. The clock is running.');
}
catch (fail) {
    failure(fail);
}
finally {
    state.pending = false;
    lock();
} }
async function guess(event) { event.preventDefault(); if (!state.active || state.pending || state.finishing)
    return; if (performance.now() >= state.deadline) {
    finishRound();
    return;
} error(); state.pending = true; lock(); try {
    const result = await api('/api/round/guess', { id: state.round.id, word: $('guess').value.trim().toLowerCase() });
    if (result.finished) {
        complete(result);
        return;
    }
    updateRound(result);
    feedback(result.message, result.accepted);
    if (result.accepted)
        $('guess').value = '';
    announce(result.message);
}
catch (fail) {
    failure(fail);
}
finally {
    state.pending = false;
    lock();
    if (state.active)
        $('guess').focus();
    if (state.finishAfter) {
        state.finishAfter = false;
        finishRound();
    }
} }
async function finishRound() { if (!state.active || state.finishing)
    return; if (state.pending) {
    state.finishAfter = true;
    return;
} state.finishing = true; lock(); try {
    const result = await api('/api/round/finish', { id: state.round.id });
    complete(result);
}
catch (fail) {
    failure(fail);
    state.finishing = false;
    clearInterval(state.ticker);
    $('submit-guess').disabled = true;
    feedback('Could not finish this round. Retry Finish round early before starting again.');
}
finally {
    lock();
} }
async function solveRack() { if (state.active || state.pending)
    return; const version = state.version; state.pending = true; lock(); error(); try {
    const result = await api('/api/solve', { rack: rack(), minimum: Number($('minimum').value) });
    if (version !== state.version)
        return;
    resetResults();
    state.words = result.words;
    state.revealed = true;
    $('word-toolbar').hidden = false;
    $('word-filter').querySelector('[value=found]').disabled = true;
    $('word-filter').querySelector('[value=missed]').disabled = true;
    renderWords();
    $('dictionary-note').textContent = `${result.dictionary_size} words in the selected dictionary. The included list is an original demo, not an official Scrabble list.`;
    feedback(`${result.words.length} possibilities found. Choose a word for its tile breakdown.`);
}
catch (fail) {
    failure(fail);
}
finally {
    state.pending = false;
    lock();
} }
function rackChanged() { state.version++; renderTiles(); resetResults(); error(); feedback('Rack updated. ' + (state.mode === 'practice' ? 'Start a round when you’re ready.' : 'Find words to explore this rack.')); }
$('rack').addEventListener('input', rackChanged);
$('minimum').addEventListener('change', rackChanged);
$('duration').addEventListener('change', () => { $('timer').textContent = formatTime(Number($('duration').value)); });
$('new-rack').addEventListener('click', () => { const choices = racks.filter(value => value !== rack()); $('rack').value = choices[Math.floor(Math.random() * choices.length)].toUpperCase(); rackChanged(); });
$('shuffle').addEventListener('click', () => { const letters = Array.from(rack()); for (let i = letters.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [letters[i], letters[j]] = [letters[j], letters[i]];
} renderTiles(letters.join('')); announce('Displayed tiles shuffled. Your rack is unchanged.'); });
$('practice-tab').addEventListener('click', () => { setMode('practice'); $('word-filter').querySelector('[value=found]').disabled = false; $('word-filter').querySelector('[value=missed]').disabled = false; });
$('solver-tab').addEventListener('click', () => setMode('solver'));
document.querySelector('.mode-tabs').addEventListener('keydown', event => { if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key))
    return; event.preventDefault(); setMode(event.key === 'Home' ? 'practice' : event.key === 'End' ? 'solver' : state.mode === 'practice' ? 'solver' : 'practice', true); });
$('start').addEventListener('click', startRound);
$('guess-form').addEventListener('submit', guess);
$('finish').addEventListener('click', finishRound);
$('solve').addEventListener('click', solveRack);
$('sort').addEventListener('change', renderWords);
$('word-filter').addEventListener('change', renderWords);
document.addEventListener('visibilitychange', () => { if (!document.hidden)
    tick(); });
$('export').addEventListener('click', () => { const url = URL.createObjectURL(new Blob([JSON.stringify(state.history, null, 2) + '\n'], { type: 'application/json' })); const link = el('a'); link.href = url; link.download = 'tile-club-progress.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); announce('Practice history exported as JSON.'); });
readHistory();
renderHistory();
renderTiles();
renderWords();
