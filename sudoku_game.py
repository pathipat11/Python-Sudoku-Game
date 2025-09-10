import pygame
import random
import time
import json
import os
from copy import deepcopy

pygame.init()
pygame.font.init()
try:
    pygame.mixer.init()
except Exception:
    print("Warning: pygame.mixer.init() failed - sound disabled")

# --- Configuration ---
WIN_WIDTH, WIN_HEIGHT = 750, 650
GRID_SIZE = 9
GRID_AREA = 560
CELL_SIZE = GRID_AREA // GRID_SIZE
GRID_ORIGIN = (35, 35)
STATS_FILE = "sudoku_stats.json"
AUTOSAVE_FILE = "sudoku_autosave.json"
SAVE_SLOTS = {
    1: "sudoku_save1.json",
    2: "sudoku_save2.json",
    3: "sudoku_save3.json",
}

THEMES = {
    "light": {
        "bg": (245, 245, 245),
        "grid": (50, 50, 50),
        "givens": (40, 40, 40),
        "user": (0, 102, 204),
        "highlight": (180, 220, 255),
        "conflict": (255, 180, 180),
        "note": (100, 100, 100),
        "button": (220, 220, 220),
        "button_hover": (200, 200, 255),
        "overlay": (255, 255, 255, 220)
    },
    "dark": {
        "bg": (20, 20, 30),
        "grid": (220, 220, 220),
        "givens": (200, 200, 200),
        "user": (100, 180, 255),
        "highlight": (60, 60, 100),
        "conflict": (180, 50, 50),
        "note": (180, 180, 180),
        "button": (50, 50, 70),
        "button_hover": (80, 80, 120),
        "overlay": (30, 30, 30, 200)
    }
}

screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
pygame.display.set_caption("Sudoku - Python")

FONT_BIG = pygame.font.SysFont("Arial", 36)
FONT_MED = pygame.font.SysFont("Arial", 20)
FONT_SMALL = pygame.font.SysFont("Arial", 14)
FONT_TITLE = pygame.font.SysFont("Arial", 48)

# --- Sounds ---
SOUND_PATH = os.path.join("assets", "sounds")
def load_sound(name):
    path = os.path.join(SOUND_PATH, name)
    if not os.path.exists(path):
        print(f"Warning: sound file {path} not found")
        return None
    try:
        return pygame.mixer.Sound(path)
    except Exception as e:
        print(f"Error loading sound {path}: {e}")
        return None


sound_type = load_sound("type.mp3")
sound_error = load_sound("error.mp3")
sound_win = load_sound("win.mp3")

# Test sound
# if sound_type: sound_type.play()
# if sound_error: sound_error.play()
# if sound_win: sound_win.play()

# --- Sudoku utilities ---
def find_empty(grid):
    for r in range(9):
        for c in range(9):
            if grid[r][c] == 0:
                return r, c
    return None

