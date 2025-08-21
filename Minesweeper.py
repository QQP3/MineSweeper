"""
Minesweeper game with optional AutoPlay solver.
All numbers and bombs in blue, board size adjustable with difficulty settings.
"""

import tkinter as tk
from tkinter import messagebox
import random

# Import solver
from Minesweeper_AutoPlay import solution, UNSEEN, FLAGGED

class Board:
    MINE = -1

    def __init__(self, rows=20, cols=20, mines=80):
        self.rows = rows
        self.cols = cols
        self.mines_count = mines
        self.reset()

    def reset(self):
        self.mines = set()
        self.revealed = [[False]*self.cols for _ in range(self.rows)]
        self.flagged = [[False]*self.cols for _ in range(self.rows)]
        self.board = [[0]*self.cols for _ in range(self.rows)]
        self.placed = False
        self.game_over = False
        self.victory = False

    def in_bounds(self, r, c):
        return 0 <= r < self.rows and 0 <= c < self.cols

    def neighbors(self, r, c):
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if self.in_bounds(nr, nc):
                    yield nr, nc

    def place_mines(self, safe_r, safe_c):
        cells = [(r,c) for r in range(self.rows) for c in range(self.cols)]
        safe_zone = {(safe_r, safe_c)} | set(self.neighbors(safe_r, safe_c))
        available = [pos for pos in cells if pos not in safe_zone]
        self.mines = set(random.sample(available, self.mines_count))
        for r,c in self.mines:
            self.board[r][c] = self.MINE
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] == self.MINE:
                    continue
                count = sum(1 for nr,nc in self.neighbors(r,c) if (nr,nc) in self.mines)
                self.board[r][c] = count
        self.placed = True

    def reveal(self, r, c):
        if self.game_over or self.flagged[r][c] or self.revealed[r][c]:
            return
        if not self.placed:
            self.place_mines(r, c)
        if (r,c) in self.mines:
            self.revealed[r][c] = True
            self.game_over = True
            self.victory = False
            return
        stack = [(r,c)]
        while stack:
            cr, cc = stack.pop()
            if self.revealed[cr][cc]:
                continue
            self.revealed[cr][cc] = True
            if self.board[cr][cc] == 0:
                for nr, nc in self.neighbors(cr, cc):
                    if not self.revealed[nr][nc] and not self.flagged[nr][nc]:
                        stack.append((nr, nc))
        self.check_victory()

    def toggle_flag(self, r, c):
        if self.game_over or self.revealed[r][c]:
            return
        self.flagged[r][c] = not self.flagged[r][c]
        self.check_victory()

    def check_victory(self):
        if self.game_over:
            return
        revealed_count = sum(1 for r in range(self.rows) for c in range(self.cols) if self.revealed[r][c])
        if revealed_count == self.rows * self.cols - self.mines_count:
            self.game_over = True
            self.victory = True

class MinesweeperGUI:
    def __init__(self, master):
        self.master = master
        self.rows = 20
        self.cols = 20
        self.mines = 80
        self.board = Board(self.rows, self.cols, self.mines)
        self.buttons = []
        self.build_ui()

    def build_ui(self):
        top = tk.Frame(self.master)
        top.pack()
        tk.Button(top, text='New Game', command=self.new_game).pack(side=tk.LEFT)
        tk.Label(top, text='Rows:').pack(side=tk.LEFT)
        self.rows_entry = tk.Entry(top, width=3)
        self.rows_entry.insert(0, str(self.rows))
        self.rows_entry.pack(side=tk.LEFT)
        tk.Label(top, text='Cols:').pack(side=tk.LEFT)
        self.cols_entry = tk.Entry(top, width=3)
        self.cols_entry.insert(0, str(self.cols))
        self.cols_entry.pack(side=tk.LEFT)
        tk.Label(top, text='Mines:').pack(side=tk.LEFT)
        self.mines_entry = tk.Entry(top, width=4)
        self.mines_entry.insert(0, str(self.mines))
        self.mines_entry.pack(side=tk.LEFT)
        tk.Button(top, text='Apply', command=self.apply_settings).pack(side=tk.LEFT)
        tk.Button(top, text='AI Step', command=self.autoplay_step).pack(side=tk.LEFT)

        self.board_frame = tk.Frame(self.master)
        self.board_frame.pack()
        self.draw_board()

    def draw_board(self):
        for widget in self.board_frame.winfo_children():
            widget.destroy()
        self.buttons = [[None]*self.cols for _ in range(self.rows)]
        for r in range(self.rows):
            for c in range(self.cols):
                b = tk.Button(self.board_frame, width=2, height=1,
                              command=lambda r=r, c=c: self.left_click(r, c))
                b.bind('<Button-3>', lambda e, r=r, c=c: self.right_click(r, c))
                b.grid(row=r, column=c)
                self.buttons[r][c] = b
        self.update_ui()

    def new_game(self):
        self.board = Board(self.rows, self.cols, self.mines)
        self.draw_board()

    def apply_settings(self):
        try:
            self.rows = int(self.rows_entry.get())
            self.cols = int(self.cols_entry.get())
            self.mines = int(self.mines_entry.get())
        except ValueError:
            messagebox.showerror('Error', 'Invalid settings')
            return
        self.new_game()

    def left_click(self, r, c):
        self.board.reveal(r, c)
        self.update_ui()
        if self.board.game_over:
            self.end_game()

    def right_click(self, r, c):
        self.board.toggle_flag(r, c)
        self.update_ui()
        if self.board.game_over:
            self.end_game()

    def update_ui(self):
        for r in range(self.rows):
            for c in range(self.cols):
                btn = self.buttons[r][c]
                if self.board.revealed[r][c]:
                    val = self.board.board[r][c]
                    if (r, c) in self.board.mines:
                        btn.config(text='*', relief=tk.SUNKEN, state=tk.DISABLED, fg="blue")
                    elif val == 0:
                        btn.config(text='', relief=tk.SUNKEN, state=tk.DISABLED)
                    else:
                        btn.config(text=str(val), relief=tk.SUNKEN, state=tk.DISABLED, fg="blue")
                else:
                    if self.board.flagged[r][c]:
                        btn.config(text='F')
                    else:
                        btn.config(text='')
        self.master.update_idletasks()

    def end_game(self):
        for r in range(self.rows):
            for c in range(self.cols):
                self.board.revealed[r][c] = True
        self.update_ui()
        if self.board.victory:
            messagebox.showinfo('Victory', 'You won!')
        else:
            messagebox.showinfo('Game Over', 'You hit a mine!')

    # === AutoPlay integration ===
    def get_solver_board(self):
        solver_board = []
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                if self.board.flagged[r][c]:
                    row.append(FLAGGED)
                elif not self.board.revealed[r][c]:
                    row.append(UNSEEN)
                else:
                    val = self.board.board[r][c]
                    if val == self.board.MINE:
                        row.append('*')
                    else:
                        row.append(str(val))
            solver_board.append(row)
        return solver_board

    def autoplay_step(self):
        solver_board = self.get_solver_board()
        try:
            action, coords = solution(solver_board, self.rows, self.cols)
        except Exception as e:
            messagebox.showinfo("AutoPlay", str(e))
            return

        for (r, c) in coords:
            if action == 0:
                self.board.reveal(r, c)
            elif action == 1:
                self.board.toggle_flag(r, c)

        self.update_ui()
        if self.board.game_over:
            self.end_game()

if __name__ == '__main__':
    root = tk.Tk()
    root.title('Minesweeper')
    game = MinesweeperGUI(root)
    root.mainloop()

