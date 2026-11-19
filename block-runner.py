#e3ff00#ff80c8# Pokémon Runner — Fullscreen Landscape + Pokémon enemies + Leaderboard + Name input
# Single-file. Works on PC and Android (Pydroid 3).
# Requires pygame: pip install pygame

import pygame
import sys
import random
import json
import os
import math
from datetime import datetime

# ---------------- CONFIG ----------------
FPS = 60
GROUND_RATIO = 0.78   # ground line at 78% of screen height
START_SPEED = 6.0
BG_COLOR = (45, 45, 45)
FG_COLOR = (255, 255, 255)
GROUND_COLOR = (0, 0, 0)
LEADERBOARD_FILE = "leaderboard.json"
MAX_LEADERBOARD = 10
SOUND_FILES = {
    'jump': 'jump.wav',
    'hit': 'hit.wav',
    'bg': 'bg_music.mp3'
}

pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# Start fullscreen and force landscape orientation (swap if portrait)
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
if HEIGHT > WIDTH:
    WIDTH, HEIGHT = HEIGHT, WIDTH
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)

GROUND_Y = int(HEIGHT * GROUND_RATIO)
clock = pygame.time.Clock()

# Load sounds
sounds = {}
for key, file in SOUND_FILES.items():
    if os.path.exists(file):
        if key == 'bg':
            try:
                pygame.mixer.music.load(file)
                pygame.mixer.music.play(-1)
            except:
                pass
        else:
            try:
                sounds[key] = pygame.mixer.Sound(file)
            except:
                pass

# Responsive fonts (use default font for better cross-platform compatibility)
def get_font(size):
    return pygame.font.Font(None, max(12, int(size)))

FONT_LG = get_font(36 if HEIGHT < 800 else 48)
FONT_MD = get_font(24 if HEIGHT < 800 else 32)
FONT_SM = get_font(18 if HEIGHT < 800 else 22)

# ---------------- POKEMON BLOCK SPRITES ----------------
POKEMON_PATTERNS = [
    [(0,0,1),(1,0,1),(2,0,1),(0,1,1),(2,1,1),(0,2,1),(1,2,1),(2,2,1)],  # Pikachu-like
    [(0,0,1),(1,0,1),(2,0,1),(1,1,1),(1,2,1)],  # Squirtle-like
    [(0,0,1),(1,0,1),(0,1,1),(1,1,1),(2,1,1),(1,2,1)],  # Charmander-like
    [(0,0,1),(2,0,1),(0,1,1),(1,1,1),(2,1,1),(1,2,1)],  # Bulbasaur-like
    [(1,0,1),(0,1,1),(1,1,1),(2,1,1),(1,2,1)],  # Jigglypuff-like
    [(0,0,1),(1,0,1),(0,1,1),(1,1,1),(0,2,1),(1,2,1)],  # Eevee-like
    [(0,0,1),(1,0,1),(2,0,1),(0,1,1),(2,1,1),(1,2,1)],  # Meowth-like
    [(0,0,1),(1,0,1),(0,1,1),(1,1,1),(2,1,1)],  # Psyduck-like
    [(1,0,1),(0,1,1),(1,1,1),(2,1,1),(1,2,1),(0,2,1),(2,2,1)],  # Snorlax-like
    [(0,0,1),(1,0,1),(2,0,1),(0,1,1),(2,1,1),(0,2,1),(2,2,1)],  # Machop-like
]
POKEMON_COLORS = [
    (100,200,255),  # Blue
    (80,200,120),   # Green
    (255,140,80),   # Orange
    (255,220,50),   # Yellow
    (50,100,200),   # Dark Blue
    (255,150,200),  # Pink
    (180,180,180),  # Gray
    (255,255,120),  # Light Yellow
    (150,100,50),   # Brown
    (160,60,200),   # Purple
]

