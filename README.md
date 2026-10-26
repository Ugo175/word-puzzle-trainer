# Word Puzzle Trainer

Find playable words from a letter rack, practice timed challenges, and track local scores. Tile values follow the letter values used in the CS50 Scrabble exercise; blank tiles score zero.

## Run

```sh
python3 trainer.py solve --rack 'react?'
python3 trainer.py practice --rack react --seconds 60 --progress progress.json
python3 trainer.py stats --progress progress.json
python3 trainer.py solve --rack example --dictionary /path/to/your/words.txt
```

A small original demonstration dictionary is included. It is deliberately not a complete or official Scrabble dictionary. Bring a larger UTF-8 word list with one ASCII word per line for broader play. Dictionary paths may be absolute or relative to your working directory. Without `--rack`, a word from the dictionary provides a solvable rack.

During practice enter one word per line. Duplicate answers score once. Enter a blank line to finish early. Because terminal input blocks, the time limit is checked when you submit an answer; submissions after the deadline are rejected. Missed words appear after the round. The default history file is `~/.word-puzzle-trainer.json`; `--progress` lets you keep it elsewhere. History updates use atomic replacement but do not support concurrent writers.

Scores are rack-only sums: no board multipliers or seven-tile bonus. A blank can replace a missing letter; the output score reflects this. Progress files are personal data and excluded from Git by default.

## Next steps

Add a browser countdown, tile-level score explanations, difficulty selection, and personal bests by rack.

## Verification

```sh
python3 -m unittest discover -s tests -v
```

Requires Python 3.9+; no third-party packages or API keys.

## Origins

Inspired by Ugochukwu Igweagu’s CS50 coursework in [the projects collection](https://github.com/Ugo175/projects). This is a new standalone implementation with additional functionality, not a copy of CS50 starter files. See [ATTRIBUTION.md](ATTRIBUTION.md).
