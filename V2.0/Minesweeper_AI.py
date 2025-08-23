import torch
import torch.nn as nn
import torch.optim as optim
import os
import json
import gzip
from General_variables import *

class MinesweeperAITrainer:
    def __init__(self, board_rows=5, board_cols=5, lr=0.01, model_file="minesweeper_ai.pt", autosave=True):
        self.board_rows = board_rows
        self.board_cols = board_cols
        self.input_size = board_rows * board_cols
        self.model_file = model_file
        self.lr = lr
        self.autosave = autosave

        # Member variables
        self.board = None
        self.action = None
        self.coord = None
        self.correct = None
        self.training_steps = 0  # Track training steps

        # Build model
        self._build_model()

        # Try loading saved model automatically
        self.load_model()

    # ----------------- Build Model -----------------
    def _build_model(self):
        self.shared = nn.Sequential(
            nn.Linear(self.input_size, 768),   # was 1024 → changed to match your input
            nn.ReLU(),
            nn.Linear(768, 640),
            nn.ReLU(),
            nn.Linear(640, 512),
            nn.ReLU(),
            nn.Linear(512, 384),
            nn.ReLU(),
            nn.Linear(384, 256),
            nn.ReLU()
            
        )
        self.action_head = nn.Linear(256, 2)                     # Reveal / Flag
        self.coord_head = nn.Linear(256, self.board_rows*self.board_cols)  # Cell index

        self.criterion_action = nn.CrossEntropyLoss()
        self.criterion_coord = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(self.parameters(), lr=self.lr)

    def parameters(self):
        return list(self.shared.parameters()) + list(self.action_head.parameters()) + list(self.coord_head.parameters())

    # ----------------- Encode board -----------------
    def encode_board(self, board):
        mapping = {UNSEEN: 0, FLAGGED: -1, BOMB: -2}
        flat = []
        for row in board:
            for cell in row:
                if cell in mapping:
                    flat.append(mapping[cell])
                else:
                    try:
                        flat.append(int(cell))
                    except:
                        flat.append(0)
        return flat

    # ----------------- 1. Input the board -----------------
    def input_board(self, board):
        self.board = board

    # ----------------- 2. Make a guess -----------------
    def make_guess(self):
        if self.board is None:
            print("Board is not set. Please input the board first.")
            return

        x = self.encode_board(self.board)
        x_tensor = torch.tensor([x], dtype=torch.float32)

        with torch.no_grad():
            features = self.shared(x_tensor)
            action_logits = self.action_head(features)
            coord_logits = self.coord_head(features)

            action_idx = torch.argmax(action_logits, dim=1).item()
            coord_idx = torch.argmax(coord_logits, dim=1).item()

        self.action = REVEAL if action_idx == 0 else FLAG
        self.coord = (coord_idx // self.board_cols, coord_idx % self.board_cols)

        print(f"AI guesses: {self.action} at {self.coord}")
        return (self.action, self.coord)

    # ----------------- 3. Adjust based on results -----------------
    def adjust_based_on_feedback(self, correct: bool, correct_coord=None, correct_action=None, penalty: float = 1.0):
        if self.board is None or self.action is None or self.coord is None:
            print("Board or guess not set. Please run previous steps first.")
            return
        self.correct = correct

        if correct:
            true_action = 0 if self.action == REVEAL else 1
            true_coord = self.coord[0] * self.board_cols + self.coord[1]
        elif correct_action != None and correct_coord != None:
            true_action = 0 if correct_action == REVEAL else 1
            true_coord = correct_coord[0] * self.board_cols + correct_coord[1]
        else:
            return  # nothing to train on if we don’t know truth

        # Training step
        x = self.encode_board(self.board)
        x_tensor = torch.tensor([x], dtype=torch.float32)
        y_action = torch.tensor([true_action], dtype=torch.long)
        y_coord = torch.tensor([true_coord], dtype=torch.long)

        self.optimizer.zero_grad()
        features = self.shared(x_tensor)
        action_logits = self.action_head(features)
        coord_logits = self.coord_head(features)

        loss_a = self.criterion_action(action_logits, y_action)
        loss_c = self.criterion_coord(coord_logits, y_coord)
        loss = loss_a + loss_c

        # Apply penalty if mistake
        if not correct and penalty != 1.0:
            loss = penalty * loss

        loss.backward()
        self.optimizer.step()

        self.training_steps += 1

        # Auto-save model
        if self.autosave and self.training_steps % 10 == 0:
            self.save_model()
            print(f"Model autosaved at step {self.training_steps}")

        print(f"correct = {correct}")
        print(f"Trained on this sample. Loss: {loss.item():.4f}")

        # Reset after adjustment 
        self.board = None
        self.action = None
        self.coord = None

    # ----------------- Save / Load -----------------
    def save_model(self):
        state = {
            "shared": self.shared.state_dict(),
            "action_head": self.action_head.state_dict(),
            "coord_head": self.coord_head.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "rows": self.board_rows,
            "cols": self.board_cols,
            "steps": self.training_steps
        }
        torch.save(state, self.model_file)
        print(f"Model saved to {self.model_file}")

    def load_model(self):
        if os.path.exists(self.model_file):
            state = torch.load(self.model_file)
            if state.get("rows") == self.board_rows and state.get("cols") == self.board_cols:
                self.shared.load_state_dict(state["shared"])
                self.action_head.load_state_dict(state["action_head"])
                self.coord_head.load_state_dict(state["coord_head"])
                self.optimizer.load_state_dict(state["optimizer"])
                self.training_steps = state.get("steps", 0)
                print(f"Model loaded from {self.model_file}, step {self.training_steps}")
            else:
                print("Board size changed. Starting with new model.")
    
    def pretrain_from_json(self, json_path = "autoplay_log.jsonl.gz", epochs=5):
        dataset = []
        with gzip.open(json_path, "rt", encoding="utf-8") as f:
            dataset = [json.loads(line) for line in f]
        
        print(f"Loaded {len(dataset)} training samples from {json_path}")

        for epoch in range(epochs):
            total_loss = 0.0
            for sample in dataset:
                board = sample["solver_board"]
                action = sample["action"]
                coord = tuple(sample["coords"])

                if not bool(sample["result_ok"]):
                    continue

                # Encode board
                x = self.encode_board(board)
                x_tensor = torch.tensor([x], dtype=torch.float32)

                # Encode labels
                true_action = 1 if action == FLAG else 0
                if type(coord) == list:
                    true_coord = coord[0][0] * self.board_cols + coord[0][1]
                else:
                    true_coord = coord[0] * self.board_cols + coord[1]
                y_action = torch.tensor([true_action], dtype=torch.long)
                y_coord = torch.tensor([true_coord], dtype=torch.long)

                # Train step
                self.optimizer.zero_grad()
                features = self.shared(x_tensor)
                action_logits = self.action_head(features)
                coord_logits = self.coord_head(features)

                loss_a = self.criterion_action(action_logits, y_action)
                loss_c = self.criterion_coord(coord_logits, y_coord)
                loss = loss_a + loss_c

                loss.backward()
                self.optimizer.step()

                total_loss += loss.item()

            print(f"Epoch {epoch+1}/{epochs}, avg loss = {total_loss/len(dataset):.4f}")

        # Save once after pretraining
        self.save_model()
        print("Pretraining finished and model saved.")

if __name__ == '__main__':
    ai = MinesweeperAITrainer(20, 20)
    ai.pretrain_from_json()
