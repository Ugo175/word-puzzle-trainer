"""Shared solver reports and server-timed practice rounds."""
from collections import Counter
from datetime import datetime, timezone
import math
import secrets
import threading
import time

from trainer import POINTS, solve, validate_rack


def options(rack, minimum):
    validate_rack(rack)
    if isinstance(minimum, bool) or not isinstance(minimum, int) or not 1 <= minimum <= 12:
        raise ValueError('Minimum word length must be from 1 to 12.')


def tiles(word, rack):
    remaining = Counter(rack)
    result = []
    for letter in word:
        blank = not remaining[letter]
        if blank:
            remaining['?'] -= 1
        else:
            remaining[letter] -= 1
        result.append({'letter': letter, 'points': 0 if blank else POINTS[letter], 'blank': blank})
    return result


def solutions(rack, dictionary, minimum=2):
    options(rack, minimum)
    return [dict(item, tiles=tiles(item['word'], rack)) for item in solve(rack, dictionary)
            if len(item['word']) >= minimum]


class Rounds:
    """In-memory practice state; the server clock decides whether a guess counts."""
    def __init__(self, dictionary, clock=time.monotonic):
        self.dictionary = dictionary
        self.clock = clock
        self.rounds = {}
        self.lock = threading.Lock()

    def start(self, rack, seconds=60, minimum=2):
        options(rack, minimum)
        if isinstance(seconds, bool) or seconds not in (30, 60, 120) or not isinstance(seconds, int):
            raise ValueError('Choose a 30, 60, or 120 second round.')
        possible = solutions(rack, self.dictionary, minimum)
        if not possible:
            raise ValueError('No words match this rack and minimum length in the selected dictionary.')
        with self.lock:
            now = self.clock()
            self.rounds = {key: value for key, value in self.rounds.items() if now - value['started'] < 600}
            if len(self.rounds) >= 100:
                raise ValueError('Too many recent rounds. Try again in a few minutes.')
            identity = secrets.token_urlsafe(24)
            entry = {'id': identity, 'rack': rack, 'seconds': seconds, 'minimum': minimum,
                     'started': now, 'found': [], 'finished': False, 'solutions': possible}
            self.rounds[identity] = entry
            return self.view(entry)

    def view(self, entry):
        remaining = max(0, entry['seconds'] - (self.clock() - entry['started']))
        finished = entry['finished'] or remaining <= 0
        if finished:
            entry['finished'] = True
        result = {'id': entry['id'], 'rack': entry['rack'], 'seconds': entry['seconds'],
                  'minimum': entry['minimum'], 'remaining': math.ceil(remaining) if not finished else 0,
                  'finished': finished, 'found': entry['found'][:],
                  'score': sum(word['score'] for word in entry['found']),
                  'possible_words': len(entry['solutions'])}
        if finished:
            result['solutions'] = entry['solutions']
            result['missed'] = [word for word in entry['solutions']
                                if word['word'] not in {found['word'] for found in entry['found']}]
            if 'date' not in entry:
                entry['date'] = datetime.now(timezone.utc).isoformat()
            result['date'] = entry['date']
        return result

    def act(self, identity, word=None, finish=False):
        if not isinstance(identity, str):
            raise ValueError('A round ID is required.')
        with self.lock:
            if identity not in self.rounds:
                raise ValueError('This round is no longer available. Start a new round.')
            entry = self.rounds[identity]
            if finish:
                entry['finished'] = True
            result = self.view(entry)
            if result['finished']:
                return dict(result, message='Round complete. Review the words you missed.')
            if not isinstance(word, str) or not word or len(word) > 12 or any(c not in POINTS for c in word):
                raise ValueError('Enter a word using lowercase ASCII letters.')
            if word in {found['word'] for found in entry['found']}:
                return dict(result, accepted=False, message='You already found that word.')
            match = next((item for item in entry['solutions'] if item['word'] == word), None)
            if match is None:
                return dict(result, accepted=False, message='That word does not fit this rack, dictionary, or minimum length.')
            entry['found'].append(match)
            return dict(self.view(entry), accepted=True, message=f"+{match['score']} points. Nice find!")
