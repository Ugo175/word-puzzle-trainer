# Tile Club walkthrough

Start with `python3 server.py` and open the printed localhost URL. The game loads the original demo word list; no installation or external account is needed.

## A short practice session

The default rack is `REACT?`. The question mark supplies one missing letter in any submitted word and scores zero.

- `REACT` uses R, E, A, C, and T: **7 points**.
- A second `REACT` is a duplicate and adds nothing.
- `TREE` uses T, R, E, and a blank for the second E: **3 points**.
- `ZOO` cannot be made from the available tiles and is rejected.

Finish the round early. Those two valid words produce **10 points**. Open the Found words filter and select TREE to see the zero-point E in the breakdown. Missed words become available after the round; they are not shown during it.

![Completed practice and tile breakdown](desktop.jpg)

## Solver example

In Rack solver, use `QUI?`. QUIZ scores **12**: Q = 10, U = 1, I = 1, and blank Z = 0. It is not a 22-point word when the Z comes from a blank.

## Browser verification checklist

- Start a timed round; rack, duration, minimum length, and mode controls are locked.
- Submit REACT, duplicate REACT, TREE, and ZOO; verify the accepted/rejected messages and total of 10.
- Finish early; review Found words and Missed words and inspect TREE’s blank tile.
- Refresh; the completed round remains in the sidebar.
- Start a 30-second CAT round and let it expire; the round finishes without a manual click and saves once.
- Use the solver with QUI? and inspect QUIZ’s 12-point breakdown.
- Enter an invalid rack such as 123; see a useful error rather than stale solutions.
- Export progress; the JSON contains the completed rounds and their word lists.
- Test a narrow mobile viewport; tiles wrap inside the board and the document has no horizontal overflow.
- Check browser logs for errors during the verified flows.

## Mobile

[Open the full mobile screenshot](mobile.jpg).

## Automated tests

```sh
python3 -m unittest discover -s tests -v
```

The server deadline is tested with a fake clock, including a guess exactly at expiration. Further tests cover round isolation, duplicate scoring, zero-point blanks, validation, HTTP errors, and keeping the solver consistent with the original CLI implementation.

Screenshots show actual demonstration play during development. Browser history is local to the browser and is not bundled as sample user data in the repository.
