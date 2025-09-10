import pygame
import random
import time
import json
import os
from copy import deepcopy

pygame.init()
pygame.font.init()

# --- Configuration ---
WIN_WIDTH, WIN_HEIGHT = 750, 650
GRID_SIZE = 9
CELL_SIZE = 560 // GRID_SIZE  # use area for grid
GRID_ORIGIN = (35, 35)
STATS_FILE = "sudoku_stats.json"
AUTOSAVE_FILE = "sudoku_autosave.json"

# Colors for light/dark themes
THEMES = {
    "light": {
        "bg": (245, 245, 245),
        "grid": (0, 0, 0),
        "givens": (50, 50, 50),
        "user": (10, 60, 160),
        "highlight": (200, 230, 255),
        "conflict": (255, 200, 200),
        "note": (80, 80, 80),
        "button": (200, 200, 200),
    },
    "dark": {
        "bg": (30, 30, 30),
        "grid": (230, 230, 230),
        "givens": (220, 220, 220),
        "user": (100, 180, 255),
        "highlight": (60, 60, 100),
        "conflict": (120, 40, 40),
        "note": (180, 180, 180),
        "button": (80, 80, 80),
    },
}

screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
pygame.display.set_caption("Sudoku - Python (by ChatGPT)")

FONT_BIG = pygame.font.SysFont("Arial", 36)
FONT_MED = pygame.font.SysFont("Arial", 20)
FONT_SMALL = pygame.font.SysFont("Arial", 14)

# --- Sudoku utilities ---
def find_empty(grid):
    for r in range(9):
        for c in range(9):
            if grid[r][c] == 0:
                return r, c
    return None

