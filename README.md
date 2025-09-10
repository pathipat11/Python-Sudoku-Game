# Python-Sudoku-Game

A classic and interactive Sudoku game built with Python and Pygame. Test your logic skills, fill the Sudoku grid, and try to complete puzzles in the fastest time possible.

## Features

* Multiple difficulty levels: Easy, Medium, Hard, Insane.
* Auto-generated puzzles with unique solutions.
* Real-time conflict checking for user inputs.
* Undo / Redo functionality.
* Notes mode to jot down possible numbers.
* Hints system with limited uses.
* Pause and resume game.
* Save and load game progress (3 save slots + autosave).
* Light and dark themes.
* Sound effects for typing, errors, and winning.
* Timer and fastest completion tracking.

## Installation

1. Clone the repository:

```bash
git clone https://github.com/pathipat11/Python-Sudoku-Game.git
```

2. Navigate to the project directory:

```bash
cd Python-Sudoku-Game
```

3. Install required packages:

```bash
pip install pygame
```

## Usage

1. Ensure the `assets` folder (sounds) is in the project directory.
2. Run the game:

```bash
python sudoku_game.py
```

3. Controls:

   * Arrow Keys: Move selection cursor
   * Number Keys (1-9): Fill selected cell
   * 0 / Delete / Backspace: Clear selected cell
   * N: Toggle Notes mode
   * H: Use hint
   * U: Undo
   * R: Redo
   * P: Pause / Resume
   * C: Toggle conflict check
   * T: Toggle theme (Light/Dark)
   * G: Start new game / Select difficulty
   * S: Auto-save
   * L: Load autosave
   * F1-F3: Save to slots 1-3
   * F8-F10: Load slots 1-3

4. Objective:

   Fill the 9x9 grid so that each row, column, and 3x3 box contains all numbers from 1 to 9 without repetition.

## 🎬 Demo Video

<img src="assets/videos/demo-Sudoku-Game.gif" alt="Sudoku Game Demo" width="540" height="350" />

## Contributing

Contributions are welcome! Submit a pull request or open an issue to suggest improvements or new features.

## Author

**Pathipat Mattra**

* 🌐 Facebook: [Pathipat Mattra](https://facebook.com/pathipat.mattra)
* 💻 GitHub: [pathipat11](https://github.com/pathipat11)
* 💼 LinkedIn: [Pathipat Mattra](https://linkedin.com/in/viixl)