def draw_pokemon(surface, x, y, poke_id, size):
    pattern = POKEMON_PATTERNS[poke_id % len(POKEMON_PATTERNS)]
    color = POKEMON_COLORS[poke_id % len(POKEMON_COLORS)]
    for px, py, val in pattern:
        if val:
            rect = pygame.Rect(int(x + px * size), int(y + py * size), int(size), int(size))
            pygame.draw.rect(surface, color, rect, border_radius=max(1, int(size*0.2)))

# ---------------- Leaderboard persistence ----------------
def load_leaderboard():
    if not os.path.exists(LEADERBOARD_FILE):
        return []
    try:
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, IOError):
        pass
    return []

def save_leaderboard(lb):
    try:
        with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
            json.dump(lb[:MAX_LEADERBOARD], f, ensure_ascii=False, indent=2)
    except (IOError, json.JSONDecodeError):
        pass

def add_score(name, score):
    lb = load_leaderboard()
    lb.append({"name": name, "score": int(score), "date": datetime.utcnow().isoformat()})
    lb.sort(key=lambda x: x["score"], reverse=True)
    save_leaderboard(lb)
    return lb[:MAX_LEADERBOARD]

def format_leaderboard(lb):
    lines = []
    for i, entry in enumerate(lb, 1):
        lines.append(f"{i}. {entry['name'][:12]:<12} {entry['score']:>6}")
    return lines