def valid(grid, r, c, val):
    # row/col
    for i in range(9):
        if grid[r][i] == val:
            return False
        if grid[i][c] == val:
            return False
    # box
    br, bc = 3 * (r // 3), 3 * (c // 3)
    for i in range(br, br + 3):
        for j in range(bc, bc + 3):
            if grid[i][j] == val:
                return False
    return True

def solve_backtrack(grid):
    empty = find_empty(grid)
    if not empty:
        return True
    r, c = empty
    for val in range(1, 10):
        if valid(grid, r, c, val):
            grid[r][c] = val
            if solve_backtrack(grid):
                return True
            grid[r][c] = 0
    return False

def count_solutions(grid, limit=2):
    # backtracking counter with early stop
    empty = find_empty(grid)
    if not empty:
        return 1
    r, c = empty
    count = 0
    for val in range(1, 10):
        if valid(grid, r, c, val):
            grid[r][c] = val
            count += count_solutions(grid, limit)
            grid[r][c] = 0
            if count >= limit:
                return count
    return count

def generate_full_solution():
    grid = [[0]*9 for _ in range(9)]
    nums = list(range(1,10))
    def fill():
        empty = find_empty(grid)
        if not empty:
            return True
        r, c = empty
        random.shuffle(nums)
        for val in nums:
            if valid(grid, r, c, val):
                grid[r][c] = val
                if fill():
                    return True
                grid[r][c] = 0
        return False
    fill()
    return grid

def generate_puzzle(difficulty="medium"):
    # difficulty -> number of clues
    targets = {"easy": 36, "medium": 32, "hard": 28, "insane": 24}
    target = targets.get(difficulty, 32)
    solution = generate_full_solution()
    puzzle = deepcopy(solution)
    # create list of cell positions and shuffle
    cells = [(r,c) for r in range(9) for c in range(9)]
    random.shuffle(cells)
    # remove while maintaining unique solution and not below target clues
    attempts = 0
    max_attempts = 5000
    while attempts < max_attempts and sum(1 for r in range(9) for c in range(9) if puzzle[r][c] != 0) > target:
        r,c = random.choice(cells)
        if puzzle[r][c] == 0:
            attempts += 1
            continue
        backup = puzzle[r][c]
        puzzle[r][c] = 0
        puzzle_copy = deepcopy(puzzle)
        sol_count = count_solutions(puzzle_copy, limit=2)
        if sol_count != 1:
            puzzle[r][c] = backup
        attempts += 1
    return puzzle, solution

# --- Game state class ---
class SudokuGame:
    def __init__(self, puzzle=None, solution=None, difficulty="medium"):
        if puzzle is None or solution is None:
            puzzle, solution = generate_puzzle(difficulty)
        self.givens = [[puzzle[r][c] for c in range(9)] for r in range(9)]
        self.solution = solution
        self.cells = [[puzzle[r][c] for c in range(9)] for r in range(9)]
        # notes: set of possible small numbers per cell
        self.notes = [[set() for _ in range(9)] for __ in range(9)]
        self.difficulty = difficulty
        self.start_time = time.time()
        self.hints_left = 3
        self.auto_check = True
        self.move_stack = []
        self.redo_stack = []
        self.fastest = self.load_fastest()
        self.paused = False

    def load_fastest(self):
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, "r") as f:
                    data = json.load(f)
                    return data.get(self.difficulty)
            except Exception:
                return None
        return None

    def save_fastest(self, elapsed):
        data = {}
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, "r") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        prev = data.get(self.difficulty)
        if prev is None or elapsed < prev:
            data[self.difficulty] = elapsed
            with open(STATS_FILE, "w") as f:
                json.dump(data, f)

    def is_given(self, r, c):
        return self.givens[r][c] != 0

    def set_cell(self, r, c, val, is_note=False):
        # record old for undo
        old_val = self.cells[r][c]
        old_notes = set(self.notes[r][c])
        self.move_stack.append((r,c,old_val, old_notes, val, is_note))
        self.redo_stack.clear()
        if is_note:
            if val in self.notes[r][c]:
                self.notes[r][c].remove(val)
            else:
                self.notes[r][c].add(val)
        else:
            self.cells[r][c] = val
            self.notes[r][c].clear()

    def undo(self):
        if not self.move_stack:
            return
        r,c,old_val, old_notes, new_val, is_note = self.move_stack.pop()
        # push to redo
        self.redo_stack.append((r,c, self.cells[r][c], set(self.notes[r][c]), old_val, old_notes))
        self.cells[r][c] = old_val
        self.notes[r][c] = set(old_notes)

    def redo(self):
        if not self.redo_stack:
            return
        r,c, old_val, old_notes, new_val, is_note = self.redo_stack.pop()
        self.move_stack.append((r,c, old_val, old_notes, new_val, is_note))
        self.cells[r][c] = new_val
        self.notes[r][c] = set(old_notes) if isinstance(old_notes, set) else set(old_notes)

    def is_complete(self):
        return all(self.cells[r][c] != 0 for r in range(9) for c in range(9))

    def check_conflicts(self):
        conflicts = [[False]*9 for _ in range(9)]
        for r in range(9):
            for c in range(9):
                val = self.cells[r][c]
                if val == 0:
                    continue
                # temporarily clear to check duplicates properly
                self.cells[r][c] = 0
                if not valid(self.cells, r, c, val):
                    conflicts[r][c] = True
                self.cells[r][c] = val
        return conflicts

    def hint(self, r, c):
        if self.hints_left <= 0:
            return False
        if self.is_given(r,c):
            return False
        val = self.solution[r][c]
        self.set_cell(r,c,val, is_note=False)
        self.hints_left -= 1
        return True

    def auto_save(self):
        data = {
            "puzzle": self.givens,
            "cells": self.cells,
            "notes": [[list(s) for s in row] for row in self.notes],
            "difficulty": self.difficulty,
            "start_time": self.start_time,
            "hints_left": self.hints_left,
        }
        with open(AUTOSAVE_FILE, "w") as f:
            json.dump(data, f)

    @staticmethod
    def load_autosave():
        if not os.path.exists(AUTOSAVE_FILE):
            return None
        try:
            with open(AUTOSAVE_FILE, "r") as f:
                data = json.load(f)
            puzzle = data["puzzle"]
            solution = None
            # solution unknown; recompute by solving
            grid = deepcopy(puzzle)
            if solve_backtrack(grid):
                solution = grid
            game = SudokuGame(puzzle=deepcopy(puzzle), solution=solution, difficulty=data.get("difficulty","medium"))
            game.cells = data["cells"]
            game.notes = [[set(lst) for lst in row] for row in data["notes"]]
            game.start_time = data.get("start_time", time.time())
            game.hints_left = data.get("hints_left", 3)
            return game
        except Exception:
            return None

