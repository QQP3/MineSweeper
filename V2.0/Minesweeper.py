"""
Minesweeper game with optional AutoPlay solver + JSON logging (single-file).
- Auto Step (one step) or AutoPlay (continuous) using your solver
- Logs each step to autoplay_log.jsonl (one JSON object per line)
- Optional gzip compression of the log
"""

import tkinter as tk
from tkinter import messagebox
import random, json, gzip, os
from datetime import datetime, UTC
from Minesweeper_AI import MinesweeperAITrainer as aimoudel
from General_variables import *

# ============================================================
# Try to use your solver; fall back to a dummy one if missing
# Expects: solution(board:str-matrix, rows:int, cols:int) -> (action:int, coords:list[(r,c)])
# Where action=0 means reveal; action=1 means flag
# Cell codes for solver input:
#   UNSEEN -> '#', FLAGGED -> 'F', revealed mines -> '*', revealed numbers -> '0'..'8'
# ============================================================


try:
    # Your solver module (keep this if you have it)
    from Minesweeper_AutoPlay import solution as external_solution

    def solution_adapter(solver_board, rows, cols):
        return external_solution(solver_board, rows, cols)

except Exception as e:
    print(e)
    # Minimal fallback so app still runs without your solver
    def solution_adapter(solver_board, rows, cols):
        """
        Dummy solver:
        - If there’s any flagged cell adjacent to obvious 0s, try reveals around zeros.
        - Otherwise, pick a random UNSEEN cell to reveal.
        """
        unseen = []
        for r in range(rows):
            for c in range(cols):
                if solver_board[r][c] == UNSEEN:
                    unseen.append((r, c))
        if not unseen:
            raise RuntimeError("No moves available.")

        # naive: reveal a random unseen cell
        return 0, [random.choice(unseen)]
    


# ============================================================
# Game logic
# ============================================================
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

