import pygame
import random
import math
import sys
import os
import pandas as pd

# --- PYGAME & FONT INITIALIZATION ---
pygame.init()
pygame.font.init()
pygame.mixer.init()

# --- SCREEN & CONSTANTS ---
WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Data-Driven 3v3 Soccer Simulator (v21 - Weather & xG)")

# COLORS
GREEN = (34, 139, 34); WHITE = (255, 255, 255); BLUE = (0, 0, 255); RED = (255, 0, 0); BLACK = (0, 0, 0); GOLD = (255, 215, 0); ORANGE = (255, 165, 0); YELLOW = (255, 255, 0)
GRAY = (100, 100, 100); DARK_GREEN = (0, 80, 0); PURPLE = (128, 0, 128)
SKIN_TONE_LIGHT = (234, 192, 134); SKIN_TONE_MEDIUM = (197, 140, 89); SKIN_TONE_DARK = (141, 85, 36)
RACE_SKIN_MAP = {"White": SKIN_TONE_LIGHT, "Hispanic": SKIN_TONE_MEDIUM, "Black": SKIN_TONE_DARK, "Asian": SKIN_TONE_LIGHT}
DEFAULT_SKIN_TONE = SKIN_TONE_MEDIUM
TEXT_BG_COLOR = (0, 0, 0, 128); TACKLE_INDICATOR_COLOR = (255, 255, 0, 100)
CARD_COLOR = (0, 50, 100); CARD_HOVER_COLOR = (0, 80, 150); CARD_SELECTED_COLOR = GOLD

# UI COLORS
STAT_ELITE = (57, 255, 20)    
STAT_GOOD = (50, 205, 50)     
STAT_AVG = (255, 215, 0)      
STAT_POOR = (255, 140, 0)     
STAT_BAD = (220, 20, 60)      
STAT_BG = (40, 40, 60)        

# TRAIT VISUAL CONFIG
TRAIT_COLORS = {
    "SPEED_DEMON": (0, 255, 255), 
    "BULLDOZER": (139, 69, 19),   
    "SNIPER": (255, 0, 0),        
    "MAGNET": (255, 0, 255),      
    "INTERCEPTOR": (255, 255, 0)  
}

# TEAM COLORS
TEAM_COLORS = {
    'lafc': (0, 0, 0),             
    'la_galaxy': (255, 255, 255),  
    'inter_miami': (247, 0, 136), 
    'columbus_crew': (255, 255, 0), 
    'cincinnati': (0, 24, 107),     
    'seattle_sounders': (93, 151, 50), 
    'charlotte_fc': (0, 168, 224),     
    'minnesota_united': (155, 165, 175), 
    'san_jose_earthquakes': (0, 102, 204), 
    'philadelphia_union': (23, 72, 155), 
    'default_player': (0, 0, 255),  
    'default_ai': (255, 0, 0)        
}

# GAME SETTINGS
FPS = 60
BASE_PLAYER_SPEED = 3.5
PACE_MODIFIER = 0.15
BALL_SPEED = 11; GOAL_WIDTH = 200; GOAL_Y_START = HEIGHT // 2 - GOAL_WIDTH // 2
GAME_DURATION_SECONDS = 60; TACKLE_RADIUS = 40
DRIBBLE_DISTANCE = 30; DRIBBLE_SPEED = 0.15
PASS_COMPLETION_TIME_LIMIT = 1000
SUPER_ARMOR_DURATION = 60
BASE_PLAYER_HEIGHT_CM = 175
AVERAGE_PACE = 12

# FONT HELPER
def get_font(size, bold=False):
    custom_font_path = os.path.join('assets', 'font.ttf')
    if os.path.exists(custom_font_path):
        return pygame.font.Font(custom_font_path, size)
    return pygame.font.SysFont("Arial", size, bold=bold)

# DATA LOADING
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, 'player_profiles.csv')
    player_profiles_df = pd.read_csv(file_path)
    player_profiles_df.fillna({
        'Height': BASE_PLAYER_HEIGHT_CM, 'Weight': 75, 'Race': 'Unknown',
        'Position': 'MF', 'Preferred Foot': 'Right', 'Pace': AVERAGE_PACE
    }, inplace=True)
except FileNotFoundError:
    print(f"FATAL ERROR: '{file_path}' not found.")
    sys.exit()
except KeyError as e:
    print(f"FATAL ERROR: CSV file is missing a required column: {e}.")
    sys.exit()

# --- ASSET LOADING ---
def load_sound(name):
    path = os.path.join('assets', name)
    if not os.path.exists(path): path = name
    if not os.path.exists(path):
        class DummySound:
            def play(self): pass
        return DummySound()
    return pygame.mixer.Sound(path)
kick_sound, goal_sound, whistle_sound, tackle_sound = load_sound('kick.wav'), load_sound('goal.wav'), load_sound('whistle.wav'), load_sound('tackle.wav')

# --- WEATHER SYSTEM CLASS ---
class WeatherManager:
    def __init__(self, mode="CLEAR"):
        self.mode = mode
        self.particles = []
        # Physics Modifiers
        if self.mode == "RAIN":
            self.friction = 0.99  # Slippery ball (travels further)
            self.player_accel = 0.9 # Harder to turn
            self.sky_overlay = (0, 0, 50, 30) # Dark Blue tint
        elif self.mode == "SNOW":
            self.friction = 0.94  # High friction (ball stops fast)
            self.player_accel = 0.8 # Sluggish movement
            self.sky_overlay = (200, 200, 200, 30) # Grey tint
        else: # CLEAR
            self.friction = 0.97  # Standard friction
            self.player_accel = 1.0
            self.sky_overlay = None

        # Init Particles
        if self.mode != "CLEAR":
            for _ in range(100):
                self.particles.append(self.create_particle())

    def create_particle(self):
        return {
            'x': random.randint(0, WIDTH),
            'y': random.randint(0, HEIGHT),
            'speed': random.randint(5, 10) if self.mode == "RAIN" else random.randint(1, 3),
            'length': random.randint(10, 20) if self.mode == "RAIN" else 3
        }

    def update(self):
        if self.mode == "CLEAR": return
        for p in self.particles:
            p['y'] += p['speed']
            if self.mode == "RAIN": p['x'] -= 1 # Slant
            if p['y'] > HEIGHT:
                p['y'] = -10
                p['x'] = random.randint(0, WIDTH)

    def draw(self, screen):
        if self.mode == "CLEAR": return
        
        # Draw Overlay
        if self.sky_overlay:
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            s.fill(self.sky_overlay)
            screen.blit(s, (0,0))

        # Draw Particles
        for p in self.particles:
            if self.mode == "RAIN":
                pygame.draw.line(screen, (200, 200, 255), (p['x'], p['y']), (p['x']-2, p['y']+p['length']), 1)
            elif self.mode == "SNOW":
                pygame.draw.circle(screen, WHITE, (p['x'], int(p['y'])), 2)

# --- UI CLASSES ---
class Button:
    def __init__(self, x, y, width, height, text, color, hover_color, font_size=30):
        self.rect, self.text, self.color, self.hover_color, self.font = pygame.Rect(x, y, width, height), text, color, hover_color, get_font(font_size, True)
        self.is_hovered = False
        self.original_y = y 

    def draw(self, screen, scroll_offset=0):
        draw_rect = self.rect.move(0, -scroll_offset)
        if draw_rect.bottom < 0 or draw_rect.top > HEIGHT: return

        draw_color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, draw_color, draw_rect, border_radius=10)
        pygame.draw.rect(screen, (255,255,255, 50), draw_rect, 2, border_radius=10)
        
        text_surf = self.font.render(self.text, True, WHITE)
        screen.blit(text_surf, text_surf.get_rect(center=draw_rect.center))

    def check_hover(self, mouse_pos, scroll_offset=0):
        check_rect = self.rect.move(0, -scroll_offset)
        self.is_hovered = check_rect.collidepoint(mouse_pos)

    def is_clicked(self, event, scroll_offset=0):
        return self.is_hovered and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1

class PlayerCard:
    def __init__(self, x, y, width, height, player_data):
        self.rect = pygame.Rect(x, y, width, height)
        self.player_data = player_data; self.name = player_data['Player']
        self.stats = player_data[['Position', 'Pace', 'Shooting', 'Dribbling', 'Passing', 'Defense']]
        self.is_hovered = False
        self.name_font = get_font(11, True); self.stat_font = get_font(12)
        
    def draw(self, screen, is_selected, scroll_offset=0):
        draw_rect = self.rect.move(0, -scroll_offset)
        if draw_rect.bottom < 0 or draw_rect.top > HEIGHT: return

        if is_selected: pygame.draw.rect(screen, CARD_SELECTED_COLOR, draw_rect, 4, border_radius=12)
        bg_color = CARD_HOVER_COLOR if self.is_hovered else CARD_COLOR
        pygame.draw.rect(screen, bg_color, draw_rect.inflate(-8, -8), border_radius=8)
        
        name_surf = self.name_font.render(self.name, True, WHITE)
        pos_surf = self.stat_font.render(self.stats['Position'], True, GOLD)
        screen.blit(name_surf, (draw_rect.x + 10, draw_rect.y + 10))
        screen.blit(pos_surf, (draw_rect.x + draw_rect.width - 35, draw_rect.y + 12))
        
        y_offset = 40
        stats_to_show = {'Pace': self.stats['Pace'], 'Sht': self.stats['Shooting'], 'Pas': self.stats['Passing'], 'Dri': self.stats['Dribbling'], 'Def': self.stats['Defense']}
        
        for label, value in stats_to_show.items():
            lbl_surf = self.stat_font.render(label, True, (200, 200, 200))
            screen.blit(lbl_surf, (draw_rect.x + 12, draw_rect.y + y_offset))
            
            bar_w, bar_h = 70, 6
            bar_x = draw_rect.x + 50
            bar_y = draw_rect.y + y_offset + 4
            pygame.draw.rect(screen, STAT_BG, (bar_x, bar_y, bar_w, bar_h))
            
            safe_val = min(max(value, 0), 20)
            fill_w = int((safe_val / 20.0) * bar_w)
            
            if safe_val >= 18: c = STAT_ELITE
            elif safe_val >= 15: c = STAT_GOOD
            elif safe_val >= 10: c = STAT_AVG
            elif safe_val >= 5: c = STAT_POOR
            else: c = STAT_BAD
            
            pygame.draw.rect(screen, c, (bar_x, bar_y, fill_w, bar_h))
            y_offset += 18
            
    def check_hover(self, mouse_pos, scroll_offset=0):
        check_rect = self.rect.move(0, -scroll_offset)
        self.is_hovered = check_rect.collidepoint(mouse_pos)
        
    def is_clicked(self, event): 
        return self.is_hovered and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1