# --- Drawing helpers ---
def draw_board(surface, game, selected, theme_name="light"):
    theme = THEMES[theme_name]
    surface.fill(theme["bg"])
    ox, oy = GRID_ORIGIN
    cell = CELL_SIZE
    # draw cells background and highlights
    conflicts = game.check_conflicts() if game.auto_check else [[False]*9 for _ in range(9)]
    if selected:
        sr, sc = selected
    for r in range(9):
        for c in range(9):
            rect = pygame.Rect(ox + c*cell, oy + r*cell, cell, cell)
            if selected and (r==sr or c==sc or (r//3==sr//3 and c//3==sc//3)):
                pygame.draw.rect(surface, theme["highlight"], rect)
            if conflicts[r][c]:
                pygame.draw.rect(surface, theme["conflict"], rect)
            # draw given or user number
            val = game.cells[r][c]
            if val != 0:
                if game.is_given(r,c):
                    txt = FONT_BIG.render(str(val), True, theme["givens"])
                else:
                    txt = FONT_BIG.render(str(val), True, theme["user"])
                surface.blit(txt, (ox + c*cell + cell//2 - txt.get_width()//2, oy + r*cell + cell//2 - txt.get_height()//2))
            else:
                # draw notes
                notes = sorted(game.notes[r][c])
                if notes:
                    # draw 3x3 grid small numbers
                    small = FONT_SMALL
                    for n in notes:
                        pos_in_box = (n-1)
                        nr = pos_in_box // 3
                        nc = pos_in_box % 3
                        nx = ox + c*cell + 6 + nc*(cell//3)
                        ny = oy + r*cell + 6 + nr*(cell//3)
                        nt = small.render(str(n), True, theme["note"])
                        surface.blit(nt, (nx, ny))
    # thick lines
    for i in range(10):
        thick = 4 if i%3==0 else 1
        pygame.draw.line(surface, theme["grid"], (ox, oy + i*cell), (ox + 9*cell, oy + i*cell), thick)
        pygame.draw.line(surface, theme["grid"], (ox + i*cell, oy), (ox + i*cell, oy + 9*cell), thick)
    # UI - right panel
    draw_right_panel(surface, game, theme_name)

def draw_right_panel(surface, game, theme_name):
    theme = THEMES[theme_name]
    x = GRID_ORIGIN[0] + 9*CELL_SIZE + 10
    y = GRID_ORIGIN[1]
    w = WIN_WIDTH - x - 20
    # Buttons and info
    funcs = [
        ("New (G)", "g"),
        ("Hint (H)", "h"),
        ("Notes (N)", "n"),
        ("Undo (U)", "u"),
        ("Redo (R)", "r"),
        ("Save (S)", "s"),
        ("Load (L)", "l"),
        ("Toggle Check (C)", "c"),
        ("Theme (T)", "t"),
    ]
    for i, (label, key) in enumerate(funcs):
        rect = pygame.Rect(x, y + i*40, w, 34)
        pygame.draw.rect(surface, theme["button"], rect)
        txt = FONT_MED.render(label, True, theme["grid"])
        surface.blit(txt, (rect.x + 6, rect.y + 6))
    # Timer and difficulty
    elapsed = int(time.time() - game.start_time) if not game.paused else 0
    txt = FONT_MED.render(f"Time: {format_time(elapsed)}", True, theme["grid"])
    surface.blit(txt, (x, y + 9*40))
    txt2 = FONT_MED.render(f"Difficulty: {game.difficulty}", True, theme["grid"])
    surface.blit(txt2, (x, y + 9*40 + 30))
    txt3 = FONT_MED.render(f"Hints left: {game.hints_left}", True, theme["grid"])
    surface.blit(txt3, (x, y + 9*40 + 60))
    if game.fastest:
        txt4 = FONT_MED.render(f"Fastest: {format_time(int(game.fastest))}", True, theme["grid"])
        surface.blit(txt4, (x, y + 9*40 + 90))

def format_time(s):
    m = s // 60
    sec = s % 60
    return f"{m:02d}:{sec:02d}"

# --- Main loop ---
def main():
    clock = pygame.time.Clock()
    running = True
    theme = "light"
    game = SudokuGame(difficulty="medium")
    selected = (0,0)
    notes_mode = False
    last_autosave = time.time()
    while running:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.auto_save()
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx,my = pygame.mouse.get_pos()
                ox, oy = GRID_ORIGIN
                if ox <= mx < ox + 9*CELL_SIZE and oy <= my < oy + 9*CELL_SIZE:
                    c = (mx - ox) // CELL_SIZE
                    r = (my - oy) // CELL_SIZE
                    selected = (r,c)
                else:
                    # check right panel clicks for buttons by position
                    x = GRID_ORIGIN[0] + 9*CELL_SIZE + 10
                    y = GRID_ORIGIN[1]
                    w = WIN_WIDTH - x - 20
                    for i, (_, key) in enumerate([("New","g"),("Hint","h"),("Notes","n"),("Undo","u"),("Redo","r"),("Save","s"),("Load","l"),("Toggle Check","c"),("Theme","t")]):
                        rect = pygame.Rect(x, y + i*40, w, 34)
                        if rect.collidepoint(mx,my):
                            if key == "g":
                                # new game choose difficulty quick cycle
                                di = ["easy","medium","hard","insane"]
                                nd = di[(di.index(game.difficulty)+1)%len(di)]
                                game = SudokuGame(difficulty=nd)
                            elif key == "h":
                                r,c = selected
                                game.hint(r,c)
                            elif key == "n":
                                notes_mode = not notes_mode
                            elif key == "u":
                                game.undo()
                            elif key == "r":
                                game.redo()
                            elif key == "s":
                                game.auto_save()
                            elif key == "l":
                                loaded = SudokuGame.load_autosave()
                                if loaded:
                                    game = loaded
                            elif key == "c":
                                game.auto_check = not game.auto_check
                            elif key == "t":
                                theme = "dark" if theme=="light" else "light"
            elif event.type == pygame.KEYDOWN:
                r,c = selected
                if event.key in (pygame.K_1,pygame.K_KP1):
                    val = 1
                elif event.key in (pygame.K_2,pygame.K_KP2):
                    val = 2
                elif event.key in (pygame.K_3,pygame.K_KP3):
                    val = 3
                elif event.key in (pygame.K_4,pygame.K_KP4):
                    val = 4
                elif event.key in (pygame.K_5,pygame.K_KP5):
                    val = 5
                elif event.key in (pygame.K_6,pygame.K_KP6):
                    val = 6
                elif event.key in (pygame.K_7,pygame.K_KP7):
                    val = 7
                elif event.key in (pygame.K_8,pygame.K_KP8):
                    val = 8
                elif event.key in (pygame.K_9,pygame.K_KP9):
                    val = 9
                elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                    val = 0
                elif event.key == pygame.K_n:
                    notes_mode = not notes_mode
                    val = None
                elif event.key == pygame.K_h:
                    game.hint(r,c)
                    val = None
                elif event.key == pygame.K_u:
                    game.undo()
                    val = None
                elif event.key == pygame.K_r:
                    game.redo()
                    val = None
                elif event.key == pygame.K_s:
                    game.auto_save()
                    val = None
                elif event.key == pygame.K_l:
                    loaded = SudokuGame.load_autosave()
                    if loaded:
                        game = loaded
                    val = None
                elif event.key == pygame.K_c:
                    game.auto_check = not game.auto_check
                    val = None
                elif event.key == pygame.K_t:
                    theme = "dark" if theme=="light" else "light"
                    val = None
                elif event.key == pygame.K_g:
                    di = ["easy","medium","hard","insane"]
                    nd = di[(di.index(game.difficulty)+1)%len(di)]
                    game = SudokuGame(difficulty=nd)
                    val = None
                else:
                    val = None
                if val is not None:
                    if not game.is_given(r,c):
                        if notes_mode and val != 0:
                            game.set_cell(r,c,val,is_note=True)
                        else:
                            game.set_cell(r,c,val,is_note=False)
        # autosave periodic
        if time.time() - last_autosave > 10:
            game.auto_save()
            last_autosave = time.time()
        # check complete
        if game.is_complete():
            # verify solution
            if game.cells == game.solution:
                elapsed = int(time.time() - game.start_time)
                game.save_fastest(elapsed)
                # restart new game preserving difficulty
                game = SudokuGame(difficulty=game.difficulty)
        draw_board(screen, game, selected, theme)
        pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    main()