# ============================================================
# GUI + AutoPlay + Logging
# ============================================================
class MinesweeperGUI:
    def __init__(self, master):
        self.master = master
        self.rows = 20
        self.cols = 20
        self.mines = 80
        self.board = Board(self.rows, self.cols, self.mines)
        self.buttons = []
        self.game_id = 0
        self.step_index = 0
        self.autoplay_running = False
        self.aiplay_running = False
        self.autoplay_delay_ms = 0   # continuous autoplay delay per step
        self.aiplay_delay_ms = 10
        self.log_path = "autoplay_log.jsonl"
        self.log_compress_on_rotate = True
        self.rotate_threshold_mb = 100  # rotate+compress if file grows beyond this
        self.ai = aimoudel(self.rows, self.cols)

        self.build_ui()

    # ---------- UI ----------
    def build_ui(self):
        top = tk.Frame(self.master)
        top.pack(pady=4)
        bottom = tk.Frame(self.master)
        bottom.pack(side=tk.BOTTOM, pady=6)
        
        tk.Button(top, text='New Game', command=self.new_game).pack(side=tk.LEFT, padx=2)
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
        tk.Button(top, text='Apply', command=self.apply_settings).pack(side=tk.LEFT, padx=2)

        tk.Button(top, text='Auto Step', command=self.autoplay_step).pack(side=tk.LEFT, padx=6)
        self.autoplay_btn = tk.Button(top, text='Start AutoPlay', command=self.toggle_autoplay)
        self.autoplay_btn.pack(side=tk.LEFT, padx=2)

        tk.Button(bottom, text='AI Step', command=self.ai_step).pack(side=tk.LEFT, padx=6)
        self.aiplay_btn = tk.Button(bottom, text='Start AIPlay', command=self.toggle_aiplay)
        self.aiplay_btn.pack(side=tk.LEFT, padx=2)

        self.compress_btn = tk.Button(top, text='Compress Log', command=self.compress_log)
        self.compress_btn.pack(side=tk.LEFT, padx=6)

        self.board_frame = tk.Frame(self.master)
        self.board_frame.pack(pady=4)
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
        self.game_id += 1
        self.step_index = 0
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
                        btn.config(text=BOMB, relief=tk.SUNKEN, state=tk.DISABLED, fg="blue")
                    elif val == 0:
                        btn.config(text='', relief=tk.SUNKEN, state=tk.DISABLED)
                    else:
                        btn.config(text=str(val), relief=tk.SUNKEN, state=tk.DISABLED, fg="blue")
                else:
                    if self.board.flagged[r][c]:
                        btn.config(text=FLAGGED)
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
        # Stop autoplay if it was running
        self.autoplay_running = False
        self.autoplay_btn.config(text='Start AutoPlay')

    # ---------- Solver I/O ----------
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
                        row.append(BOMB)
                    else:
                        row.append(str(val))
            solver_board.append(row)
        return solver_board

    # ---------- Logging ----------
    def _log_rotate_if_needed(self):
        if DISABLE_LOG:
            return
        
        try:
            if not os.path.exists(self.log_path):
                return
            size_mb = os.path.getsize(self.log_path) / (1024*1024)
            if size_mb >= self.rotate_threshold_mb:
                base = os.path.splitext(self.log_path)[0]
                ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                rotated = f"{base}.{ts}.jsonl"
                os.rename(self.log_path, rotated)
                if self.log_compress_on_rotate:
                    with open(rotated, "rb") as fin, gzip.open(rotated + ".gz", "wb") as fout:
                        fout.writelines(fin)
                    os.remove(rotated)
        except Exception as e:
            # non-fatal
            print("Log rotation error:", e)

    def log_step(self, solver_board, action, coords, ok=True, error=None):
        if DISABLE_LOG:
            return 
        
        rec = {
            "timestamp": datetime.now(UTC).isoformat(),
            "game_id": self.game_id,
            "step_index": self.step_index,
            "rows": self.rows,
            "cols": self.cols,
            "mines": self.mines,
            "solver_board": solver_board,
            "action": action,
            "coords": coords,
            "result_ok": bool(ok),
            "error": str(error) if error else None
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception as e:
            print("Log write error:", e)
        self._log_rotate_if_needed()

    def compress_log(self):
        if DISABLE_LOG:
            return
        
        try:
            if not os.path.exists(self.log_path):
                messagebox.showinfo("Compress Log", "No log file found.")
                return
            gz_path = self.log_path + ".gz"
            with open(self.log_path, "rb") as fin, gzip.open(gz_path, "wb") as fout:
                fout.writelines(fin)
            messagebox.showinfo("Compress Log", f"Compressed to: {gz_path}")
        except Exception as e:
            messagebox.showerror("Compress Log", str(e))

    # ---------- AutoPlay ----------
    def autoplay_step(self):
        if self.board.game_over:
            self.end_game()
            return

        solver_board = self.get_solver_board()
        try:
            action, coords = solution_adapter(solver_board, self.rows, self.cols)
        except Exception as e:
            # Log failure and show the message
            self.log_step(solver_board, action=None, coords=None, ok=False, error=e)
            messagebox.showinfo("AutoPlay", str(e))
            return

        # Apply moves
        r, c = coords[0]
        if action == REVEAL:
            self.board.reveal(r, c)
        elif action == FLAG:
            self.board.toggle_flag(r, c)

        self.step_index += 1
        self.update_ui()
        if self.board.game_over:
            if not AUTOPLAY_LOOP_FOR_EVER:
                self.end_game()
                return
        else:
            # Log the successful solver output BEFORE applying to board
            self.log_step(solver_board, action=action, coords=coords[0], ok=True)

            
    def toggle_autoplay(self):
        self.autoplay_running = not self.autoplay_running
        self.autoplay_btn.config(text='Stop AutoPlay' if self.autoplay_running else 'Start AutoPlay')
        if self.autoplay_running:
            self._autoplay_loop()

    def _autoplay_loop(self):
        
        if not self.autoplay_running:
            return
        
        # Do one step
        self.autoplay_step()
        
        if self.board.game_over:
            if AUTOPLAY_LOOP_FOR_EVER:
                self.new_game()
                self.board.reveal(self.rows // 2, self.cols // 2)
            else:
                self.end_game()
                self.toggle_autoplay()
                return

        
        # Schedule next
        if self.autoplay_running and not self.board.game_over:
            self.master.after(self.autoplay_delay_ms, self._autoplay_loop)
    
    # ---------- AIPlay ----------
    def correct_step(self,solver_board, mboxstr = "", do_not_disturb = False):
        try:
            correct_action, correct_coords = solution_adapter(solver_board, self.rows, self.cols)
            return (correct_action, correct_coords)
        except Exception as e:
            if not do_not_disturb:
                # Log failure and show the message
                self.log_step(solver_board, action=None, coords=None, ok=False, error=e)
                messagebox.showinfo(mboxstr, str(e))
            return (-1, -1)

    def ai_step(self):
        if self.board.game_over:
            self.end_game()
            return

        solver_board = self.get_solver_board()
        try:
            self.ai.input_board(solver_board)
            action, coords = self.ai.make_guess()
        except Exception as e:
            messagebox.showinfo("AIPlay:", str(e))
            return
        
        r, c = coords

        # Check move
        if self.board.revealed[r][c]:
            self.log_step(solver_board, action=action, coords=coords, ok=False, error="The coordinates given is already revealed!!")
            correct_action, correct_coords = self.correct_step(solver_board=solver_board, mboxstr = "AI Failed Correct Action:")
            if correct_coords == -1:
                return
            
            cr, cc = correct_coords[0]
            if correct_action == REVEAL:
                self.board.reveal(cr, cc)
            elif correct_action == FLAG:
                self.board.toggle_flag(cr, cc)
            
            self.step_index += 1
            self.update_ui()
        
            if self.board.game_over:
                if self.board.check_victory():
                    print(1)
                    self.ai.adjust_based_on_feedback(correct = False, correct_action = correct_action, correct_coord = (cr, cc), penalty = PENALTY_HIGH)
                                
                if not AIPLAY_LOOP_FOR_EVER:
                    self.end_game()
                    return
            else:
                print(correct_action, (cr, cc))
                self.ai.adjust_based_on_feedback(correct = False, correct_action = correct_action, correct_coord = (cr, cc), penalty = PENALTY_HIGH)
                self.log_step(solver_board, action=action, coords=coords[0], ok=True)
            return

        if action == FLAG and self.board.board[r][c] != self.board.MINE:
            self.ai.adjust_based_on_feedback(correct=False, correct_action=REVEAL, correct_coord=coords, penalty = PENALTY_MID)
            print(3)
            return
            
        if self.board.flagged[r][c]:
            correct_action, correct_coords = self.correct_step(solver_board = solver_board, mboxstr="AI Failed Correct Action:")
            if correct_coords == -1:
                return
            cr, cc = correct_coords[0]
            if correct_action == REVEAL:
                self.board.reveal(cr, cc)
            elif correct_action == FLAG:
                self.board.toggle_flag(cr, cc)
            
            self.step_index += 1
            self.update_ui()

            if self.board.game_over:
                if self.board.check_victory():
                    self.ai.adjust_based_on_feedback(correct = False, correct_action = correct_action, correct_coord = (cr, cc), penalty = PENALTY_HIGH)
                    print(4)             
                if not AIPLAY_LOOP_FOR_EVER:
                    self.end_game()
                    return
            else:
                self.ai.adjust_based_on_feedback(correct = False, correct_action = correct_action, correct_coord = (cr, cc), penalty = PENALTY_HIGH)
                self.log_step(solver_board, action=action, coords=coords[0], ok=True)
                print(5)
            return
        # End of check
        
        correct_action, correct_coords = self.correct_step(solver_board = solver_board, do_not_disturb = True)
        if correct_coords == -1:
            correct_action = None
            correct_coords = None
        
        if action == REVEAL:
            self.board.reveal(r, c)
        elif action == FLAG:
            self.board.toggle_flag(r, c)

        self.step_index += 1
        self.update_ui()

        if self.board.game_over:
            if self.board.check_victory():
                self.ai.adjust_based_on_feedback(correct = True)
            elif correct_action != None and correct_coords != None:
                solver_board = self.get_solver_board()
                cr, cc = correct_coords[0]
                if solver_board[cr][cc] != BOMB:
                    self.ai.adjust_based_on_feedback(correct = False, correct_action = correct_action, correct_coord = (cr, cc))
                    print(6)
            if not AIPLAY_LOOP_FOR_EVER:
                self.end_game()
                return
        else:
            self.ai.adjust_based_on_feedback(correct = True)
            self.log_step(solver_board, action=action, coords=coords, ok=True)
            print(8)


    def toggle_aiplay(self):
        self.aiplay_running = not self.aiplay_running
        self.aiplay_btn.config(text='Stop AIPlay' if self.aiplay_running else 'Start AIPlay')
        if self.aiplay_running:
            self._aiplay_loop()

    def _aiplay_loop(self):
         
        if not self.aiplay_running:
            return
        
        # Do one step
        self.ai_step()
        
        if self.board.game_over:
            if AIPLAY_LOOP_FOR_EVER:
                self.new_game()
            else:
                self.end_game()
                self.toggle_aiplay()
                return

        
        # Schedule next
        if self.aiplay_running and not self.board.game_over:
            self.master.after(self.aiplay_delay_ms, self._aiplay_loop)


# ============================================================
# Run
# ============================================================
if __name__ == '__main__':
    root = tk.Tk()
    root.title('Minesweeper (AutoPlay + Logging)')
    game = MinesweeperGUI(root)
    root.mainloop()

