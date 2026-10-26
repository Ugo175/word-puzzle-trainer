#!/usr/bin/env python3
"""Solve letter racks and practice timed word challenges with local progress."""
import argparse
from collections import Counter
import json
from pathlib import Path
import random
import string
import time

POINTS = dict(zip(string.ascii_lowercase,
                  [1, 3, 3, 2, 1, 4, 2, 4, 1, 8, 5, 1, 3, 1, 1, 3, 10, 1, 1, 1, 1, 4, 4, 8, 4, 10]))
DEFAULT_DICTIONARY = Path(__file__).with_name('words.txt')


def load_words(path):
    entries = path.read_text(encoding='utf-8').splitlines()
    result = {word.strip().lower() for word in entries if word.strip()}
    if not result or any(any(letter not in POINTS for letter in word) for word in result):
        raise ValueError('Dictionary must contain ASCII words, one per line.')
    return result


def validate_rack(rack):
    if not rack or any(letter not in POINTS and letter != '?' for letter in rack):
        raise ValueError('Rack must contain ASCII letters or ? for blank tiles.')


def score(word, rack):
    available = Counter(rack)
    value = 0
    for letter in word:
        if letter not in POINTS:
            return None
        if available[letter]:
            available[letter] -= 1
            value += POINTS[letter]
        elif available['?']:
            available['?'] -= 1
        else:
            return None
    return value


def solve(rack, dictionary):
    validate_rack(rack)
    results = [{'word': word, 'score': score(word, rack)} for word in dictionary]
    return sorted((item for item in results if item['score'] is not None),
                  key=lambda item: (-item['score'], item['word']))


def save_progress(path, record):
    history = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    if not isinstance(history, list):
        raise ValueError('Progress file must contain a JSON list.')
    history.append(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replace avoids a partially written history if the process stops mid-write.
    import tempfile
    import os
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         delete=False) as destination:
            temporary = destination.name
            json.dump(history, destination, indent=2)
            destination.write('\n')
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def practice(rack, dictionary, seconds, progress):
    solutions = {item['word']: item['score'] for item in solve(rack, dictionary)}
    if not solutions:
        raise ValueError('This rack has no words in the selected dictionary.')
    print(f'Rack: {rack.upper()} | {seconds}s | Enter one word per line; blank ends the round.')
    found = set()
    started = time.monotonic()
    while True:
        try:
            answer = input('Word: ').strip().lower()
        except EOFError:
            break
        if time.monotonic() - started > seconds:
            print('Time expired; that answer does not count.')
            break
        if not answer:
            break
        if answer in found:
            print('Already found.')
        elif answer in solutions:
            found.add(answer)
            print(f'+{solutions[answer]} points')
        else:
            print('Not a valid word for this rack and dictionary.')
    record = {'date': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'rack': rack,
              'seconds': seconds, 'words': sorted(found),
              'score': sum(solutions[word] for word in found), 'possible_words': len(solutions)}
    save_progress(progress, record)
    print(json.dumps(record, indent=2))
    print('Missed: ' + ', '.join(sorted(set(solutions) - found)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['solve', 'practice', 'stats'])
    parser.add_argument('--rack', help='Letters plus optional ? blanks')
    parser.add_argument('--dictionary', type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument('--seconds', type=int, default=60)
    parser.add_argument('--progress', type=Path, default=Path.home() / '.word-puzzle-trainer.json')
    args = parser.parse_args()
    if args.seconds < 1:
        parser.error('--seconds must be positive')
    try:
        if args.mode == 'stats':
            records = json.loads(args.progress.read_text(encoding='utf-8')) if args.progress.exists() else []
            if not isinstance(records, list) or any(not isinstance(r, dict) or not isinstance(r.get('score'), int) for r in records):
                raise ValueError('Invalid progress history.')
            print(json.dumps({'rounds': len(records), 'best_score': max((r['score'] for r in records), default=0),
                              'total_score': sum(r['score'] for r in records)}, indent=2))
            return
        dictionary = load_words(args.dictionary)
        rack = args.rack.lower() if args.rack else random.choice(sorted(dictionary))
        validate_rack(rack)
        if args.mode == 'solve':
            print(json.dumps(solve(rack, dictionary), indent=2))
        else:
            practice(rack, dictionary, args.seconds, args.progress)
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(2, f'Error: {error}\n')


if __name__ == '__main__':
    main()