class Particle:
    def __init__(self, x, y, color, size_max=8):
        self.x, self.y, self.color = x, y, color; self.size = random.randint(4, size_max); self.life = 20; self.vx = random.uniform(-1, 1); self.vy = random.uniform(-1, 1)
    def update(self): self.x += self.vx; self.y += self.vy; self.size *= 0.9; self.life -= 1
    def draw(self, screen):
        if self.life > 0 and self.size > 1:
            s = pygame.Surface((int(self.size*2), int(self.size*2)), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, 150), (int(self.size), int(self.size)), int(self.size))
            screen.blit(s, (self.x - self.size, self.y - self.size))

# --- SEASON / LEAGUE CLASS ---
class Season:
    def __init__(self, user_team, all_teams):
        self.user_team = user_team
        self.teams = all_teams 
        self.schedule = [] 
        self.current_round_idx = 0
        self.standings = {team: {'GP': 0, 'W': 0, 'D': 0, 'L': 0, 'GF': 0, 'GA': 0, 'GD': 0, 'Pts': 0} for team in self.teams}
        self.season_over = False
        self.generate_schedule()

    def generate_schedule(self):
        teams_copy = self.teams[:]
        if len(teams_copy) % 2 != 0: teams_copy.append("BYE")
        n = len(teams_copy)
        for round_num in range(n - 1):
            round_matches = []
            for i in range(n // 2):
                t1 = teams_copy[i]
                t2 = teams_copy[n - 1 - i]
                if t1 != "BYE" and t2 != "BYE":
                    round_matches.append((t1, t2))
            self.schedule.append(round_matches)
            teams_copy.insert(1, teams_copy.pop())

    def get_current_round_match(self):
        if self.season_over: return None
        matches = self.schedule[self.current_round_idx]
        for match in matches:
            if self.user_team in match:
                opponent = match[0] if match[1] == self.user_team else match[1]
                return opponent
        return None

    def simulate_ai_matches(self):
        if self.season_over: return
        matches = self.schedule[self.current_round_idx]
        for t1, t2 in matches:
            if self.user_team not in (t1, t2):
                s1 = random.randint(0, 3)
                s2 = random.randint(0, 3)
                self.update_stats(t1, s1, t2, s2)

    def record_user_result(self, user_goals, ai_goals, ai_team):
        self.update_stats(self.user_team, user_goals, ai_team, ai_goals)
        self.simulate_ai_matches()
        self.current_round_idx += 1
        if self.current_round_idx >= len(self.schedule):
            self.season_over = True

    def update_stats(self, t1, s1, t2, s2):
        self.standings[t1]['GP'] += 1; self.standings[t1]['GF'] += s1; self.standings[t1]['GA'] += s2; self.standings[t1]['GD'] += (s1 - s2)
        if s1 > s2: self.standings[t1]['W'] += 1; self.standings[t1]['Pts'] += 3
        elif s1 == s2: self.standings[t1]['D'] += 1; self.standings[t1]['Pts'] += 1
        else: self.standings[t1]['L'] += 1
        self.standings[t2]['GP'] += 1; self.standings[t2]['GF'] += s2; self.standings[t2]['GA'] += s1; self.standings[t2]['GD'] += (s2 - s1)
        if s2 > s1: self.standings[t2]['W'] += 1; self.standings[t2]['Pts'] += 3
        elif s2 == s1: self.standings[t2]['D'] += 1; self.standings[t2]['Pts'] += 1
        else: self.standings[t2]['L'] += 1

    def draw_standings(self, screen):
        screen.fill(BLACK)
        sorted_teams = sorted(self.standings.keys(), key=lambda t: (self.standings[t]['Pts'], self.standings[t]['GD'], self.standings[t]['GF']), reverse=True)
        header_font = get_font(36, True); row_font = get_font(28)
        title = get_font(50, True).render(f"LEAGUE TABLE - ROUND {self.current_round_idx + 1}/{len(self.schedule)}", True, GOLD)
        if self.season_over: title = get_font(50, True).render("FINAL STANDINGS", True, GOLD)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 30))
        headers = ["Rank", "Team", "P", "W", "D", "L", "GD", "Pts"]
        x_offsets = [50, 120, 450, 520, 590, 660, 730, 850]
        pygame.draw.line(screen, WHITE, (40, 80), (WIDTH-40, 80), 2)
        for i, h in enumerate(headers): screen.blit(header_font.render(h, True, WHITE), (x_offsets[i], 50))
        y = 100
        for idx, team in enumerate(sorted_teams):
            stats = self.standings[team]; color = GOLD if team == self.user_team else WHITE
            bg_rect = pygame.Rect(40, y-5, WIDTH-80, 30)
            if team == self.user_team: pygame.draw.rect(screen, (50, 50, 50), bg_rect)
            vals = [str(idx + 1), team.replace('_', ' ').title(), str(stats['GP']), str(stats['W']), str(stats['D']), str(stats['L']), str(stats['GD']), str(stats['Pts'])]
            for i, val in enumerate(vals):
                render_color = color
                if i == 1: 
                    team_c = TEAM_COLORS.get(team, WHITE)
                    if team_c != (0,0,0) and team_c != WHITE: render_color = team_c
                txt = row_font.render(val, True, render_color); screen.blit(txt, (x_offsets[i], y))
            y += 40
        if not self.season_over:
            next_opp = self.get_current_round_match()
            if next_opp:
                info_rect = pygame.Rect(WIDTH//2 - 250, HEIGHT - 80, 500, 60)
                pygame.draw.rect(screen, (20, 20, 20), info_rect, border_radius=10); pygame.draw.rect(screen, GOLD, info_rect, 2, border_radius=10)
                info_text = row_font.render(f"NEXT MATCH VS: {next_opp.replace('_', ' ').title()}", True, WHITE); screen.blit(info_text, (WIDTH//2 - info_text.get_width()//2, HEIGHT - 60))

# --- TOURNAMENT CLASS ---
class Tournament:
    def __init__(self, user_team, ai_teams):
        self.user_team = user_team
        self.all_teams = [user_team] + ai_teams[:3] 
        random.shuffle(self.all_teams) 
        self.semi_finals = [ [self.all_teams[0], self.all_teams[1]], [self.all_teams[2], self.all_teams[3]] ]
        self.final = [None, None] 
        self.champion = None
        self.current_round = "SEMI" 
        self.user_status = "ALIVE" 

    def get_opponent(self):
        if self.current_round == "SEMI":
            if self.user_team in self.semi_finals[0]: return self.semi_finals[0][0] if self.semi_finals[0][1] == self.user_team else self.semi_finals[0][1]
            else: return self.semi_finals[1][0] if self.semi_finals[1][1] == self.user_team else self.semi_finals[1][1]
        elif self.current_round == "FINAL":
            return self.final[0] if self.final[1] == self.user_team else self.final[1]
        return None

    def advance_tournament(self, user_won):
        if self.current_round == "SEMI":
            if user_won:
                if self.user_team in self.semi_finals[0]: self.final[0] = self.user_team
                else: self.final[1] = self.user_team
            else:
                self.user_status = "ELIMINATED"
                opponent = self.get_opponent()
                if self.user_team in self.semi_finals[0]: self.final[0] = opponent
                else: self.final[1] = opponent

            other_match_idx = 1 if self.user_team in self.semi_finals[0] else 0
            other_match = self.semi_finals[other_match_idx]
            winner = random.choice(other_match) 
            if other_match_idx == 0: self.final[0] = winner
            else: self.final[1] = winner
            
            if self.user_status == "ALIVE":
                self.current_round = "FINAL"
        
        elif self.current_round == "FINAL":
            if user_won: self.user_status = "CHAMPION"; self.champion = self.user_team
            else: self.user_status = "ELIMINATED"; self.champion = self.get_opponent()

    def draw_bracket(self, screen):
        screen.fill(BLACK)
        font = get_font(40); small_font = get_font(30)
        title = get_font(60, True).render("MLS CUP BRACKET", True, GOLD); screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
        t1 = self.semi_finals[0][0].replace('_', ' ').title(); t2 = self.semi_finals[0][1].replace('_', ' ').title()
        color1 = GOLD if self.semi_finals[0][0] == self.user_team else WHITE; color2 = GOLD if self.semi_finals[0][1] == self.user_team else WHITE
        pygame.draw.line(screen, WHITE, (150, 200), (300, 200), 2); pygame.draw.line(screen, WHITE, (150, 400), (300, 400), 2); pygame.draw.line(screen, WHITE, (300, 200), (300, 400), 2); pygame.draw.line(screen, WHITE, (300, 300), (400, 300), 2) 
        screen.blit(small_font.render(t1, True, color1), (50, 190)); screen.blit(small_font.render(t2, True, color2), (50, 390))
        t3 = self.semi_finals[1][0].replace('_', ' ').title(); t4 = self.semi_finals[1][1].replace('_', ' ').title()
        color3 = GOLD if self.semi_finals[1][0] == self.user_team else WHITE; color4 = GOLD if self.semi_finals[1][1] == self.user_team else WHITE
        pygame.draw.line(screen, WHITE, (850, 200), (700, 200), 2); pygame.draw.line(screen, WHITE, (850, 400), (700, 400), 2); pygame.draw.line(screen, WHITE, (700, 200), (700, 400), 2); pygame.draw.line(screen, WHITE, (700, 300), (600, 300), 2)
        screen.blit(small_font.render(t3, True, color3), (710, 190)); screen.blit(small_font.render(t4, True, color4), (710, 390))
        final_rect = pygame.Rect(400, 250, 200, 100)
        pygame.draw.rect(screen, (50, 50, 50), final_rect, border_radius=10); pygame.draw.rect(screen, GOLD, final_rect, 2, border_radius=10)
        if self.final[0]:
            f1 = self.final[0].replace('_', ' ').title(); c1 = GOLD if self.final[0] == self.user_team else WHITE
            screen.blit(small_font.render(f1, True, c1), (420, 270)); screen.blit(small_font.render("VS", True, ORANGE), (490, 300))
        if self.final[1]:
            f2 = self.final[1].replace('_', ' ').title(); c2 = GOLD if self.final[1] == self.user_team else WHITE
            screen.blit(small_font.render(f2, True, c2), (420, 330))
        if self.champion:
            champ_text = get_font(80, True).render(f"CHAMPION: {self.champion.replace('_',' ').title()}", True, GOLD)
            screen.blit(champ_text, (WIDTH//2 - champ_text.get_width()//2, 550))

# --- GAME OBJECT CLASSES ---
class Player:
    def __init__(self, x, y, team_name, name, stats_dict):
        self.x, self.y, self.name, self.stats = x, y, name, stats_dict
        self.team_name = team_name
        if 'ai' in team_name: self.color = TEAM_COLORS.get(team_name, TEAM_COLORS['default_ai'])
        else: self.color = TEAM_COLORS.get(team_name, TEAM_COLORS['default_player'])
        self.height_cm = self.stats.get('Height', BASE_PLAYER_HEIGHT_CM); self.weight_kg = self.stats.get('Weight', 75); self.race = self.stats.get('Race', 'Unknown')
        self.skin_tone = RACE_SKIN_MAP.get(self.race, DEFAULT_SKIN_TONE); self.height_scale = self.height_cm / BASE_PLAYER_HEIGHT_CM
        base_head_radius = 8; base_body_width, base_body_height = 18, 25; base_leg_width, base_leg_height = 6, 15; base_arm_width, base_arm_height = 4, 18
        self.head_radius = int(base_head_radius * (1 + (self.height_scale - 1) * 0.5)); self.body_width = int(base_body_width * (1 + (self.height_scale - 1) * 0.2)); self.body_height = int(base_body_height * self.height_scale)
        self.leg_width = int(base_leg_width * (1 + (self.height_scale - 1) * 0.2)); self.leg_height = int(base_leg_height * self.height_scale); self.arm_width = int(base_arm_width * (1 + (self.height_scale - 1) * 0.2)); self.arm_height = int(base_arm_height * self.height_scale)
        total_width = self.body_width + 2 * self.arm_width; total_height = self.head_radius * 2 + self.body_height + self.leg_height
        self.rect = pygame.Rect(x - total_width//2, y - self.head_radius, total_width, total_height)
        self.stamina, self.max_stamina = 100, 100; self.is_pressing = False
        self.direction_vector = pygame.Vector2(0, 0); self.home_position = pygame.Vector2(x, y); self.font = get_font(14); self.goals = 0; self.super_armor_timer = 0
        self.position = self.stats.get('Position', 'MF'); self.pace = self.stats.get('Pace', AVERAGE_PACE)
        self.attack_direction = 1 if self.home_position.x < WIDTH / 2 else -1
        self.pass_cooldown = 0
        self.traits = []
        if self.weight_kg > 80: self.traits.append("BULLDOZER")         
        if self.stats.get('Defense', 0) >= 15 and self.height_cm > 182: self.traits.append("INTERCEPTOR") 
        if self.pace >= 15: self.traits.append("SPEED_DEMON")           
        if self.stats.get('Shooting', 0) >= 15: self.traits.append("SNIPER") 
        if self.stats.get('Dribbling', 0) >= 16: self.traits.append("MAGNET") 

    def get_pos(self): return pygame.Vector2(self.x, self.y)
    
    def move(self, keys, ball_owner, weather_accel_mod=1.0): # Update acceleration
        sprinting = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        speed_multiplier = 1.0
        if not ball_owner and self.stats.get('Dribbling', 0) >= 15 and self.stats.get('Passing', 0) >= 10: speed_multiplier = 1.35 
        calculated_speed = BASE_PLAYER_SPEED + (self.pace * PACE_MODIFIER)
        current_speed = calculated_speed * speed_multiplier * (1.5 if sprinting and self.stamina > 0 else 1) * weather_accel_mod # Apply weather
        self.direction_vector.x = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]; self.direction_vector.y = keys[pygame.K_DOWN] - keys[pygame.K_UP]
        if self.direction_vector.length() > 0: self.direction_vector.normalize_ip()
        self.x += self.direction_vector.x * current_speed; self.y += self.direction_vector.y * current_speed
        if sprinting and self.stats.get('Dribbling', 0) >= 18 and self.super_armor_timer <= 0: self.super_armor_timer = SUPER_ARMOR_DURATION
        if self.super_armor_timer > 0: self.super_armor_timer -= 1
        if sprinting and self.stamina > 0: 
            cost = 0.5 if "SPEED_DEMON" in self.traits else 1.0
            self.stamina -= cost
        elif self.stamina < self.max_stamina: self.stamina += 0.3
        half_total_width = (self.body_width + 2 * self.arm_width) // 2; bottom_y_offset = self.body_height + self.leg_height
        self.x = max(half_total_width, min(WIDTH - half_total_width, self.x)); self.y = max(self.head_radius, min(HEIGHT - bottom_y_offset, self.y))
        self.rect.center = (self.x, self.y - self.head_radius + self.rect.height // 2)

    def draw(self, screen):
        head_pos = (int(self.x), int(self.y)); torso_rect = pygame.Rect(self.x - self.body_width // 2, self.y + self.head_radius, self.body_width, self.body_height); leg_y = torso_rect.bottom
        left_leg_rect = pygame.Rect(self.x - self.body_width // 2, leg_y, self.leg_width, self.leg_height); right_leg_rect = pygame.Rect(self.x + self.body_width // 2 - self.leg_width, leg_y, self.leg_width, self.leg_height); arm_y = torso_rect.top + 3
        left_arm_rect = pygame.Rect(torso_rect.left - self.arm_width, arm_y, self.arm_width, self.arm_height); right_arm_rect = pygame.Rect(torso_rect.right, arm_y, self.arm_width, self.arm_height)
        pygame.draw.rect(screen, self.color, torso_rect); pygame.draw.rect(screen, self.color, left_leg_rect); pygame.draw.rect(screen, self.color, right_leg_rect); pygame.draw.rect(screen, self.color, left_arm_rect); pygame.draw.rect(screen, self.color, right_arm_rect)
        pygame.draw.circle(screen, self.skin_tone, head_pos, self.head_radius)
        
        # Name Tag
        name_surf = self.font.render(self.name, True, WHITE); bg_rect = name_surf.get_rect(center=(int(self.x), int(self.y - self.head_radius - 10))); bg_surface = pygame.Surface((bg_rect.width+4, bg_rect.height+4), pygame.SRCALPHA); bg_surface.fill(TEXT_BG_COLOR); screen.blit(bg_surface, (bg_rect.left - 2, bg_rect.top - 2)); screen.blit(name_surf, bg_rect)
        
        # Floating Stamina Bar
        if self.stamina < self.max_stamina:
            sb_w, sb_h = 30, 4
            sb_x = self.x - sb_w // 2
            sb_y = self.y - self.head_radius - 20
            pygame.draw.rect(screen, (50, 50, 50), (sb_x, sb_y, sb_w, sb_h))
            fill_pct = self.stamina / self.max_stamina
            color = GREEN if fill_pct > 0.5 else (RED if fill_pct < 0.2 else ORANGE)
            pygame.draw.rect(screen, color, (sb_x, sb_y, int(sb_w * fill_pct), sb_h))

        if self.is_pressing: press_indicator_center = (int(self.x), int(self.y + self.body_height + self.leg_height + 10)); pygame.draw.circle(screen, TACKLE_INDICATOR_COLOR, press_indicator_center, 15, 3)
        if self.super_armor_timer > 0: pygame.draw.circle(screen, GOLD, (int(self.x), int(self.y)), 30, 2)
        
        # Trait Icons
        pip_x = self.rect.centerx - ((len(self.traits) * 12) // 2); pip_y = self.rect.top - 18
        for trait in self.traits:
            c = TRAIT_COLORS.get(trait, WHITE)
            if trait == "SPEED_DEMON": pygame.draw.polygon(screen, c, [(pip_x, pip_y-4), (pip_x-4, pip_y+4), (pip_x+4, pip_y+4)])
            elif trait == "BULLDOZER": pygame.draw.rect(screen, c, (pip_x-4, pip_y-4, 8, 8))
            elif trait == "SNIPER": 
                pygame.draw.circle(screen, c, (pip_x, pip_y), 5, 1)
                pygame.draw.circle(screen, c, (pip_x, pip_y), 2)
            elif trait == "MAGNET": pygame.draw.polygon(screen, c, [(pip_x, pip_y-5), (pip_x+5, pip_y), (pip_x, pip_y+5), (pip_x-5, pip_y)])
            elif trait == "INTERCEPTOR": pygame.draw.polygon(screen, c, [(pip_x-4, pip_y-2), (pip_x+4, pip_y-2), (pip_x+4, pip_y+2), (pip_x, pip_y+5), (pip_x-4, pip_y+2)])
            else: pygame.draw.circle(screen, c, (pip_x, pip_y), 4)
            pip_x += 12

    def reset(self): self.x, self.y = self.home_position.x, self.home_position.y; self.rect.center = (self.x, self.y - self.head_radius + self.rect.height // 2) ; self.stamina = self.max_stamina; self.super_armor_timer = 0; self.pass_cooldown = 0
    
    def tackle(self, ball, opponent_team):
        target_player = ball.owner
        effective_radius = TACKLE_RADIUS * 1.4 if "INTERCEPTOR" in self.traits else TACKLE_RADIUS
        if target_player in opponent_team and self.get_pos().distance_to(target_player.get_pos()) < effective_radius:
            tackle_success_prob = 1.0 if self.stats.get('Defense', 0) >= 18 else (self.stats.get('Defense', 10) / 20) * 0.7
            if "BULLDOZER" in target_player.traits: tackle_success_prob *= 0.6 
            if hasattr(target_player, 'super_armor_timer') and target_player.super_armor_timer > 0: tackle_success_prob = 0
            if random.random() < tackle_success_prob: tackle_sound.play(); ball.owner = None; ball.last_toucher = self; ball.last_touch_time = pygame.time.get_ticks()
    
    def update_ai_movement(self, ball, team_has_ball, target_override=None, sprint_override=False, weather_accel_mod=1.0):
        speed_multiplier = 1.0
        if not team_has_ball and self.stats.get('Dribbling', 0) >= 15 and self.stats.get('Passing', 0) >= 10: speed_multiplier = 1.35
        base_def_x = 200 if self.attack_direction == 1 else WIDTH - 200
        base_mid_x = 400 if self.attack_direction == 1 else WIDTH - 400
        base_fwd_x = 600 if self.attack_direction == 1 else WIDTH - 600
        if target_override: target_pos = target_override
        elif team_has_ball: 
            if self.position == 'FW': target_pos = pygame.Vector2(base_fwd_x + (100 * self.attack_direction), self.home_position.y)
            elif self.position == 'MF': target_pos = pygame.Vector2(base_mid_x, self.home_position.y)
            else: target_pos = pygame.Vector2(base_def_x, self.home_position.y)
        else: 
            if self.position == 'FW': target_pos = self.home_position.lerp(pygame.Vector2(ball.x, ball.y), 0.2)
            elif self.position == 'MF': target_pos = self.home_position.lerp(pygame.Vector2(ball.x, ball.y), 0.5)
            else: target_pos = self.home_position.lerp(pygame.Vector2(ball.x, ball.y), 0.7)
        direction = target_pos - self.get_pos()
        if direction.length() > 20:
            direction.normalize_ip()
            calculated_speed = (BASE_PLAYER_SPEED + (self.pace * PACE_MODIFIER)) * 0.8
            if sprint_override:
                calculated_speed *= 1.25 
                if self.stamina > 0: self.stamina -= 0.5
            current_speed = calculated_speed * speed_multiplier * weather_accel_mod
            self.x += direction.x * current_speed; self.y += direction.y * current_speed
            self.rect.center = (self.x, self.y - self.head_radius + self.rect.height // 2)

class AIPlayer(Player):
    def update(self, ball, player_team, ai_team, is_presser, game_stats, weather_accel_mod, xG_tracker):
        self.is_pressing = is_presser
        if self.pass_cooldown > 0: self.pass_cooldown -= 1
        if ball.owner == self:
            target_goal_x = WIDTH - 15 if self.attack_direction == 1 else 15
            goal_center = pygame.Vector2(target_goal_x, HEIGHT/2)
            dist_to_goal = self.get_pos().distance_to(goal_center)
            w_shoot = self.stats.get('Shooting', 10); w_pass = self.stats.get('Passing', 10); w_dribble = self.stats.get('Dribbling', 10)
            if self.pass_cooldown > 0 and dist_to_goal > 250: w_pass = 0; w_shoot = 0; w_dribble = 100
            if dist_to_goal < 250: w_shoot *= 10; w_pass *= 0.1; w_dribble *= 0.5
            elif dist_to_goal < 450: w_shoot *= 2; w_dribble *= 2.5; w_pass *= 1.2
            else: w_dribble *= 1.5; w_pass *= 1.0
            action = random.choices(['shoot', 'pass', 'dribble'], weights=[w_shoot, w_pass, w_dribble], k=1)[0]
            if action == "shoot" and dist_to_goal < 400:
                game_stats["AI"]["Shots"] += 1; shot_angle = math.atan2(goal_center.y-self.y, goal_center.x-self.x); shot_prob = 0.8; speed = BALL_SPEED; spin = 0
                foot = self.stats.get('Preferred Foot', 'Right')
                if self.stats.get('Shooting', 0) >= 15 and self.stats.get('Passing', 0) >= 12: 
                    shot_prob += 0.15
                    if foot == 'Right': spin = -0.3
                    elif foot == 'Left': spin = 0.3
                    elif foot == 'Both': spin = random.choice([-0.3, 0.3])
                if "SNIPER" in self.traits: speed *= 1.2
                if self.stats.get('Shooting', 0) >= 18: speed *= 1.5
                shot_prob_final = (self.stats.get('Shooting', 10)/20) * shot_prob
                
                # Update xG
                xG_tracker['AI'] += shot_prob_final
                
                target_y_on_goal_line = self.y + math.sin(shot_angle) * abs(target_goal_x - self.x)
                if GOAL_Y_START < target_y_on_goal_line < GOAL_Y_START + GOAL_WIDTH: game_stats["AI"]["ShotsOnGoal"] += 1
                if random.random() > shot_prob_final: shot_angle += random.uniform(-0.4, 0.4)
                ball.shoot(shot_angle, speed, spin_effect=spin); return
            elif action == "pass":
                game_stats["AI"]["PassesAttempted"] += 1
                teammate = find_best_pass_target(self, ai_team, player_team, exclude_player=ball.last_toucher) 
                angle = 0; pass_prob = 0.95
                if teammate: angle = math.atan2(teammate.y - self.y, teammate.x - self.x)
                if self.stats.get('Passing', 0) >= 18: pass_prob = 1.0
                pass_prob_final = (self.stats.get('Passing', 10)/20) * pass_prob
                if random.random() > pass_prob_final: angle += random.uniform(-0.5, 0.5)
                if teammate: ball.shoot(angle, BALL_SPEED * 0.8); return
                else: self.update_ai_movement(ball, True, goal_center, weather_accel_mod=weather_accel_mod)
            self.update_ai_movement(ball, True, goal_center, weather_accel_mod=weather_accel_mod)
        else:
            if is_presser: 
                self.update_ai_movement(ball, False, pygame.Vector2(ball.x, ball.y), sprint_override=True, weather_accel_mod=weather_accel_mod); self.tackle(ball, player_team)
            else: self.update_ai_movement(ball, False, weather_accel_mod=weather_accel_mod)
        self.rect.center = (self.x, self.y - self.head_radius + self.rect.height // 2)

class Goalkeeper(Player):
    def __init__(self, x, y, team_name):
        super().__init__(x, y, team_name, "GK", {})
        self.width, self.height = 15, 60
        self.rect = pygame.Rect(x - self.width//2, y - self.height//2, self.width, self.height)
        self.skin_tone = DEFAULT_SKIN_TONE
        self.color = GOLD 
    def draw(self, screen):
        head_pos = (int(self.x), int(self.y - self.height//2 + self.head_radius))
        body_rect = pygame.Rect(self.x - self.width//2, self.y - self.height//2 + self.head_radius*2, self.width, self.height - self.head_radius*2)
        pygame.draw.rect(screen, self.color, body_rect, border_radius=3)
        pygame.draw.circle(screen, self.skin_tone, head_pos, self.head_radius)
    def update(self, ball):
        target_y = self.rect.centery
        is_threatening = False
        if self.team_name == 'ai' and ball.vx > 0: is_threatening = True 
        elif self.team_name != 'ai' and ball.vx < 0: is_threatening = True 
        
        if is_threatening:
            time_to_reach = abs(self.x - ball.x) / abs(ball.vx) if abs(ball.vx) > 0.1 else 0
            predicted_y = ball.y + (ball.vy * time_to_reach)
            if predicted_y < 0: predicted_y = -predicted_y
            if predicted_y > HEIGHT: predicted_y = HEIGHT - (predicted_y - HEIGHT)
            target_y = predicted_y
        else:
            target_y = HEIGHT // 2

        speed = 4.0 
        if target_y > self.rect.centery + 5: self.y += speed
        elif target_y < self.rect.centery - 5: self.y -= speed
        self.y = max(GOAL_Y_START + self.height//2, min(GOAL_Y_START + GOAL_WIDTH - self.height//2, self.y))
        self.rect.center = (self.x, self.y)

class Ball:
    def __init__(self, x, y):
        self.x, self.y, self.radius, self.vx, self.vy, self.owner = x, y, 8, 0, 0, None
        self.rect = pygame.Rect(x-self.radius, y-self.radius, self.radius*2, self.radius*2)
        self.last_toucher, self.last_touch_time, self.last_toucher_team = None, 0, None
        self.spin_effect = 0
    def update(self, friction_mod=1.0):
        if self.owner:
            dist_val = DRIBBLE_DISTANCE * 0.7 if "MAGNET" in self.owner.traits else DRIBBLE_DISTANCE
            target_x = self.owner.rect.centerx + self.owner.direction_vector.x * dist_val
            target_y = self.owner.rect.centery + self.owner.direction_vector.y * dist_val
            self.x += (target_x - self.x) * DRIBBLE_SPEED; self.y += (target_y - self.y) * DRIBBLE_SPEED; self.vx, self.vy = 0, 0; self.spin_effect = 0
        else:
            self.x += self.vx; self.y += self.vy
            if self.spin_effect != 0: self.vy += self.spin_effect * abs(self.vx) * 0.3; self.spin_effect *= 0.95; 
            if abs(self.spin_effect) < 0.001: self.spin_effect = 0
            
            # Apply Weather Friction
            self.vx *= 0.97 * friction_mod
            self.vy *= 0.97 * friction_mod
            
        if self.y <= self.radius or self.y >= HEIGHT - self.radius: self.vy *= -0.8; self.spin_effect *= -0.5
        if self.x <= self.radius or self.x >= WIDTH - self.radius: self.vx *= -0.8; self.spin_effect = 0
        self.rect.center = (int(self.x), int(self.y))
    def shoot(self, angle, speed, spin_effect=0):
        kick_sound.play()
        if self.owner: self.last_toucher = self.owner; self.last_touch_time = pygame.time.get_ticks(); self.last_toucher_team = self.owner.team_name
        self.vx, self.vy = speed*math.cos(angle), speed*math.sin(angle); self.owner = None; self.spin_effect = spin_effect
    def draw(self, screen):
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius)
        if self.owner: pygame.draw.circle(screen, WHITE, (self.owner.rect.centerx, self.owner.rect.centery + 20), self.radius + 2, 2)
    def reset(self): self.x,self.y,self.vx,self.vy,self.owner = WIDTH//2,HEIGHT//2,0,0,None; self.last_toucher = None; self.last_toucher_team = None; self.spin_effect = 0

# --- DRAWING FUNCTIONS ---
def draw_playing_field(screen): 
    stripe_width = 100
    for x in range(0, WIDTH, stripe_width):
        if (x // stripe_width) % 2 == 0: color = (34, 139, 34) 
        else: color = (28, 120, 28) 
        pygame.draw.rect(screen, color, (x, 0, stripe_width, HEIGHT))
    pygame.draw.rect(screen, WHITE, (0, GOAL_Y_START, 15, GOAL_WIDTH))
    pygame.draw.rect(screen, WHITE, (WIDTH - 15, GOAL_Y_START, 15, GOAL_WIDTH))
    pygame.draw.line(screen, WHITE, (WIDTH // 2, 0), (WIDTH // 2, HEIGHT), 2)
    pygame.draw.circle(screen, WHITE, (WIDTH // 2, HEIGHT // 2), 70, 2)

# UPDATED HUD with xG
def draw_hud(screen, player, score, timer, team_names, xG_tracker, is_golden_goal=False): 
    font = get_font(24, True)
    p_color = TEAM_COLORS.get(team_names['player_code'], WHITE); ai_color = TEAM_COLORS.get(team_names['ai_code'], WHITE)
    if p_color == BLACK: p_color = (50, 50, 50) 
    if ai_color == BLACK: ai_color = (50, 50, 50)
    
    score_str = f"{team_names['player']} {score['Player']} ({xG_tracker['Player']:.2f} xG) - {score['AI']} {team_names['ai']} ({xG_tracker['AI']:.2f} xG)"
    score_text = font.render(score_str, True, WHITE)
    
    screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, 10))
    if is_golden_goal: timer_text = font.render("GOLDEN GOAL", True, GOLD); screen.blit(timer_text, (WIDTH-220, 10))
    else: mins, secs = int(timer//60), int(timer%60); timer_text = font.render(f"{mins:02}:{secs:02}", True, WHITE); screen.blit(timer_text, (WIDTH-100, 10))

def draw_screen_title(screen, title): 
    title_font = get_font(50, True) 
    title_surf = title_font.render(title, True, WHITE)
    screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 60))
    
def find_closest_player_to_ball(team, ball, exclude_player=None): return min([p for p in team if p != exclude_player and isinstance(p, Player)], key=lambda p_to_check: p_to_check.get_pos().distance_to(pygame.Vector2(ball.x, ball.y)), default=None)

def find_best_pass_target(player, team, opponent_team, exclude_player=None):
    best_target, highest_score = None, -1000 
    for teammate in team:
        if teammate == player or not isinstance(teammate, Player): continue
        if exclude_player and teammate == exclude_player: continue 
        distance = player.get_pos().distance_to(teammate.get_pos())
        if distance == 0: continue
        forwardness = (teammate.x - player.x) * player.attack_direction 
        score = (100 / distance) + (forwardness * 0.5) 
        blocked = False
        for opponent in opponent_team:
            if opponent.rect.inflate(10, 10).clipline(player.x, player.y, teammate.x, teammate.y): blocked = True; break
        if blocked: score -= 50
        if score > highest_score: highest_score, best_target = score, teammate
    return best_target

def draw_stats_screen(screen, game_objects):
    stats = game_objects.get('game_stats'); teams = game_objects.get('team_names'); score = game_objects.get('score'); xG = game_objects.get('xG')
    if not stats or not teams or not score: return
    total_time = stats['Player']['PossessionTime'] + stats['AI']['PossessionTime']; player_poss_pct = (stats['Player']['PossessionTime'] / total_time) * 100 if total_time > 0 else 50; ai_poss_pct = 100 - player_poss_pct
    all_players = game_objects.get('player_team', []) + game_objects.get('ai_team', [])
    mom = max([p for p in all_players if isinstance(p, Player)], key=lambda p: p.goals) if any(p.goals > 0 for p in all_players if isinstance(p, Player)) else None
    screen.fill((10, 20, 40))
    if game_objects.get('is_golden_goal') and game_objects.get('won_by_golden_goal'): draw_screen_title(screen, "GOLDEN GOAL VICTORY!")
    else: draw_screen_title(screen, "Match Statistics")
    font_header = get_font(30, True); font_stat = get_font(25)
    player_team_color = TEAM_COLORS.get(game_objects['user_team'], TEAM_COLORS['default_player'])
    ai_team_color = TEAM_COLORS.get(game_objects.get('ai_team_name', 'default_ai'), TEAM_COLORS['default_ai'])
    player_header = font_header.render(teams['player'], True, player_team_color); ai_header = font_header.render(teams['ai'], True, ai_team_color)
    screen.blit(player_header, (WIDTH*0.25-player_header.get_width()//2, 150)); screen.blit(ai_header, (WIDTH*0.75-ai_header.get_width()//2, 150))
    
    stat_y = 220; stat_list = ["Score", "xG", "Shots", "Shots on Goal", "Possession", "Passes (Comp/Att)"]
    player_stats = [score['Player'], f"{xG['Player']:.2f}", stats['Player']['Shots'], stats['Player']['ShotsOnGoal'], f"{player_poss_pct:.1f}%", f"{stats['Player']['PassesCompleted']}/{stats['Player']['PassesAttempted']}"]
    ai_stats = [score['AI'], f"{xG['AI']:.2f}", stats['AI']['Shots'], stats['AI']['ShotsOnGoal'], f"{ai_poss_pct:.1f}%", f"{stats['AI']['PassesCompleted']}/{stats['AI']['PassesAttempted']}"]
    for i, stat_name in enumerate(stat_list):
        name_surf = font_header.render(stat_name, True, WHITE); screen.blit(name_surf, (WIDTH//2 - name_surf.get_width()//2, stat_y + i*50))
        player_stat_surf = font_stat.render(str(player_stats[i]), True, player_team_color); screen.blit(player_stat_surf, (WIDTH*0.25-player_stat_surf.get_width()//2, stat_y + i*50))
        ai_stat_surf = font_stat.render(str(ai_stats[i]), True, ai_team_color); screen.blit(ai_stat_surf, (WIDTH*0.75-ai_stat_surf.get_width()//2, stat_y + i*50))
    if mom: mom_text = f"Man of the Match: {mom.name} ({mom.goals} Goals)"; mom_surf = font_header.render(mom_text, True, GOLD); screen.blit(mom_surf, (WIDTH//2 - mom_surf.get_width()//2, HEIGHT-180))
    nav_font = get_font(30); nav_text = nav_font.render("Press ENTER to continue", True, WHITE); screen.blit(nav_text, (WIDTH//2 - nav_text.get_width()//2, HEIGHT-80))

# --- RESET GAME FUNCTION ---
def reset_game(player_team_name, ai_team_name, selected_players, is_golden_goal=False):
    game_objects = {'player_team': [], 'ai_team': []}
    pos = {'player': [(WIDTH*0.35, HEIGHT*0.5), (WIDTH*0.2, HEIGHT*0.25), (WIDTH*0.2, HEIGHT*0.75)], 'ai': [(WIDTH*0.65, HEIGHT*0.5), (WIDTH*0.8, HEIGHT*0.25), (WIDTH*0.8, HEIGHT*0.75)]}
    p_df = player_profiles_df[player_profiles_df['Player'].isin(selected_players)]
    ai_team_roster = player_profiles_df[player_profiles_df['Team'] == ai_team_name]
    ai_df = ai_team_roster.sample(n=3, replace=True) if len(ai_team_roster) > 0 else ai_team_roster
    if len(p_df) < 3 or len(ai_df) < 3: return None
    for i in range(3):
        p_row = p_df.iloc[i]; game_objects['player_team'].append(Player(pos['player'][i][0], pos['player'][i][1], p_row['Team'], p_row['Player'], p_row.to_dict()))
        ai_row = ai_df.iloc[i]; game_objects['ai_team'].append(AIPlayer(pos['ai'][i][0], pos['ai'][i][1], ai_row['Team'], ai_row['Player'], ai_row.to_dict()))
    game_objects['player_goalie'] = Goalkeeper(20, HEIGHT//2, player_team_name); game_objects['ai_goalie'] = Goalkeeper(WIDTH-20, HEIGHT//2, ai_team_name)
    game_objects['ball'] = Ball(WIDTH//2, HEIGHT//2); game_objects['score'] = {"Player": 0, "AI": 0}; game_objects['start_ticks'] = pygame.time.get_ticks()
    game_objects['team_names'] = {"player": player_team_name.replace('_', ' ').title(), "ai": ai_team_name.replace('_', ' ').title(), "player_code": player_team_name, "ai_code": ai_team_name}
    game_objects['game_stats'] = {"Player": {"Shots": 0, "ShotsOnGoal": 0, "PassesAttempted": 0, "PassesCompleted": 0, "PossessionTime": 0}, "AI": {"Shots": 0, "ShotsOnGoal": 0, "PassesAttempted": 0, "PassesCompleted": 0, "PossessionTime": 0}}
    game_objects['xG'] = {'Player': 0.0, 'AI': 0.0}
    game_objects['particles'] = []
    game_objects['user_team'] = player_team_name
    game_objects['ai_team_name'] = ai_team_name 
    game_objects['is_golden_goal'] = is_golden_goal
    game_objects['won_by_golden_goal'] = False
    game_objects['goal_data'] = {'scorer': None, 'timer': 0}
    
    # Initialize Random Weather
    weather_type = random.choice(["CLEAR", "CLEAR", "RAIN", "SNOW"])
    game_objects['weather'] = WeatherManager(weather_type)
    
    return game_objects

# --- STATE HANDLERS ---
def handle_menu_state(events, mouse_pos, menu_buttons, tournament):
    for event in events:
        if menu_buttons['start'].is_clicked(event): return "TEAM_SELECTION", None
        if menu_buttons['golden_goal'].is_clicked(event): return "TEAM_SELECTION_GOLDEN", None
        if menu_buttons['mls_cup'].is_clicked(event): return "TEAM_SELECTION_TOURNAMENT", None
        if menu_buttons['season'].is_clicked(event): return "TEAM_SELECTION_SEASON", None
        if menu_buttons['quit'].is_clicked(event): return "QUIT", None
    screen.fill(GREEN); draw_screen_title(screen, "Data-Driven Soccer")
    for button in menu_buttons.values(): button.check_hover(mouse_pos); button.draw(screen)
    return "MENU", None

def handle_team_selection_state(events, mouse_pos, team_buttons, scroll_y, back_button, is_tournament=False, is_golden_goal=False, is_season=False):
    for event in events:
        if back_button.is_clicked(event): return "MENU", None, 0 

    max_scroll = max(0, len(team_buttons) * 80 + 200 - HEIGHT + 50) 
    for event in events:
        if event.type == pygame.MOUSEWHEEL:
            scroll_y -= event.y * 20 
            scroll_y = max(0, min(scroll_y, max_scroll)) 
        for team_name, button in team_buttons.items():
            if button.is_clicked(event, scroll_offset=scroll_y): 
                return "PLAYER_SELECTION", team_name, 0 

    title_text = "Choose Your Team"; 
    if is_tournament: title_text += " (MLS Cup)"
    if is_golden_goal: title_text += " (Golden Goal)"
    if is_season: title_text += " (Season)"
    
    screen.fill(GREEN)
    draw_screen_title(screen, title_text)
    back_button.check_hover(mouse_pos); back_button.draw(screen)

    for button in team_buttons.values(): 
        button.check_hover(mouse_pos, scroll_offset=scroll_y) 
        button.draw(screen, scroll_offset=scroll_y) 

    if is_tournament: return "TEAM_SELECTION_TOURNAMENT", None, scroll_y
    if is_golden_goal: return "TEAM_SELECTION_GOLDEN", None, scroll_y
    if is_season: return "TEAM_SELECTION_SEASON", None, scroll_y
    return "TEAM_SELECTION", None, scroll_y

def handle_player_selection_state(events, mouse_pos, user_team, player_cards, selected_players, start_match_button, back_button, scroll_y, is_tournament=False, tournament=None, is_golden_goal=False, is_season=False, season=None):
    for event in events:
        if back_button.is_clicked(event):
            if is_tournament: return "TEAM_SELECTION_TOURNAMENT", None, 0
            if is_golden_goal: return "TEAM_SELECTION_GOLDEN", None, 0
            if is_season: return "TEAM_SELECTION_SEASON", None, 0
            return "TEAM_SELECTION", None, 0

    num_rows = (len(player_cards) + 4) // 5 
    total_height = 150 + num_rows * (160 + 20)
    max_scroll = max(0, total_height - HEIGHT + 100)

    for event in events:
        if event.type == pygame.MOUSEWHEEL:
            scroll_y -= event.y * 20
            scroll_y = max(0, min(scroll_y, max_scroll))
        for card in player_cards:
            card.check_hover(mouse_pos, scroll_offset=scroll_y)
            if card.is_clicked(event):
                if card.name in selected_players: selected_players.remove(card.name)
                elif len(selected_players) < 3: selected_players.append(card.name)
        
        if len(selected_players) == 3 and start_match_button.is_clicked(event):
            if is_tournament:
                opponents = [t for t in player_profiles_df['Team'].unique() if t != user_team]; random.shuffle(opponents); ai_teams = opponents[:3]
                tournament = Tournament(user_team, ai_teams); return "TOURNAMENT_BRACKET", tournament, 0
            elif is_season:
                all_teams = list(player_profiles_df['Team'].unique()); season = Season(user_team, all_teams); return "LEAGUE_TABLE", season, 0
            else:
                opponents = [t for t in player_profiles_df['Team'].unique() if t != user_team]; ai_team = random.choice(opponents)
                game_objects = reset_game(user_team, ai_team, selected_players, is_golden_goal)
                if game_objects: whistle_sound.play(); return "PLAYING", game_objects, 0

    screen.fill(GREEN); draw_screen_title(screen, f"Select Squad ({len(selected_players)}/3)")
    back_button.check_hover(mouse_pos); back_button.draw(screen)

    for card in player_cards: 
        card.check_hover(mouse_pos, scroll_offset=scroll_y)
        card.draw(screen, card.name in selected_players, scroll_offset=scroll_y)
    if len(selected_players) == 3: start_match_button.check_hover(mouse_pos); start_match_button.draw(screen)
    return "PLAYER_SELECTION", None, scroll_y

def handle_tournament_bracket_state(events, mouse_pos, tournament, selected_players, play_match_button, back_button):
    for event in events:
         if back_button.is_clicked(event): return "MENU", None

    tournament.draw_bracket(screen)
    back_button.check_hover(mouse_pos); back_button.draw(screen)

    for event in events:
        if tournament.current_round == "SEMI" or tournament.current_round == "FINAL":
             if tournament.user_status == "ALIVE" and play_match_button.is_clicked(event):
                opponent = tournament.get_opponent()
                game_objects = reset_game(tournament.user_team, opponent, selected_players, is_golden_goal=False)
                if game_objects: whistle_sound.play(); return "PLAYING", game_objects
        if tournament.user_status == "ELIMINATED" or tournament.user_status == "CHAMPION":
             if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN: return "MENU", None
    
    if tournament.user_status == "ALIVE":
        play_match_button.check_hover(mouse_pos); play_match_button.draw(screen)
    else:
        msg = "Eliminated! Press Enter." if tournament.user_status == "ELIMINATED" else "Champion! Press Enter."
        font = get_font(40); text = font.render(msg, True, WHITE); screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT - 100))
    return "TOURNAMENT_BRACKET", None

def handle_league_table_state(events, mouse_pos, season, selected_players, play_match_button, back_button):
    for event in events:
         if back_button.is_clicked(event): return "MENU", None

    season.draw_standings(screen)
    back_button.check_hover(mouse_pos); back_button.draw(screen)

    for event in events:
        if not season.season_over:
            if play_match_button.is_clicked(event):
                opponent = season.get_current_round_match()
                if opponent:
                    game_objects = reset_game(season.user_team, opponent, selected_players, is_golden_goal=False)
                    if game_objects: whistle_sound.play(); return "PLAYING", game_objects
        else:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN: return "MENU", None

    if not season.season_over:
        play_match_button.check_hover(mouse_pos); play_match_button.draw(screen)
    else:
        msg = "Season Over! Press Enter."
        font = get_font(40); text = font.render(msg, True, WHITE); screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT - 30))
    return "LEAGUE_TABLE", None

def handle_penalty_shootout_state(events, keys, game_objects, penalty_data):
    GOAL_TOP_Y = 100
    KICKER_START_POS = pygame.Vector2(WIDTH // 2, HEIGHT - 150)
    BALL_START_POS = pygame.Vector2(WIDTH // 2, HEIGHT - 200)
    GK_START_POS = pygame.Vector2(WIDTH // 2, 120)
    if 'anim_state' not in penalty_data:
        penalty_data['anim_state'] = 'aiming'; penalty_data['kicker_pos'] = KICKER_START_POS.copy(); penalty_data['ball_pos'] = BALL_START_POS.copy(); penalty_data['gk_pos'] = GK_START_POS.copy(); penalty_data['target_ball'] = None; penalty_data['target_gk'] = None; penalty_data['gk_feint_offset'] = 0; penalty_data['has_hesitated'] = False; penalty_data['hesitation_end'] = 0
    current_time = pygame.time.get_ticks()

    if penalty_data['anim_state'] == 'result_display':
        if current_time > penalty_data['timer']:
            penalty_data['anim_state'] = 'aiming'; penalty_data['kicker_pos'] = KICKER_START_POS.copy(); penalty_data['ball_pos'] = BALL_START_POS.copy(); penalty_data['gk_pos'] = GK_START_POS.copy(); penalty_data['gk_feint_offset'] = 0; penalty_data['has_hesitated'] = False
            if penalty_data['shot_result'] == 'GOAL':
                if penalty_data['phase'] == 'USER_KICK': penalty_data['user_history'].append('O')
                else: penalty_data['ai_history'].append('O')
            else:
                if penalty_data['phase'] == 'USER_KICK': penalty_data['user_history'].append('X')
                else: penalty_data['ai_history'].append('X')
            if penalty_data['phase'] == 'USER_KICK':
                penalty_data['phase'] = 'AI_KICK'; penalty_data['charge'] = 0; penalty_data['user_dir'] = None
            else:
                penalty_data['phase'] = 'USER_KICK'; penalty_data['round'] += 1
                u_score = penalty_data['user_history'].count('O'); a_score = penalty_data['ai_history'].count('O'); rounds_played = penalty_data['round'] - 1
                if rounds_played < 3:
                    u_rem = 3 - rounds_played; a_rem = 3 - rounds_played
                    if u_score > a_score + a_rem: return "POST_GAME_PENALTY_DONE"
                    if a_score > u_score + u_rem: return "POST_GAME_PENALTY_DONE"
                elif rounds_played >= 3:
                    if u_score != a_score: return "POST_GAME_PENALTY_DONE"
        else:
            font = get_font(80, True); color = GOLD if "GOAL" in penalty_data['result_msg'] else RED; msg = font.render(penalty_data['result_msg'], True, color)

    elif penalty_data['anim_state'] == 'aiming':
        if penalty_data['phase'] == 'USER_KICK':
            penalty_data['gk_feint_offset'] = math.sin(current_time * 0.01) * 30 
            penalty_data['gk_pos'].x = (WIDTH // 2) + penalty_data['gk_feint_offset']
            if penalty_data['user_dir'] is None:
                if keys[pygame.K_LEFT]: penalty_data['user_dir'] = "LEFT"
                elif keys[pygame.K_UP]: penalty_data['user_dir'] = "CENTER"
                elif keys[pygame.K_RIGHT]: penalty_data['user_dir'] = "RIGHT"
            else:
                if keys[pygame.K_SPACE]:
                    penalty_data['charge'] += 2
                    if penalty_data['charge'] > 100: penalty_data['charge'] = 100
                for event in events:
                    if event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
                        ai_choice = random.choice(["LEFT", "CENTER", "RIGHT"]); penalty_data['ai_move'] = ai_choice
                        if penalty_data['charge'] > 95: penalty_data['shot_result'] = "MISS"; penalty_data['result_msg'] = "MISS! (Overpowered)"
                        elif penalty_data['user_dir'] == ai_choice: penalty_data['shot_result'] = "SAVE"; penalty_data['result_msg'] = "SAVED!"
                        else: penalty_data['shot_result'] = "GOAL"; penalty_data['result_msg'] = "GOAL!"
                        shot_x = WIDTH//2
                        if penalty_data['user_dir'] == "LEFT": shot_x = WIDTH//2 - 120
                        elif penalty_data['user_dir'] == "RIGHT": shot_x = WIDTH//2 + 120
                        shot_y = GOAL_TOP_Y + 50 if penalty_data['shot_result'] != "MISS" else -50
                        penalty_data['target_ball'] = pygame.Vector2(shot_x, shot_y)
                        gk_x = WIDTH//2
                        if ai_choice == "LEFT": gk_x = WIDTH//2 - 100
                        elif ai_choice == "RIGHT": gk_x = WIDTH//2 + 100
                        penalty_data['target_gk'] = pygame.Vector2(gk_x, GK_START_POS.y)
                        penalty_data['gk_pos'].x = WIDTH // 2; penalty_data['anim_state'] = 'running' 
        else: 
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_LEFT, pygame.K_UP, pygame.K_RIGHT]:
                        user_dive = "LEFT" if event.key == pygame.K_LEFT else ("CENTER" if event.key == pygame.K_UP else "RIGHT")
                        ai_shot = random.choice(["LEFT", "CENTER", "RIGHT"])
                        if random.random() < 0.1: penalty_data['shot_result'] = "MISS"; penalty_data['result_msg'] = "MISS! (AI Wide)"
                        elif user_dive == ai_shot: penalty_data['shot_result'] = "SAVE"; penalty_data['result_msg'] = "SAVED!"
                        else: penalty_data['shot_result'] = "GOAL"; penalty_data['result_msg'] = "GOAL!"
                        shot_x = WIDTH//2
                        if ai_shot == "LEFT": shot_x = WIDTH//2 - 120
                        elif ai_shot == "RIGHT": shot_x = WIDTH//2 + 120
                        shot_y = GOAL_TOP_Y + 50 if penalty_data['shot_result'] != "MISS" else -50
                        penalty_data['target_ball'] = pygame.Vector2(shot_x, shot_y)
                        gk_x = WIDTH//2
                        if user_dive == "LEFT": gk_x = WIDTH//2 - 100
                        elif user_dive == "RIGHT": gk_x = WIDTH//2 + 100
                        penalty_data['target_gk'] = pygame.Vector2(gk_x, GK_START_POS.y)
                        penalty_data['anim_state'] = 'running'
    if penalty_data['anim_state'] == 'running':
        if penalty_data['phase'] == 'AI_KICK' and not penalty_data['has_hesitated']:
            dist = penalty_data['kicker_pos'].distance_to(penalty_data['ball_pos'])
            if dist < 80 and dist > 40 and random.random() < 0.5: penalty_data['anim_state'] = 'hesitating'; penalty_data['hesitation_end'] = current_time + random.randint(200, 500); penalty_data['has_hesitated'] = True
        direction = penalty_data['ball_pos'] - penalty_data['kicker_pos']
        if direction.length() > 5: direction.normalize_ip(); penalty_data['kicker_pos'] += direction * 4
        else: penalty_data['anim_state'] = 'kicking'; kick_sound.play()
    elif penalty_data['anim_state'] == 'hesitating':
        if current_time > penalty_data['hesitation_end']: penalty_data['anim_state'] = 'running'
    elif penalty_data['anim_state'] == 'kicking':
        ball_dir = penalty_data['target_ball'] - penalty_data['ball_pos']; gk_dir = penalty_data['target_gk'] - penalty_data['gk_pos']
        if ball_dir.length() > 10: ball_dir.normalize_ip(); penalty_data['ball_pos'] += ball_dir * 15 
        if gk_dir.length() > 5: gk_dir.normalize_ip(); penalty_data['gk_pos'] += gk_dir * 8 
        if penalty_data['ball_pos'].distance_to(penalty_data['target_ball']) < 15:
            penalty_data['anim_state'] = 'result_display'; penalty_data['timer'] = current_time + 2000 
            if penalty_data['shot_result'] == "GOAL": goal_sound.play()
            elif penalty_data['shot_result'] == "SAVE": tackle_sound.play()

    screen.fill(DARK_GREEN)
    pygame.draw.rect(screen, WHITE, (WIDTH//2 - 150, GOAL_TOP_Y, 300, 10)); pygame.draw.rect(screen, WHITE, (WIDTH//2 - 150, GOAL_TOP_Y, 10, 150)); pygame.draw.rect(screen, WHITE, (WIDTH//2 + 150, GOAL_TOP_Y, 10, 150)) 
    for i in range(1, 10): pygame.draw.line(screen, (200, 200, 200), (WIDTH//2 - 150 + i*30, GOAL_TOP_Y), (WIDTH//2 - 150 + i*30, GOAL_TOP_Y+150), 1); pygame.draw.line(screen, (200, 200, 200), (WIDTH//2 - 150, GOAL_TOP_Y + i*15), (WIDTH//2 + 150, GOAL_TOP_Y + i*15), 1)

    gk_color = GOLD if penalty_data['phase'] == 'USER_KICK' else TEAM_COLORS['default_player']; pygame.draw.circle(screen, gk_color, (int(penalty_data['gk_pos'].x), int(penalty_data['gk_pos'].y)), 20)
    kicker_color = TEAM_COLORS['default_player'] if penalty_data['phase'] == 'USER_KICK' else TEAM_COLORS['default_ai']; pygame.draw.circle(screen, kicker_color, (int(penalty_data['kicker_pos'].x), int(penalty_data['kicker_pos'].y)), 20)
    pygame.draw.circle(screen, WHITE, (int(penalty_data['ball_pos'].x), int(penalty_data['ball_pos'].y)), 10)

    if penalty_data['anim_state'] == 'aiming':
        font = get_font(40)
        if penalty_data['phase'] == 'USER_KICK':
            if penalty_data['user_dir'] is None: msg = "Aim: Arrow Keys"
            else: 
                msg = "Hold SPACE (Power)"; bar_w = 200; bar_h = 20; pygame.draw.rect(screen, BLACK, (WIDTH//2 - bar_w//2, HEIGHT - 80, bar_w, bar_h))
                fill = (penalty_data['charge'] / 100) * bar_w; c = GREEN if penalty_data['charge'] < 60 else (YELLOW if penalty_data['charge'] < 95 else RED); pygame.draw.rect(screen, c, (WIDTH//2 - bar_w//2, HEIGHT - 80, fill, bar_h))
        else: msg = "Predict Dive: Arrow Keys"
        screen.blit(font.render(msg, True, WHITE), (WIDTH//2 - 100, HEIGHT - 40))

    if penalty_data['anim_state'] == 'result_display':
        font = get_font(80, True); color = GOLD if "GOAL" in penalty_data['result_msg'] else RED; msg = font.render(penalty_data['result_msg'], True, color); screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2))

    start_x = WIDTH//2 - 150
    for i in range(5):
        res = penalty_data['user_history'][i] if i < len(penalty_data['user_history']) else None; color = GREEN if res == 'O' else (RED if res == 'X' else GRAY); pygame.draw.circle(screen, color, (start_x + i*60, 30), 15)
        res_a = penalty_data['ai_history'][i] if i < len(penalty_data['ai_history']) else None; color_a = GREEN if res_a == 'O' else (RED if res_a == 'X' else GRAY); pygame.draw.circle(screen, color_a, (start_x + i*60, 70), 15)
    font = get_font(30); screen.blit(font.render("YOU", True, WHITE), (start_x - 50, 20)); screen.blit(font.render("CPU", True, WHITE), (start_x - 50, 60))
    return "PENALTY_SHOOTOUT"

# --- GOAL CELEBRATION STATE ---
def handle_goal_celebration_state(game_objects):
    draw_playing_field(screen)
    game_objects['weather'].draw(screen) # Draw Weather Overlays
    for p in game_objects['player_team'] + game_objects['ai_team']: p.draw(screen)
    for p in game_objects['particles']: p.draw(screen)
    game_objects['player_goalie'].draw(screen); game_objects['ai_goalie'].draw(screen); game_objects['ball'].draw(screen)
    
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0,0))
    
    scorer = game_objects['goal_data']['scorer']
    if scorer:
        big_font = get_font(100, True); small_font = get_font(60)
        t1 = big_font.render("GOAL!", True, GOLD)
        t2 = small_font.render(f"Scored by {scorer.name}", True, WHITE)
        screen.blit(t1, (WIDTH//2 - t1.get_width()//2, HEIGHT//2 - 60))
        screen.blit(t2, (WIDTH//2 - t2.get_width()//2, HEIGHT//2 + 40))
        
    game_objects['goal_data']['timer'] -= 1
    if game_objects['goal_data']['timer'] <= 0:
        if game_objects['is_golden_goal'] and game_objects['won_by_golden_goal']:
            return "POST_GAME" 
        [p.reset() for p in game_objects['player_team']+game_objects['ai_team']]
        game_objects['ball'].reset()
        whistle_sound.play()
        return "PLAYING"
        
    return "GOAL_CELEBRATION"

# --- MAIN GAME LOOP HANDLER ---
def handle_playing_state(events, keys, game_objects, active_idx, elapsed_time):
    player_team, ai_team, ball = game_objects['player_team'], game_objects['ai_team'], game_objects['ball']
    active_player = player_team[active_idx]
    is_golden_goal = game_objects.get('is_golden_goal', False)
    
    # Weather Updates
    weather = game_objects['weather']
    weather.update()

    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                new_player = find_closest_player_to_ball(game_objects['player_team'],ball,active_player)
                if new_player: active_idx = game_objects['player_team'].index(new_player)
            if event.key == pygame.K_s and ball.owner == active_player:
                game_objects['game_stats']['Player']['PassesAttempted'] += 1; 
                teammate = find_best_pass_target(active_player, game_objects['player_team'], game_objects['ai_team']); 
                angle = 0; pass_prob = 0.95
                if teammate: angle = math.atan2(teammate.y-active_player.y, teammate.x-active_player.x)
                if active_player.stats.get('Passing', 0) >= 18: pass_prob = 1.0
                else: pass_prob = (active_player.stats.get('Passing', 10)/20)*0.95
                if random.random() > pass_prob: angle += random.uniform(-0.5, 0.5)
                if teammate: ball.shoot(angle, BALL_SPEED * 0.8)
            if event.key == pygame.K_SPACE and ball.owner == active_player:
                game_objects['game_stats']['Player']['Shots'] += 1; shot_prob = 0.8; speed = BALL_SPEED * 1.2; spin = 0; goal_center = pygame.Vector2(WIDTH-15, HEIGHT/2); angle = math.atan2(goal_center.y-active_player.y, goal_center.x-active_player.x)
                foot = active_player.stats.get('Preferred Foot', 'Right')
                if active_player.stats.get('Shooting', 0) >= 15 and active_player.stats.get('Passing', 0) >= 12: 
                    shot_prob += 0.15
                    if foot == 'Right': spin = -0.3
                    elif foot == 'Left': spin = 0.3
                    elif foot == 'Both': spin = random.choice([-0.3, 0.3])
                if "SNIPER" in active_player.traits: speed *= 1.2
                if active_player.stats.get('Shooting', 0) >= 18: speed *= 1.5
                shot_prob_final = (active_player.stats.get('Shooting', 10)/20) * shot_prob
                
                # Update xG
                game_objects['xG']['Player'] += shot_prob_final
                
                if GOAL_Y_START < active_player.y + math.sin(angle) * (WIDTH - active_player.x) < GOAL_Y_START + GOAL_WIDTH: game_objects['game_stats']['Player']['ShotsOnGoal'] += 1
                if random.random() > shot_prob_final: angle += random.uniform(-0.4, 0.4)
                ball.shoot(angle, speed, spin_effect=spin)

    # Pass Weather modifiers to move functions
    active_player.move(keys, ball.owner == active_player, weather_accel_mod=weather.player_accel)
    
    if ball.owner in player_team: game_objects['game_stats']['Player']['PossessionTime'] += elapsed_time
    elif ball.owner in ai_team: game_objects['game_stats']['AI']['PossessionTime'] += elapsed_time
    is_pressing = keys[pygame.K_d]
    for p in player_team: p.is_pressing = False
    if is_pressing:
        active_player.is_pressing = True; active_player.tackle(ball, ai_team)
        teammate_for_press = find_closest_player_to_ball(player_team, ball, active_player)
        if teammate_for_press: teammate_for_press.is_pressing = True; teammate_for_press.update_ai_movement(ball, False, pygame.Vector2(ball.x, ball.y), weather_accel_mod=weather.player_accel)
    player_has_ball = ball.owner in player_team
    for p in player_team:
        if p != active_player and not p.is_pressing: p.update_ai_movement(ball, player_has_ball, weather_accel_mod=weather.player_accel)
    presser = find_closest_player_to_ball(ai_team, ball)
    
    # Pass xG tracker to AI
    for p in ai_team: p.update(ball, player_team, ai_team, is_presser=(p == presser), game_stats=game_objects['game_stats'], weather_accel_mod=weather.player_accel, xG_tracker=game_objects['xG'])
    
    game_objects['player_goalie'].update(ball); game_objects['ai_goalie'].update(ball)
    current_time = pygame.time.get_ticks()
    for p in player_team + ai_team:
        if ball.owner is None and p.rect.colliderect(ball.rect) and (p != ball.last_toucher or current_time - ball.last_touch_time > 200):
            ball.owner = p
            p.pass_cooldown = 55 
            if ball.last_toucher and ball.last_toucher_team == p.team_name and current_time - ball.last_touch_time < PASS_COMPLETION_TIME_LIMIT:
                if p.team_name == game_objects['user_team']: game_objects['game_stats']['Player']['PassesCompleted'] += 1
                else: game_objects['game_stats']['AI']['PassesCompleted'] += 1
    
    ball_speed = math.sqrt(ball.vx**2 + ball.vy**2)
    if ball_speed > 18: 
        for _ in range(3): game_objects['particles'].append(Particle(ball.x, ball.y, ORANGE, size_max=10)) 
    elif ball.spin_effect != 0 and ball_speed > 5:
        for _ in range(1): game_objects['particles'].append(Particle(ball.x, ball.y, (0, 255, 255), size_max=6))

    for p in game_objects['particles'][:]:
        p.update()
        if p.life <= 0: game_objects['particles'].remove(p)
    
    # Update Ball with weather friction
    ball.update(friction_mod=weather.friction)
    
    if game_objects['player_goalie'].rect.colliderect(ball.rect) or game_objects['ai_goalie'].rect.colliderect(ball.rect): ball.vx*=-0.5; ball.vy*=-0.5; ball.owner=None
    
    # GOAL DETECTION
    goal_scored = False
    if ball.rect.colliderect((WIDTH-15, GOAL_Y_START, 15, GOAL_WIDTH)): 
        if ball.last_toucher and ball.last_toucher.team_name == game_objects['user_team']: 
            game_objects['score']["Player"]+=1; goal_sound.play(); ball.last_toucher.goals += 1; goal_scored=True
    elif ball.rect.colliderect((0, GOAL_Y_START, 15, GOAL_WIDTH)): 
         if ball.last_toucher and ball.last_toucher.team_name == game_objects.get('ai_team_name'):
            game_objects['score']["AI"]+=1; goal_sound.play(); ball.last_toucher.goals += 1; goal_scored=True
    
    if goal_scored:
        if is_golden_goal:
            game_objects['won_by_golden_goal'] = True; whistle_sound.play(); return "POST_GAME", active_idx
        else:
            game_objects['goal_data']['scorer'] = ball.last_toucher
            game_objects['goal_data']['timer'] = 120 
            return "GOAL_CELEBRATION", active_idx

    timer = GAME_DURATION_SECONDS - ((pygame.time.get_ticks()-game_objects['start_ticks'])/1000)
    if not is_golden_goal and timer <= 0: whistle_sound.play(); return "POST_GAME", active_idx

    draw_playing_field(screen)
    weather.draw(screen) # Draw Weather Overlays
    
    all_game_players = player_team + ai_team
    for p in all_game_players: p.draw(screen)
    for p in game_objects['particles']: p.draw(screen) 
    indicator_points = [(active_player.rect.centerx, active_player.rect.top-20), (active_player.rect.centerx-7, active_player.rect.top-13), (active_player.rect.centerx+7, active_player.rect.top-13)]
    pygame.draw.polygon(screen, GOLD, indicator_points)
    game_objects['player_goalie'].draw(screen); game_objects['ai_goalie'].draw(screen); ball.draw(screen)
    draw_hud(screen, active_player, game_objects['score'], timer, game_objects['team_names'], game_objects['xG'], is_golden_goal)
    return "PLAYING", active_idx

def handle_post_game_state(events, game_objects, is_tournament, tournament, penalty_data, is_season=False, season=None):
    for event in events:
        if event.type == pygame.KEYDOWN and (event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER):
            if is_tournament:
                if game_objects['score']['Player'] == game_objects['score']['AI']:
                    penalty_data.clear()
                    penalty_data.update({'phase': 'USER_KICK', 'round': 1, 'user_history': [], 'ai_history': [], 'result_msg': None, 'timer': 0, 'user_dir': None, 'charge': 0, 'shot_result': None})
                    return "PENALTY_SHOOTOUT"
                user_won = game_objects['score']['Player'] > game_objects['score']['AI']; tournament.advance_tournament(user_won); return "TOURNAMENT_BRACKET"
            elif is_season:
                 season.record_user_result(game_objects['score']['Player'], game_objects['score']['AI'], game_objects['ai_team_name'])
                 return "LEAGUE_TABLE"
            else: return "MENU"
    draw_stats_screen(screen, game_objects)
    if is_tournament and game_objects['score']['Player'] == game_objects['score']['AI']:
        font = get_font(40); text = font.render("DRAW! Press Enter for Penalty Shootout", True, GOLD); screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT - 130))
    return "POST_GAME"

# --- MAIN GAME LOOP ---
def main():
    clock = pygame.time.Clock(); game_state = "MENU"
    
    # Main Menu Buttons
    menu_buttons = {
        "start": Button(WIDTH//2-100, 200, 200, 50, "Friendly", BLUE, (0,100,255)),
        "golden_goal": Button(WIDTH//2-100, 270, 200, 50, "Golden Goal", GOLD, (255,215,0)), 
        "mls_cup": Button(WIDTH//2-100, 340, 200, 50, "MLS Cup", ORANGE, (255,200,0)),
        "season": Button(WIDTH//2-100, 410, 200, 50, "League Mode", PURPLE, (180,50,180)), 
        "quit": Button(WIDTH//2-100, 480, 200, 50, "Quit", RED, (255,100,100))
    }
    
    # Back Button
    back_button = Button(20, 20, 100, 40, "Back", RED, (255, 80, 80), 24)

    team_buttons = {team: Button(WIDTH//2-150, 200+i*80, 300, 60, team.replace('_',' ').title(), ORANGE, (255,200,0), 36) for i, team in enumerate(player_profiles_df['Team'].unique())}
    game_objects, active_idx, user_team, player_cards, selected_players = {}, 0, None, [], []
    start_match_button = Button(WIDTH//2-125, HEIGHT-100, 250, 60, "Start Match", BLUE, (0,100,255))
    play_match_button = Button(WIDTH//2-125, 550, 250, 60, "Play Match", BLUE, (0,100,255))
    
    tournament = None; is_tournament_mode = False; is_golden_goal_mode = False; 
    season = None; is_season_mode = False 
    penalty_data = {} 
    menu_scroll_y = 0

    running = True
    while running:
        elapsed_time = clock.tick(FPS); mouse_pos = pygame.mouse.get_pos(); events = pygame.event.get(); keys = pygame.key.get_pressed()
        for event in events:
            if event.type == pygame.QUIT: running = False

        if game_state == "MENU":
            next_state, _ = handle_menu_state(events, mouse_pos, menu_buttons, tournament)
            if next_state == "QUIT": running = False
            elif next_state in ["TEAM_SELECTION", "TEAM_SELECTION_TOURNAMENT", "TEAM_SELECTION_GOLDEN", "TEAM_SELECTION_SEASON"]:
                game_state = "TEAM_SELECTION"
                is_tournament_mode = (next_state == "TEAM_SELECTION_TOURNAMENT")
                is_golden_goal_mode = (next_state == "TEAM_SELECTION_GOLDEN")
                is_season_mode = (next_state == "TEAM_SELECTION_SEASON")
                menu_scroll_y = 0 
            
        elif game_state == "TEAM_SELECTION":
            next_state, team_choice, menu_scroll_y = handle_team_selection_state(
                events, mouse_pos, team_buttons, menu_scroll_y, back_button, is_tournament_mode, is_golden_goal_mode, is_season_mode
            )
            if next_state == "MENU": game_state = "MENU"
            elif team_choice:
                user_team, game_state, selected_players = team_choice, next_state, []
                menu_scroll_y = 0 
                roster = player_profiles_df[player_profiles_df['Team'] == user_team]; player_cards = []
                card_width, card_height, gap = 140, 160, 20; num_cols = 5; total_width = (card_width + gap) * num_cols - gap; start_x = (WIDTH - total_width) // 2
                for i, p_data in enumerate(roster.iterrows()):
                    row, col = i // num_cols, i % num_cols; x, y = start_x + col * (card_width + gap), 150 + row * (card_height + gap)
                    player_cards.append(PlayerCard(x, y, card_width, card_height, p_data[1]))

        elif game_state == "PLAYER_SELECTION":
            next_state, result, menu_scroll_y = handle_player_selection_state(
                events, mouse_pos, user_team, player_cards, selected_players, start_match_button, back_button, menu_scroll_y, 
                is_tournament_mode, tournament, is_golden_goal_mode, is_season_mode, season
            )
            if next_state == "TEAM_SELECTION" or next_state == "TEAM_SELECTION_TOURNAMENT" or next_state == "TEAM_SELECTION_GOLDEN" or next_state == "TEAM_SELECTION_SEASON":
                game_state = "TEAM_SELECTION"
            elif next_state == "PLAYING": game_objects, game_state, active_idx = result, "PLAYING", 0
            elif next_state == "TOURNAMENT_BRACKET": tournament, game_state = result, "TOURNAMENT_BRACKET"
            elif next_state == "LEAGUE_TABLE": season, game_state = result, "LEAGUE_TABLE"

        elif game_state == "TOURNAMENT_BRACKET":
            next_state, new_game_objects = handle_tournament_bracket_state(events, mouse_pos, tournament, selected_players, play_match_button, back_button)
            if next_state == "PLAYING": game_objects, game_state, active_idx = new_game_objects, "PLAYING", 0
            elif next_state == "MENU": game_state = "MENU"

        elif game_state == "LEAGUE_TABLE": 
            next_state, new_game_objects = handle_league_table_state(events, mouse_pos, season, selected_players, play_match_button, back_button)
            if next_state == "PLAYING": game_objects, game_state, active_idx = new_game_objects, "PLAYING", 0
            elif next_state == "MENU": game_state = "MENU"

        elif game_state == "PLAYING": 
            result = handle_playing_state(events, keys, game_objects, active_idx, elapsed_time)
            if isinstance(result, tuple):
                game_state, active_idx = result
            else: 
                game_state = result

        elif game_state == "GOAL_CELEBRATION":
            game_state = handle_goal_celebration_state(game_objects)

        elif game_state == "POST_GAME": game_state = handle_post_game_state(events, game_objects, is_tournament_mode, tournament, penalty_data, is_season_mode, season)
        elif game_state == "PENALTY_SHOOTOUT":
            result = handle_penalty_shootout_state(events, keys, game_objects, penalty_data)
            if result == "POST_GAME_PENALTY_DONE":
                user_won = penalty_data['user_history'].count('O') > penalty_data['ai_history'].count('O'); tournament.advance_tournament(user_won); game_state = "TOURNAMENT_BRACKET"
        
        pygame.display.flip()
    pygame.quit(); sys.exit()

if __name__ == "__main__":
    main()