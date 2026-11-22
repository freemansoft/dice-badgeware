# Bigger dice on the Badger: design

A small change to `2026-11-20-badger-and-saved-roll-design.md` (the
Badger's "Look" section). Where the two disagree, this one wins.

## Why

On the user's Badger the dice look much smaller than on the Tufty. They
are: the Tufty's die is 74 px (about 13 mm), the Badger's white die 38 px
(about 8 mm). The Badger gives each die a 54 px slot, but an 8 px band
inside it is kept for the locked die's grey box, on every die.

## Approaches

|                | Locked die                                             | Die size          | Trade-off                                                       |
| -------------- | ------------------------------------------------------ | ----------------- | --------------------------------------------------------------- |
| A              | Grey band inside the die's outline, round a white face | 54 px, face 38 px | Keeps "grey round white"; the number sits on a smaller face.    |
| B              | Thinner (4 px) grey box outside the die                | ~46 px            | Keeps the look exactly; the user found 4 px hard to see before. |
| **C (picked)** | The whole die is light grey, black number              | 54 px             | Biggest and simplest; drops the white-die-in-a-grey-box look.   |

The user picked C, as a trial: "or at least we can try c". If it doesn't
look right on the badge, A is the fallback.

## Design

- **Every die fills its slot:** 54 px across (twice `half` from
  `grid_slots`), black 2 px outline, as today.
- **Unlocked:** white face. **Locked:** light-grey face (160, 160, 160),
  the same shade the grey box used. Number and "d6" label black on both.
- **Highlight:** the same 3 px black ring, just outside the die (outer
  edge `half + 4`), in the gap between dice. It still clears the title
  bar and the line above the labels.
- **Text grows with the die**, in the Tufty's proportions: number 22 → 29,
  "d6" 9 → 10, the Setup screen's "d6" 16 → 19.
- **Unchanged:** layout, title bars, labels, the Tufty.

## Tests

The Badger simulator tests change with the look:

- a locked die's face reads light grey, an unlocked one's white;
- every die is at least 50 px across (was 38);
- the old "grey band at least 8 px" test goes.

The README's "grey box" line becomes "a locked die turns grey".

_Claude's calls:_ the font sizes, and keeping the ring at its old place.