# ---------------- Entities ----------------
class Player:
    def __init__(self):
        self.size = max(12, HEIGHT // 26)
        self.w, self.h = 3 * self.size, 3 * self.size
        self.x = WIDTH // 10
        self.y = float(GROUND_Y - self.h)
        self.rect = pygame.Rect(self.x, int(self.y), self.w, self.h)
        self.vel_y = 0.0
        self.on_ground = True
        self.gravity = HEIGHT * 0.0016
        self.jump_power = -(HEIGHT * 0.036)
        self.poke_id = random.randint(0, len(POKEMON_PATTERNS) - 1)
        self.bob_offset = 0.0

    def reset(self):
        self.__init__()

    def jump(self):
        if self.on_ground:
            self.vel_y = self.jump_power
            self.on_ground = False
            if 'jump' in sounds:
                sounds['jump'].play()

    def update(self):
        self.vel_y += self.gravity
        self.y += self.vel_y
        if self.y >= GROUND_Y - self.h:
            self.y = GROUND_Y - self.h
            self.vel_y = 0.0
            self.on_ground = True
        if self.on_ground:
            self.bob_offset = math.sin(pygame.time.get_ticks() * 0.005) * (self.size // 3)
        else:
            self.bob_offset = 0.0
        self.rect.topleft = (int(self.x), int(self.y))

    def draw(self, surface):
        draw_pokemon(surface, self.x, self.y + self.bob_offset, self.poke_id, self.size)

class Enemy:
    def __init__(self, base_speed):
        self.poke_id = random.randint(0, len(POKEMON_PATTERNS) - 1)
        scale_choice = random.choice([0.7, 0.9, 1.1])
        self.size = max(8, int((HEIGHT // 26) * scale_choice))
        self.w, self.h = 3 * self.size, 3 * self.size
        self.x = float(WIDTH + random.randint(int(WIDTH * 0.02), int(WIDTH * 0.25)))
        self.y = float(GROUND_Y - self.h)
        self.speed_multiplier = random.uniform(1.0, 1.35)
        self.speed = base_speed * self.speed_multiplier
        self.rect = pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        self.bob_offset = 0.0

    def update(self, base_speed):
        self.speed = base_speed * self.speed_multiplier
        self.x -= self.speed
        self.bob_offset = math.sin(pygame.time.get_ticks() * 0.005) * (self.size // 3)
        self.rect.topleft = (int(self.x), int(self.y))

    def offscreen(self):
        return self.x + self.w < 0

    def draw(self, surface):
        draw_pokemon(surface, self.x, self.y + self.bob_offset, self.poke_id, self.size)

class Obstacle:
    def __init__(self, base_speed):
        self.w = random.randint(20, 60)
        self.h = random.randint(15, 40)
        self.x = float(WIDTH + random.randint(0, int(WIDTH * 0.25)))
        self.y = float(GROUND_Y - self.h)
        self.speed_multiplier = random.uniform(0.9, 1.3)
        self.speed = base_speed * self.speed_multiplier
        self.rect = pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        self.bob_offset = 0.0

    def update(self, base_speed):
        self.speed = base_speed * self.speed_multiplier
        self.x -= self.speed
        self.bob_offset = math.sin(pygame.time.get_ticks() * 0.005) * 2
        self.rect.topleft = (int(self.x), int(self.y))

    def offscreen(self):
        return self.x + self.w < 0

    def draw(self, surface):
        color = (128, 128, 128)
        rect = self.rect.copy()
        rect.y += self.bob_offset
        pygame.draw.rect(surface, color, rect, border_radius=5)

# ---------------- UI Helpers ----------------
def draw_text_center(surface, text, y, font, color=FG_COLOR):
    r = font.render(text, True, color)
    surface.blit(r, (WIDTH // 2 - r.get_width() // 2, y))

# ---------------- Name input screen ----------------
def name_input_screen():
    name = ""
    prompt = "Enter your name (max 12 chars)"
    input_box = pygame.Rect(WIDTH // 2 - 260, HEIGHT // 2 - 60, 520, 60)
    blink = True
    blink_timer = 0

    # On-screen keyboard
    keyboard_keys = [
        list("QWERTYUIOP"),
        list("ASDFGHJKL"),
        list("ZXCVBNM"),
    ]
    key_w, key_h = 64, 64
    key_margin = 10
    kb_top = HEIGHT // 2 + 40   # keyboard below input box

    # Start button above input box
    start_button = pygame.Rect(WIDTH // 2 - 120,
                               HEIGHT // 2 - 130,
                               240, 50)

    # Compute keyboard rects once
    keys_rects = []
    for row_idx, row in enumerate(keyboard_keys):
        row_y = kb_top + row_idx * (key_h + key_margin)
        total_w = len(row) * (key_w + key_margin) - key_margin
        start_x = WIDTH // 2 - total_w // 2
        for col_idx, ch in enumerate(row):
            rect = pygame.Rect(start_x + col_idx * (key_w + key_margin),
                               row_y, key_w, key_h)
            keys_rects.append((rect, ch))

    # Backspace key
    bs_rect = pygame.Rect(WIDTH // 2 - 100,
                          kb_top + 3 * (key_h + key_margin),
                          200, key_h)
    keys_rects.append((bs_rect, "BACK"))

    while True:
        dt = clock.tick(FPS)
        blink_timer += dt
        if blink_timer > 500:
            blink = not blink
            blink_timer = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if name.strip() == "":
                        name = "Player"
                    return name[:12]
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                else:
                    if len(name) < 12 and event.unicode.isprintable() and event.unicode.isalpha():
                        name += event.unicode.upper()  # Ensure uppercase for consistency
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if start_button.collidepoint(mx, my):
                    if name.strip() == "":
                        name = "Player"
                    return name[:12]
                # Check virtual keys
                for rect, ch in keys_rects:
                    if rect.collidepoint(mx, my):
                        if ch == "BACK":
                            name = name[:-1]
                        elif len(name) < 12:
                            name += ch

        # Draw UI
        screen.fill(BG_COLOR)
        draw_text_center(screen, "Pokémon Runner By Arjun", HEIGHT // 6, FONT_LG)
        draw_text_center(screen, prompt, HEIGHT // 6 + 48, FONT_SM)

        # Input box
        pygame.draw.rect(screen, (230, 230, 230), input_box, border_radius=10)
        pygame.draw.rect(screen, (200, 200, 200), input_box, 2, border_radius=10)
        name_s = FONT_MD.render(name, True, (20, 20, 20))
        screen.blit(name_s, (input_box.x + 12, input_box.y + (input_box.h - name_s.get_height()) // 2))
        # caret
        if blink:
            caret_x = input_box.x + 12 + name_s.get_width() + 2
            caret_y = input_box.y + 12
            pygame.draw.rect(screen, (20, 20, 20), (caret_x, caret_y, 2, input_box.h - 24))

        # start button
        pygame.draw.rect(screen, (66, 133, 244), start_button, border_radius=12)
        btn_text = FONT_MD.render("START", True, (255, 255, 255))
        screen.blit(btn_text, (start_button.centerx - btn_text.get_width() // 2,
                               start_button.centery - btn_text.get_height() // 2))

        # draw keyboard
        for rect, ch in keys_rects:
            if ch == "BACK":
                color = (255, 180, 180)
                txt = FONT_SM.render("⌫", True, (20, 20, 20))
            else:
                color = (230, 230, 230)
                txt = FONT_SM.render(ch, True, (20, 20, 20))
            pygame.draw.rect(screen, color, rect, border_radius=8)
            screen.blit(txt, (rect.centerx - txt.get_width() // 2,
                              rect.centery - txt.get_height() // 2))
            pygame.draw.rect(screen, (180, 180, 180), rect, 2, border_radius=8)

        pygame.display.flip()

# ---------------- Menu screen ----------------
def show_menu():
    start_rect = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2, 120, 50)
    cancel_rect = pygame.Rect(WIDTH // 2 + 30, HEIGHT // 2, 120, 50)

    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 'CANCEL'
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return 'CANCEL'
                elif event.key == pygame.K_RETURN:
                    return 'START'
            if event.type == pygame.MOUSEBUTTONDOWN:
                if start_rect.collidepoint(event.pos):
                    return 'START'
                if cancel_rect.collidepoint(event.pos):
                    return 'CANCEL'

        screen.fill(BG_COLOR)
        draw_text_center(screen, "Pokémon Runner", HEIGHT // 3, FONT_LG)
        draw_text_center(screen, "By Arjun", HEIGHT // 3 + 50, FONT_MD)

        # start button
        pygame.draw.rect(screen, (66, 133, 244), start_rect, border_radius=10)
        st_text = FONT_MD.render("START", True, FG_COLOR)
        screen.blit(st_text, (start_rect.centerx - st_text.get_width() // 2,
                              start_rect.centery - st_text.get_height() // 2))

        # cancel button
        pygame.draw.rect(screen, (200, 50, 50), cancel_rect, border_radius=10)
        ca_text = FONT_MD.render("CANCEL", True, FG_COLOR)
        screen.blit(ca_text, (cancel_rect.centerx - ca_text.get_width() // 2,
                              cancel_rect.centery - ca_text.get_height() // 2))

        pygame.display.flip()

# ---------------- Leaderboard display ----------------
def show_leaderboard(surface, y_top):
    lb = load_leaderboard()
    lines = format_leaderboard(lb)
    header = FONT_MD.render(f"Leaderboard (Top {MAX_LEADERBOARD})", True, FG_COLOR)
    surface.blit(header, (WIDTH // 2 - header.get_width() // 2, y_top))
    for i, line in enumerate(lines):
        txt = FONT_SM.render(line, True, FG_COLOR)
        surface.blit(txt, (WIDTH // 2 - txt.get_width() // 2, y_top + 40 + i * 28))

# ---------------- Main Game ----------------
def run_game(player_name):
    player = Player()
    enemies = []
    obstacles = []
    score = 0
    speed = START_SPEED
    spawn_timer = 0
    game_over = False
    score_saved = False
    menu_button = pygame.Rect(WIDTH - 100, 10, 80, 40)

    while True:
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 'QUIT'
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return 'MENU'
                elif event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    if game_over:
                        # restart
                        player.reset()
                        player.poke_id = random.randint(0, len(POKEMON_PATTERNS) - 1)
                        enemies.clear()
                        obstacles.clear()
                        score = 0
                        speed = START_SPEED
                        spawn_timer = 0
                        game_over = False
                        score_saved = False
                    else:
                        player.jump()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if not game_over and menu_button.collidepoint(mx, my):
                    return 'MENU'
                if game_over:
                    # restart
                    player.reset()
                    player.poke_id = random.randint(0, len(POKEMON_PATTERNS) - 1)
                    enemies.clear()
                    obstacles.clear()
                    score = 0
                    speed = START_SPEED
                    spawn_timer = 0
                    game_over = False
                    score_saved = False
                else:
                    player.jump()

        if not game_over:
            player.update()
            spawn_timer += dt
            base_interval = max(650, 1400 - (score // 200))  # Slightly faster spawning progression
            if spawn_timer > random.randint(int(base_interval), int(base_interval * 1.4)):
                if random.random() < 0.6:
                    enemies.append(Enemy(speed))
                else:
                    obstacles.append(Obstacle(speed))
                spawn_timer = 0

            speed = START_SPEED + (score // 200)  # Adjusted for smoother progression
            hit_played = False
            for e in enemies:
                e.update(speed)
                if player.rect.colliderect(e.rect) and not hit_played:
                    if 'hit' in sounds:
                        sounds['hit'].play()
                    hit_played = True
                    game_over = True
            for o in obstacles:
                o.update(speed)
                if player.rect.colliderect(o.rect) and not hit_played:
                    if 'hit' in sounds:
                        sounds['hit'].play()
                    hit_played = True
                    game_over = True

            enemies = [e for e in enemies if not e.offscreen()]
            obstacles = [o for o in obstacles if not o.offscreen()]
            score += 1  # Score per frame; consider score += dt / 1000 * 60 for time-based, but frame-based is fine for consistency

        # Drawing
        screen.fill(BG_COLOR)
        # Ground
        pygame.draw.rect(screen, (30, 30, 30), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
        pygame.draw.line(screen, GROUND_COLOR, (0, GROUND_Y), (WIDTH, GROUND_Y), max(2, int(HEIGHT * 0.003)))
        player.draw(screen)
        for e in enemies:
            e.draw(screen)
        for o in obstacles:
            o.draw(screen)

        score_text = FONT_SM.render(f"{player_name}  Score: {score}", True, FG_COLOR)
        screen.blit(score_text, (20, 18))
        if not game_over:
            # Menu button
            pygame.draw.rect(screen, (66, 133, 244), menu_button, border_radius=5)
            m_text = FONT_SM.render("MENU", True, (255, 255, 255))
            screen.blit(m_text, (menu_button.centerx - m_text.get_width() // 2,
                                 menu_button.centery - m_text.get_height() // 2))
            hint = FONT_SM.render("Esc/Menu=Menu  •  Space/Up/W/Tap=Jump", True, FG_COLOR)
            screen.blit(hint, (20, HEIGHT - 40))
        else:
            hint = FONT_SM.render("Esc=Menu  •  Space/Tap=Restart", True, FG_COLOR)
            screen.blit(hint, (20, HEIGHT - 40))

        if game_over:
            if not score_saved:
                add_score(player_name, score)
                score_saved = True

            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((55, 55, 55, 220))
            screen.blit(overlay, (0, 0))
            draw_text_center(screen, "Game Over! :(", HEIGHT // 4, FONT_LG)
            draw_text_center(screen, f"{player_name}'s Score: {score}", HEIGHT // 4 + 60, FONT_MD)
            draw_text_center(screen, "Tap / Space to Restart", HEIGHT // 4 + 110, FONT_SM)

            lb_y = HEIGHT // 2 - 20
            show_leaderboard(screen, lb_y)

        pygame.display.flip()

# ---------------- Entry Point ----------------
def main():
    try:
        player_name = name_input_screen()
        while True:
            choice = show_menu()
            if choice == 'CANCEL':
                break
            result = run_game(player_name)
            if result == 'QUIT':
                break
            # If 'MENU', loop back to show_menu
    except SystemExit:
        pass
    finally:
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()
