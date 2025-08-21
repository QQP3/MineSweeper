# Minesweeper in Python (Tkinter)

This project is a fully playable **Minesweeper game** built with Python and Tkinter.  
The game includes classic mechanics such as revealing squares, placing flags, and adjustable board size with difficulty settings.

Additionally, it features an **Auto Step** function that can assist the player by suggesting and performing safe moves based on logical deduction.

---

## Features
- 🎮 Classic Minesweeper gameplay  
- 🏆 Victory and game over detection  
- ⚙️ Adjustable rows, columns, and number of mines  
- 🔄 New game and reset options  
- 🤖 *Auto Step*: runs a single logical move (either flagging or revealing a cell)  

---

## Controls
- **Left click**: Reveal a cell  
- **Right click**: Place or remove a flag  
- **Apply button**: Apply new board settings (rows, columns, mines)  
- **New Game button**: Start a fresh game with current settings  
- **Auto Step button**: Automatically perform one move based on the current board state  

---

## Auto Step
The Auto Step logic analyzes the visible numbers and flags on the board.  
- If all mines around a number are already flagged, it will safely reveal the remaining neighbors.  
- If the number of unseen neighbors equals the number of remaining mines, it will flag them.  
- If no clear move exists, it will select one unseen square to reveal.  

---

## Requirements
- Python 3.x  
- Tkinter (comes bundled with most Python installations)

---

## Run the Game
```bash
python minesweeper.py