def valid(grid, r, c, val):
    for i in range(9):
        if grid[r][i] == val or grid[i][c] == val:
            return False
    br, bc = 3*(r//3), 3*(c//3)
    for i in range(br, br+3):
        for j in range(bc, bc+3):
            if grid[i][j] == val:
                return False
    return True

def solve_backtrack(grid):
    empty = find_empty(grid)
    if not empty: return True
    r, c = empty
    for val in range(1, 10):
        if valid(grid, r, c, val):
            grid[r][c] = val
            if solve_backtrack(grid):return True
            grid[r][c] = 0
    return False

def count_solutions(grid, limit=2):
    empty = find_empty(grid)
    if not empty: return 1
    r, c = empty
    count = 0
    for val in range(1, 10):
        if valid(grid, r, c, val):
            grid[r][c] = val
            count += count_solutions(grid, limit)
            grid[r][c] = 0
            if count >= limit: return count
    return count

def generate_full_solution():
    grid = [[0]*9 for _ in range(9)]
    nums = list(range(1,10))
    def fill():
        empty = find_empty(grid)
        if not empty: return True
        r, c = empty
        random.shuffle(nums)
        for val in nums:
            if valid(grid,r,c,val):
                grid[r][c] = val
                if fill(): return True
                grid[r][c] = 0
        return False
    fill()
    return grid

def generate_puzzle(difficulty="medium"):
    targets = {"easy":36,"medium":32,"hard":28,"insane":22}
    target = targets.get(difficulty,32)
    solution = generate_full_solution()
    puzzle = deepcopy(solution)
    cells = [(r,c) for r in range(9) for c in range(9)]
    random.shuffle(cells)
    attempts = 0
    max_attempts = 8000 if difficulty=="insane" else 5000
    while attempts < max_attempts and sum(1 for r in range(9) for c in range(9) if puzzle[r][c]!=0) > target:
        r,c = random.choice(cells)
        if puzzle[r][c]==0:
            attempts+=1
            continue
        backup = puzzle[r][c]
        puzzle[r][c]=0
        if count_solutions(deepcopy(puzzle), limit=2)!=1:
            puzzle[r][c]=backup
        attempts+=1
    return puzzle, solution

# --- Drawing helpers ---
def draw_button(surface, rect, label, theme, mouse_pos):
    color = theme["button_hover"] if rect.collidepoint(mouse_pos) else theme["button"]
    pygame.draw.rect(surface, color, rect, border_radius=6)
    pygame.draw.rect(surface, theme["grid"], rect, 2, border_radius=6)
    txt = FONT_MED.render(label, True, theme["grid"])
    surface.blit(txt, (rect.x + rect.width//2 - txt.get_width()//2, rect.y + rect.height//2 - txt.get_height()//2))

def draw_gradient_background(surface, color1, color2):
    w, h = surface.get_size()
    for y in range(h):
        ratio = y / h
        r = int(color1[0]*(1-ratio) + color2[0]*ratio)
        g = int(color1[1]*(1-ratio) + color2[1]*ratio)
        b = int(color1[2]*(1-ratio) + color2[2]*ratio)
        pygame.draw.line(surface, (r,g,b), (0,y), (w,y))

# --- Game state ---
class SudokuGame:
    def __init__(self, puzzle=None, solution=None, difficulty="medium"):
        if puzzle is None or solution is None:
            puzzle, solution = generate_puzzle(difficulty)
        self.givens = deepcopy(puzzle)
        self.solution = solution
        self.cells = deepcopy(puzzle)
        self.notes = [[set() for _ in range(9)] for __ in range(9)]
        self.difficulty = difficulty
        self.start_time = time.time()
        self.total_paused = 0.0
        self.pause_start = None
        self.hints_left = 3
        self.auto_check = True
        self.move_stack = []
        self.redo_stack = []
        self.fastest = self.load_fastest()
        self.paused = False
        self.animations = {}

    def load_fastest(self):
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE,"r") as f:
                    data = json.load(f)
                    return data.get(self.difficulty)
            except Exception: return None
        return None

    def save_fastest(self, elapsed):
        data = {}
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE,"r") as f:
                    data = json.load(f)
            except Exception:
                data={}
        prev = data.get(self.difficulty)
        if prev is None or elapsed<prev:
            data[self.difficulty]=elapsed
            with open(STATS_FILE,"w") as f:
                json.dump(data,f)

    def is_given(self,r,c): return self.givens[r][c]!=0

    def set_cell(self, r, c, val, is_note=False):
        if self.is_given(r, c):
            return
        old_val = self.cells[r][c]
        old_notes = set(self.notes[r][c])
        self.move_stack.append((r, c, old_val, old_notes, val, is_note))
        self.redo_stack.clear()
        if is_note:
            if val in self.notes[r][c]:
                self.notes[r][c].remove(val)
            else:
                self.notes[r][c].add(val)
        else:
            self.cells[r][c] = val
            self.notes[r][c].clear()
        self.animations[(r,c)] = {"type":"highlight","start":time.time()}

    def undo(self):
        if not self.move_stack: 
            return
        r, c, old_val, old_notes, new_val, is_note = self.move_stack.pop()
        self.redo_stack.append((r, c, self.cells[r][c], set(self.notes[r][c]), new_val, is_note))
        if is_note:
            self.notes[r][c] = set(old_notes)
        else:
            self.cells[r][c] = old_val
            self.notes[r][c] = set(old_notes)

    def redo(self):
        if not self.redo_stack: 
            return
        r, c, old_val, old_notes, new_val, is_note = self.redo_stack.pop()
        self.move_stack.append((r, c, self.cells[r][c], set(self.notes[r][c]), new_val, is_note))
        if is_note:
            if new_val in self.notes[r][c]:
                if new_val in self.notes[r][c]:
                    self.notes[r][c].remove(new_val)
                else:
                    self.notes[r][c].add(new_val)
            else:
                self.notes[r][c].add(new_val)
        else:
            self.cells[r][c] = new_val
            self.notes[r][c].clear()

    def is_complete(self):
        return all(self.cells[r][c] == self.solution[r][c] for r in range(9) for c in range(9))

    def check_conflicts(self):
        conflicts=[[False]*9 for _ in range(9)]
        for r in range(9):
            for c in range(9):
                val=self.cells[r][c]
                if val==0: continue
                self.cells[r][c]=0
                if not valid(self.cells,r,c,val):
                    conflicts[r][c]=True
                self.cells[r][c]=val
        return conflicts

    def hint(self,r,c):
        if self.hints_left<=0 or self.is_given(r,c): return False
        val=self.solution[r][c]
        self.set_cell(r,c,val,is_note=False)
        self.hints_left-=1
        return True

    def auto_save(self):
        data={
            "puzzle":self.givens,
            "cells":self.cells,
            "notes":[[list(s) for s in row] for row in self.notes],
            "difficulty":self.difficulty,
            "start_time":self.start_time,
            "total_paused":self.total_paused,
            "hints_left":self.hints_left,
        }
        try:
            with open(AUTOSAVE_FILE,"w") as f:
                json.dump(data,f)
        except Exception: pass

    @staticmethod
    def load_autosave():
        if not os.path.exists(AUTOSAVE_FILE): return None
        try:
            with open(AUTOSAVE_FILE,"r") as f:
                data=json.load(f)
            puzzle=data["puzzle"]
            grid=deepcopy(puzzle)
            solution=None
            if solve_backtrack(grid): solution=grid
            game=SudokuGame(puzzle=deepcopy(puzzle),solution=solution,difficulty=data.get("difficulty","medium"))
            game.cells=data["cells"]
            game.notes=[[set(lst) for lst in row] for row in data["notes"]]
            game.start_time=data.get("start_time",time.time())
            game.total_paused=data.get("total_paused",0.0)
            game.hints_left=data.get("hints_left",3)
            return game
        except Exception: return None

    def save_to_slot(self, slot):
        filename = SAVE_SLOTS.get(slot)
        if not filename: return
        data = {
            "puzzle": self.givens,
            "cells": self.cells,
            "notes": [[list(s) for s in row] for row in self.notes],
            "difficulty": self.difficulty,
            "start_time": self.start_time,
            "total_paused": self.total_paused,
            "hints_left": self.hints_left,
            "is_slot": True
        }
        try:
            with open(filename, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    @staticmethod
    def load_from_slot(slot):
        filename = SAVE_SLOTS.get(slot)
        if not filename or not os.path.exists(filename): return None
        try:
            with open(filename, "r") as f:
                data = json.load(f)
            puzzle = data["puzzle"]
            grid = deepcopy(puzzle)
            solution = None
            if solve_backtrack(grid): 
                solution = grid
            game = SudokuGame(puzzle=deepcopy(puzzle), solution=solution, difficulty=data.get("difficulty", "medium"))
            game.cells = data["cells"]
            game.notes = [[set(lst) for lst in row] for row in data["notes"]]
            game.start_time = data.get("start_time", time.time())
            game.total_paused = data.get("total_paused", 0.0)
            game.hints_left = data.get("hints_left", 3)
            return game
        except Exception:
            return None

# --- Drawing ---
def draw_board(surface,game,selected,theme_name="light"):
    theme=THEMES[theme_name]
    bg1 = tuple(min(255, c+30) for c in theme["bg"])  # top lighter
    bg2 = theme["bg"]  # bottom darker
    draw_gradient_background(surface, bg1, bg2)
    now = time.time()
    for (ar,ac), anim in list(game.animations.items()):
        if anim["type"]=="highlight":
            elapsed = now - anim["start"]
            alpha = max(0, 180*(1-elapsed))  # fade out 1 sec
            if alpha <= 0:
                del game.animations[(ar,ac)]
                continue
            s = pygame.Surface((CELL_SIZE,CELL_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(s, (255,255,0,int(alpha)), s.get_rect(), border_radius=6)
            surface.blit(s, (GRID_ORIGIN[0]+ac*CELL_SIZE, GRID_ORIGIN[1]+ar*CELL_SIZE))
    ox,oy=GRID_ORIGIN
    cell=CELL_SIZE
    conflicts=game.check_conflicts() if game.auto_check else [[False]*9 for _ in range(9)]
    sr=sc=None
    if selected: sr,sc=selected
    for r in range(9):
        for c in range(9):
            rect=pygame.Rect(ox+c*cell,oy+r*cell,cell,cell)
            if selected and (r==sr or c==sc or (r//3==sr//3 and c//3==sc//3)):
                pygame.draw.rect(surface,theme["highlight"],rect)
            if conflicts[r][c]: pygame.draw.rect(surface,theme["conflict"],rect)
            val=game.cells[r][c]
            if val!=0:
                color=theme["givens"] if game.is_given(r,c) else theme["user"]
                txt_surface=FONT_BIG.render(str(val),True,color)
                if (r,c) in game.animations:
                    scale = 1 + 0.2*max(0, 1-(time.time()-game.animations[(r,c)]["start"]))
                    txt_surface = pygame.transform.smoothscale(txt_surface, (int(txt_surface.get_width()*scale), int(txt_surface.get_height()*scale)))
                surface.blit(txt_surface,(ox+c*cell+cell//2-txt_surface.get_width()//2,oy+r*cell+cell//2-txt_surface.get_height()//2))
            else:
                notes=sorted(game.notes[r][c])
                if notes:
                    for n in notes:
                        nr=(n-1)//3
                        nc=(n-1)%3
                        nx=ox+c*cell+6+nc*(cell//3)
                        ny=oy+r*cell+6+nr*(cell//3)
                        nt=FONT_SMALL.render(str(n),True,theme["note"])
                        surface.blit(nt,(nx,ny))
    # grid lines
    for i in range(10):
        thick=4 if i%3==0 else 1
        pygame.draw.line(surface,theme["grid"],(ox,oy+i*cell),(ox+9*cell,oy+i*cell),thick)
        pygame.draw.line(surface,theme["grid"],(ox+i*cell,oy),(ox+i*cell,oy+9*cell),thick)
    draw_right_panel(surface,game,theme_name)

def draw_right_panel(surface, game, theme_name):
    theme = THEMES[theme_name]
    x = GRID_ORIGIN[0] + 9*CELL_SIZE + 10
    y = GRID_ORIGIN[1]
    w = WIN_WIDTH - x - 20
    mouse_pos = pygame.mouse.get_pos()
    
    funcs = [("New (G)","g"),("Hint (H)","h"),("Notes (N)","n"),("Undo (U)","u"), 
            ("Redo (R)","r"),("Save (S)","s"),("Load (L)","l"),("Toggle Check (C)","c"),
            ("Pause (P)","p"),("Theme (T)","t")]
    
    for i, (label, _) in enumerate(funcs):
        rect = pygame.Rect(x, y + i*50, w, 40)
        draw_button(surface, rect, label, theme, mouse_pos)
    
    # Info panel
    elapsed = int(get_elapsed_time(game)) if not game.paused else int(game.pause_start - game.start_time - game.total_paused) if game.pause_start else int(get_elapsed_time(game))
    info_lines = [f"Time: {format_time(elapsed)}", f"Difficulty: {game.difficulty}", f"Hints left: {game.hints_left}"]
    if game.fastest: info_lines.append(f"Fastest: {format_time(int(game.fastest))}")
    
    for i, line in enumerate(info_lines):
        txt = FONT_MED.render(line, True, theme["grid"])
        surface.blit(txt, (x, y + 520 + i*30))

def format_time(s): return f"{s//60:02d}:{s%60:02d}"
def get_elapsed_time(game):
    if game.paused and game.pause_start:
        return max(0, game.pause_start - game.start_time - game.total_paused)
    else:
        return max(0, time.time() - game.start_time - game.total_paused)

# --- Overlays ---
def draw_centered_overlay(screen,text_lines,buttons=None,theme_name="light"):
    theme=THEMES[theme_name]
    overlay_surf=pygame.Surface((WIN_WIDTH-100,WIN_HEIGHT-160),pygame.SRCALPHA)
    overlay_surf.fill(theme["overlay"])
    ox=(WIN_WIDTH-overlay_surf.get_width())//2
    oy=(WIN_HEIGHT-overlay_surf.get_height())//2
    screen.blit(overlay_surf,(ox,oy))
    for i,line in enumerate(text_lines):
        txt=FONT_BIG.render(line,True,theme["grid"])
        screen.blit(txt,(ox+overlay_surf.get_width()//2-txt.get_width()//2,oy+30+i*50))
    if buttons:
        for label,rect in buttons:
            pygame.draw.rect(screen,theme["button"],rect)
            txt=FONT_MED.render(label,True,theme["grid"])
            screen.blit(txt,(rect.x+rect.width//2-txt.get_width()//2,rect.y+rect.height//2-txt.get_height()//2))

def draw_pause_overlay(screen,theme_name):
    theme=THEMES[theme_name]
    s=pygame.Surface((WIN_WIDTH,WIN_HEIGHT),pygame.SRCALPHA)
    s.fill((0,0,0,120))
    screen.blit(s,(0,0))
    txt=FONT_TITLE.render("PAUSED",True,(255,255,255))
    screen.blit(txt,(WIN_WIDTH//2-txt.get_width()//2,WIN_HEIGHT//2-txt.get_height()//2-20))
    hint=FONT_MED.render("Press P to resume",True,(255,255,255))
    screen.blit(hint,(WIN_WIDTH//2-hint.get_width()//2,WIN_HEIGHT//2+20))

# --- Difficulty menu ---
def menu_select_difficulty(theme_name="light"):
    selecting=True
    diffs=["easy","medium","hard","insane"]
    idx=1
    while selecting:
        screen.fill(THEMES[theme_name]["bg"])
        title=FONT_TITLE.render("Sudoku",True,THEMES[theme_name]["grid"])
        screen.blit(title,(WIN_WIDTH//2-title.get_width()//2,80))
        sub=FONT_MED.render("Select difficulty (Up/Down arrows) and Enter",True,THEMES[theme_name]["grid"])
        screen.blit(sub,(WIN_WIDTH//2-sub.get_width()//2,150))
        for i,d in enumerate(diffs):
            color=THEMES[theme_name]["grid"]
            txt=FONT_BIG.render(d.capitalize(),True,color if i==idx else (120,120,120))
            screen.blit(txt,(WIN_WIDTH//2-txt.get_width()//2,260+i*60))
        pygame.display.flip()
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT:
                pygame.quit(); exit(0)
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_UP: idx=(idx-1)%len(diffs)
                if ev.key==pygame.K_DOWN: idx=(idx+1)%len(diffs)
                if ev.key in (pygame.K_RETURN,pygame.K_KP_ENTER): selecting=False; return diffs[idx]
                if ev.key==pygame.K_ESCAPE: pygame.quit(); exit(0)
        pygame.time.delay(50)
    return "medium"

# --- Main loop ---
def toggle_pause(game):
    if game.paused:
        if game.pause_start: game.total_paused+=time.time()-game.pause_start
        game.pause_start=None
        game.paused=False
    else:
        game.pause_start=time.time()
        game.paused=True

def main():
    clock = pygame.time.Clock()
    running = True
    theme = "light"
    difficulty = menu_select_difficulty(theme)
    game = SudokuGame(difficulty=difficulty)
    selected = (0, 0)
    notes_mode = False
    last_autosave = time.time()
    show_win_overlay = False
    win_overlay_info = None
    message = ""
    message_time = 0
    number_keys = {
        pygame.K_1: 1, pygame.K_KP1: 1,
        pygame.K_2: 2, pygame.K_KP2: 2,
        pygame.K_3: 3, pygame.K_KP3: 3,
        pygame.K_4: 4, pygame.K_KP4: 4,
        pygame.K_5: 5, pygame.K_KP5: 5,
        pygame.K_6: 6, pygame.K_KP6: 6,
        pygame.K_7: 7, pygame.K_KP7: 7,
        pygame.K_8: 8, pygame.K_KP8: 8,
        pygame.K_9: 9, pygame.K_KP9: 9,
    }

    while running:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.auto_save()
                running = False

            # --- Keyboard input ---
            elif event.type == pygame.KEYDOWN:
                # Pause toggle works anytime (evenเมื่อ paused)
                if event.key == pygame.K_p:
                    toggle_pause(game)
                    continue

                # ถ้า paused หรือ win overlay อยู่ ข้ามทุกอย่าง
                if game.paused or show_win_overlay:
                    continue

                r, c = selected
                
                # --- Number input ---
                if event.key in number_keys:
                    val = number_keys[event.key]
                    game.set_cell(r, c, val, is_note=notes_mode)
                    if sound_type: sound_type.play()
                elif event.key in (pygame.K_0, pygame.K_DELETE, pygame.K_BACKSPACE):
                    if not game.is_given(r, c):
                        game.set_cell(r, c, 0)
                        if sound_type: sound_type.play()
                    else:
                        if sound_error: sound_error.play()
                        
                elif event.key in (pygame.K_0, pygame.K_DELETE, pygame.K_BACKSPACE):
                    if not game.is_given(r, c):
                        game.set_cell(r, c, 0)
                        if sound_type: sound_type.play()
                    else:
                        if sound_error: sound_error.play()
                
                # --- Keyboard Navigation ---
                elif event.key == pygame.K_LEFT:
                    r, c = selected
                    selected = (r, (c - 1) % 9)
                elif event.key == pygame.K_RIGHT:
                    r, c = selected
                    selected = (r, (c + 1) % 9)
                elif event.key == pygame.K_UP:
                    r, c = selected
                    selected = ((r - 1) % 9, c)
                elif event.key == pygame.K_DOWN:
                    r, c = selected
                    selected = ((r + 1) % 9, c)
                    
                # --- Save slots ---
                elif event.key == pygame.K_F1:
                    game.save_to_slot(1)
                    if sound_type: sound_type.play()
                    message = "Save Slot 1 Success!"
                    message_time = time.time()

                elif event.key == pygame.K_F2:
                    game.save_to_slot(2)
                    if sound_type: sound_type.play()
                    message = "Save Slot 2 Success!"
                    message_time = time.time()

                elif event.key == pygame.K_F3:
                    game.save_to_slot(3)
                    if sound_type: sound_type.play()
                    message = "Save Slot 3 Success!"
                    message_time = time.time()

                # --- Load slots ---
                elif event.key == pygame.K_F8:
                    loaded = SudokuGame.load_from_slot(1)
                    if loaded: 
                        game = loaded
                        if sound_type: sound_type.play()
                        message = "Load Slot 1 Success!"
                        message_time = time.time()

                elif event.key == pygame.K_F9:
                    loaded = SudokuGame.load_from_slot(2)
                    if loaded: 
                        game = loaded
                        if sound_type: sound_type.play()
                        message = "Load Slot 2 Success!"
                        message_time = time.time()

                elif event.key == pygame.K_F10:
                    loaded = SudokuGame.load_from_slot(3)
                    if loaded: 
                        game = loaded
                        if sound_type: sound_type.play()
                        message = "Load Slot 3 Success!"
                        message_time = time.time()

                # --- Auto-save (กด S) ---
                elif event.key == pygame.K_s:
                    game.auto_save()
                    if sound_type: sound_type.play()
                    message = "Auto Save Success!"
                    message_time = time.time()

                # --- Auto-load (กด L) ---
                elif event.key == pygame.K_l:
                    loaded = SudokuGame.load_autosave()
                    if loaded: 
                        game = loaded
                        if sound_type: sound_type.play()
                        message = "Load AutoSave Success!"
                        message_time = time.time()
                

                # --- Game actions ---
                elif event.key == pygame.K_u: game.undo(); sound_type.play()
                elif event.key == pygame.K_r: game.redo(); sound_type.play()
                elif event.key == pygame.K_n: notes_mode = not notes_mode; sound_type.play()
                elif event.key == pygame.K_h: 
                    if not game.hint(r, c): sound_error.play()
                    else: sound_type.play()
                elif event.key == pygame.K_c: game.auto_check = not game.auto_check; sound_type.play()
                elif event.key == pygame.K_t: theme = "dark" if theme=="light" else "light"; sound_type.play()
                elif event.key == pygame.K_g:
                    # กลับไปหน้าเลือกความยาก
                    difficulty = menu_select_difficulty(theme)
                    game = SudokuGame(difficulty=difficulty)
                    selected = (0, 0)
                    notes_mode = False
                    show_win_overlay = False
                    sound_type.play() if sound_type else None

            # --- Mouse selection ---
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                if show_win_overlay:
                    ox = (WIN_WIDTH - (WIN_WIDTH - 100)) // 2
                    oy = (WIN_HEIGHT - (WIN_HEIGHT - 160)) // 2
                    bw = 160
                    bh = 42
                    bx = ox + (WIN_WIDTH - 100)//2 - bw - 10
                    by = oy + (WIN_HEIGHT - 160) - 80
                    rect_new = pygame.Rect(bx, by, bw, bh)
                    rect_quit = pygame.Rect(bx + bw + 20, by, bw, bh)
                    if rect_new.collidepoint(mx, my):
                        game = SudokuGame(difficulty=game.difficulty)
                        show_win_overlay = False
                        selected = (0, 0)
                        notes_mode = False
                        continue
                    if rect_quit.collidepoint(mx, my):
                        game.auto_save()
                        running = False
                        continue
                ox, oy = GRID_ORIGIN
                if ox <= mx < ox + 9*CELL_SIZE and oy <= my < oy + 9*CELL_SIZE:
                    c = (mx - ox) // CELL_SIZE
                    r = (my - oy) // CELL_SIZE
                    selected = (r, c)
                    game.animations[(r,c)] = {"type":"highlight","start":time.time()}

        # --- Auto-save every 30s ---
        if time.time() - last_autosave > 30:
            game.auto_save()
            last_autosave = time.time()

        # --- Drawing ---
        draw_board(screen, game, selected, theme)

        if message and time.time() - message_time < 2:
            txt = FONT_MED.render(message, True, (0, 200, 0))
            screen.blit(txt, (WIN_WIDTH//2 - txt.get_width()//2, WIN_HEIGHT - 40))
        
        if game.paused:
            draw_pause_overlay(screen, theme)

        # --- Win overlay ---
        if game.is_complete() and not show_win_overlay:
            show_win_overlay = True
            win_overlay_info = int(get_elapsed_time(game))
            game.save_fastest(win_overlay_info)
            sound_win.play() if sound_win else None

        if show_win_overlay and win_overlay_info is not None:
            ox = (WIN_WIDTH - (WIN_WIDTH - 100)) // 2
            oy = (WIN_HEIGHT - (WIN_HEIGHT - 160)) // 2
            lines = ["You Win!", f"Time: {format_time(win_overlay_info)}"]
            bw = 160
            bh = 42
            bx = ox + (WIN_WIDTH - 100)//2 - bw - 10
            by = oy + (WIN_HEIGHT - 160) - 80
            rect_new = pygame.Rect(bx, by, bw, bh)
            rect_quit = pygame.Rect(bx + bw + 20, by, bw, bh)
            draw_centered_overlay(screen, lines, buttons=[("New", rect_new), ("Quit", rect_quit)], theme_name=theme)

        pygame.display.flip()


if __name__=="__main__":
    main()
