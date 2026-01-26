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
pygame.display.set_caption("Data-Driven 3v3 Soccer Simulator (v14 - MLS Cup)")

# COLORS
GREEN = (34, 139, 34); WHITE = (255, 255, 255); BLUE = (0, 0, 255); RED = (255, 0, 0); BLACK = (0, 0, 0); GOLD = (255, 215, 0); ORANGE = (255, 165, 0)
GRAY = (100, 100, 100); DARK_GREEN = (0, 100, 0)
SKIN_TONE_LIGHT = (234, 192, 134); SKIN_TONE_MEDIUM = (197, 140, 89); SKIN_TONE_DARK = (141, 85, 36)
RACE_SKIN_MAP = {"White": SKIN_TONE_LIGHT, "Hispanic": SKIN_TONE_MEDIUM, "Black": SKIN_TONE_DARK, "Asian": SKIN_TONE_LIGHT}
DEFAULT_SKIN_TONE = SKIN_TONE_MEDIUM
TEXT_BG_COLOR = (0, 0, 0, 128); TACKLE_INDICATOR_COLOR = (255, 255, 0, 100)
CARD_COLOR = (0, 50, 100); CARD_HOVER_COLOR = (0, 80, 150); CARD_SELECTED_COLOR = GOLD

# TEAM COLORS
TEAM_COLORS = {
    'lafc': (0, 0, 0),             # Black
    'la_galaxy': (255, 255, 255),  # White
    'inter_miami': (247, 0, 136),  # Pink
    'columbus_crew': (255, 255, 0), # Yellow
    'cincinnati': (0, 24, 107),     # Navy Blue
    'default_player': (0, 0, 255),  # Blue
    'default_ai': (255, 0, 0)       # Red
}

# Game Settings
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

# --- UI CLASSES ---
class Button:
    def __init__(self, x, y, width, height, text, color, hover_color, font_size=40):
        self.rect, self.text, self.color, self.hover_color, self.font = pygame.Rect(x, y, width, height), text, color, hover_color, pygame.font.SysFont(None, font_size)
        self.is_hovered = False
    def draw(self, screen):
        draw_color = self.hover_color if self.is_hovered else self.color; pygame.draw.rect(screen, draw_color, self.rect, border_radius=10)
        text_surf = self.font.render(self.text, True, WHITE); screen.blit(text_surf, text_surf.get_rect(center=self.rect.center))
    def check_hover(self, mouse_pos): self.is_hovered = self.rect.collidepoint(mouse_pos)
    def is_clicked(self, event): return self.is_hovered and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1

class PlayerCard:
    def __init__(self, x, y, width, height, player_data):
        self.rect = pygame.Rect(x, y, width, height)
        self.player_data = player_data; self.name = player_data['Player']
        self.stats = player_data[['Position', 'Pace', 'Shooting', 'Dribbling', 'Passing', 'Defense']]
        self.is_hovered = False
        self.name_font = pygame.font.SysFont(None, 24); self.stat_font = pygame.font.SysFont(None, 20)
    def draw(self, screen, is_selected):
        if is_selected: pygame.draw.rect(screen, CARD_SELECTED_COLOR, self.rect, 4, border_radius=12)
        bg_color = CARD_HOVER_COLOR if self.is_hovered else CARD_COLOR
        pygame.draw.rect(screen, bg_color, self.rect.inflate(-8, -8), border_radius=8)
        name_surf = self.name_font.render(self.name, True, WHITE); screen.blit(name_surf, (self.rect.x + 10, self.rect.y + 10))
        y_offset = 40
        for stat, value in self.stats.items():
            stat_text = f"{stat}: {value}"; stat_surf = self.stat_font.render(stat_text, True, WHITE)
            screen.blit(stat_surf, (self.rect.x + 10, self.rect.y + y_offset)); y_offset += 18
    def check_hover(self, mouse_pos): self.is_hovered = self.rect.collidepoint(mouse_pos)
    def is_clicked(self, event): return self.is_hovered and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1

class Particle:
    def __init__(self, x, y, color, size_max=8):
        self.x, self.y, self.color = x, y, color; self.size = random.randint(4, size_max); self.life = 20; self.vx = random.uniform(-1, 1); self.vy = random.uniform(-1, 1)
    def update(self): self.x += self.vx; self.y += self.vy; self.size *= 0.9; self.life -= 1
    def draw(self, screen):
        if self.life > 0 and self.size > 1:
            s = pygame.Surface((int(self.size*2), int(self.size*2)), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, 150), (int(self.size), int(self.size)), int(self.size))
            screen.blit(s, (self.x - self.size, self.y - self.size))

# <<<<<<< TOURNAMENT CLASS >>>>>>>
class Tournament:
    def __init__(self, user_team, ai_teams):
        self.user_team = user_team
        self.all_teams = [user_team] + ai_teams[:3] # Ensure 4 teams total
        random.shuffle(self.all_teams) # Random bracket placement
        
        # Bracket Structure: [ [Semi1_TeamA, Semi1_TeamB], [Semi2_TeamA, Semi2_TeamB] ]
        self.semi_finals = [ [self.all_teams[0], self.all_teams[1]], [self.all_teams[2], self.all_teams[3]] ]
        self.final = [None, None] # Winners of semis
        self.champion = None
        
        self.current_round = "SEMI" # SEMI or FINAL
        self.user_status = "ALIVE" # ALIVE, ELIMINATED, CHAMPION

    def get_opponent(self):
        if self.current_round == "SEMI":
            if self.user_team in self.semi_finals[0]: return self.semi_finals[0][0] if self.semi_finals[0][1] == self.user_team else self.semi_finals[0][1]
            else: return self.semi_finals[1][0] if self.semi_finals[1][1] == self.user_team else self.semi_finals[1][1]
        elif self.current_round == "FINAL":
            return self.final[0] if self.final[1] == self.user_team else self.final[1]
        return None

    def advance_tournament(self, user_won):
        if self.current_round == "SEMI":
            # Resolve User Match
            if user_won:
                if self.user_team in self.semi_finals[0]: self.final[0] = self.user_team
                else: self.final[1] = self.user_team
            else:
                self.user_status = "ELIMINATED"
                # If user lost, the opponent advances
                opponent = self.get_opponent()
                if self.user_team in self.semi_finals[0]: self.final[0] = opponent
                else: self.final[1] = opponent

            # Simulate Other Match
            other_match_idx = 1 if self.user_team in self.semi_finals[0] else 0
            other_match = self.semi_finals[other_match_idx]
            winner = random.choice(other_match) # Simple random simulation
            if other_match_idx == 0: self.final[0] = winner
            else: self.final[1] = winner
            
            if self.user_status == "ALIVE":
                self.current_round = "FINAL"
        
        elif self.current_round == "FINAL":
            if user_won: self.user_status = "CHAMPION"; self.champion = self.user_team
            else: self.user_status = "ELIMINATED"; self.champion = self.get_opponent()

    def draw_bracket(self, screen):
        screen.fill(BLACK)
        font = pygame.font.SysFont(None, 40)
        small_font = pygame.font.SysFont(None, 30)
        title = pygame.font.SysFont(None, 60).render("MLS CUP BRACKET", True, GOLD)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))

        # Draw Semi Finals
        # Left Match
        t1 = self.semi_finals[0][0].replace('_', ' ').title()
        t2 = self.semi_finals[0][1].replace('_', ' ').title()
        color1 = GOLD if self.semi_finals[0][0] == self.user_team else WHITE
        color2 = GOLD if self.semi_finals[0][1] == self.user_team else WHITE
        
        pygame.draw.line(screen, WHITE, (150, 200), (300, 200), 2)
        pygame.draw.line(screen, WHITE, (150, 400), (300, 400), 2)
        pygame.draw.line(screen, WHITE, (300, 200), (300, 400), 2) # Connector
        pygame.draw.line(screen, WHITE, (300, 300), (400, 300), 2) # To Final

        screen.blit(small_font.render(t1, True, color1), (50, 190))
        screen.blit(small_font.render(t2, True, color2), (50, 390))

        # Right Match
        t3 = self.semi_finals[1][0].replace('_', ' ').title()
        t4 = self.semi_finals[1][1].replace('_', ' ').title()
        color3 = GOLD if self.semi_finals[1][0] == self.user_team else WHITE
        color4 = GOLD if self.semi_finals[1][1] == self.user_team else WHITE

        pygame.draw.line(screen, WHITE, (850, 200), (700, 200), 2)
        pygame.draw.line(screen, WHITE, (850, 400), (700, 400), 2)
        pygame.draw.line(screen, WHITE, (700, 200), (700, 400), 2) # Connector
        pygame.draw.line(screen, WHITE, (700, 300), (600, 300), 2) # To Final

        screen.blit(small_font.render(t3, True, color3), (710, 190))
        screen.blit(small_font.render(t4, True, color4), (710, 390))

        # Final
        final_rect = pygame.Rect(400, 250, 200, 100)
        pygame.draw.rect(screen, (50, 50, 50), final_rect, border_radius=10)
        pygame.draw.rect(screen, GOLD, final_rect, 2, border_radius=10)
        
        if self.final[0]:
            f1 = self.final[0].replace('_', ' ').title()
            c1 = GOLD if self.final[0] == self.user_team else WHITE
            screen.blit(small_font.render(f1, True, c1), (420, 270))
            screen.blit(small_font.render("VS", True, ORANGE), (490, 300))
        if self.final[1]:
            f2 = self.final[1].replace('_', ' ').title()
            c2 = GOLD if self.final[1] == self.user_team else WHITE
            screen.blit(small_font.render(f2, True, c2), (420, 330))
        
        # Champion
        if self.champion:
            champ_text = pygame.font.SysFont(None, 80).render(f"CHAMPION: {self.champion.replace('_',' ').title()}", True, GOLD)
            screen.blit(champ_text, (WIDTH//2 - champ_text.get_width()//2, 550))
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

# --- GAME OBJECT CLASSES ---
class Player:
    def __init__(self, x, y, team_name, name, stats_dict):
        self.x, self.y, self.name, self.stats = x, y, name, stats_dict
        self.team_name = team_name
        
        if 'ai' in team_name: self.color = TEAM_COLORS.get(team_name, TEAM_COLORS['default_ai'])
        else: self.color = TEAM_COLORS.get(team_name, TEAM_COLORS['default_player'])

        self.height_cm = self.stats.get('Height', BASE_PLAYER_HEIGHT_CM); self.weight_kg = self.stats.get('Weight', 75); self.race = self.stats.get('Race', 'Unknown')
        self.skin_tone = RACE_SKIN_MAP.get(self.race, DEFAULT_SKIN_TONE)
        self.height_scale = self.height_cm / BASE_PLAYER_HEIGHT_CM
        base_head_radius = 8; base_body_width, base_body_height = 18, 25; base_leg_width, base_leg_height = 6, 15; base_arm_width, base_arm_height = 4, 18
        self.head_radius = int(base_head_radius * (1 + (self.height_scale - 1) * 0.5)); self.body_width = int(base_body_width * (1 + (self.height_scale - 1) * 0.2)); self.body_height = int(base_body_height * self.height_scale)
        self.leg_width = int(base_leg_width * (1 + (self.height_scale - 1) * 0.2)); self.leg_height = int(base_leg_height * self.height_scale); self.arm_width = int(base_arm_width * (1 + (self.height_scale - 1) * 0.2)); self.arm_height = int(base_arm_height * self.height_scale)
        total_width = self.body_width + 2 * self.arm_width; total_height = self.head_radius * 2 + self.body_height + self.leg_height
        self.rect = pygame.Rect(x - total_width//2, y - self.head_radius, total_width, total_height)
        self.stamina, self.max_stamina = 100, 100; self.is_pressing = False
        self.direction_vector = pygame.Vector2(0, 0); self.home_position = pygame.Vector2(x, y)
        self.font = pygame.font.SysFont(None, 20); self.goals = 0; self.super_armor_timer = 0
        self.position = self.stats.get('Position', 'MF'); self.pace = self.stats.get('Pace', AVERAGE_PACE)
        self.attack_direction = 1 if self.home_position.x < WIDTH / 2 else -1

    def get_pos(self): return pygame.Vector2(self.x, self.y)
    
    def move(self, keys, ball_owner):
        sprinting = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        speed_multiplier = 1.0
        if not ball_owner and self.stats.get('Dribbling', 0) >= 15 and self.stats.get('Passing', 0) >= 10: speed_multiplier = 1.35 
        calculated_speed = BASE_PLAYER_SPEED + (self.pace * PACE_MODIFIER)
        current_speed = calculated_speed * speed_multiplier * (1.5 if sprinting and self.stamina > 0 else 1)
        self.direction_vector.x = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]; self.direction_vector.y = keys[pygame.K_DOWN] - keys[pygame.K_UP]
        if self.direction_vector.length() > 0: self.direction_vector.normalize_ip()
        self.x += self.direction_vector.x * current_speed; self.y += self.direction_vector.y * current_speed
        if sprinting and self.stats.get('Dribbling', 0) >= 18 and self.super_armor_timer <= 0: self.super_armor_timer = SUPER_ARMOR_DURATION
        if self.super_armor_timer > 0: self.super_armor_timer -= 1
        if sprinting and self.stamina > 0: self.stamina -= 1
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
        name_surf = self.font.render(self.name, True, WHITE); bg_rect = name_surf.get_rect(center=(int(self.x), int(self.y - self.head_radius - 10))); bg_surface = pygame.Surface((bg_rect.width+4, bg_rect.height+4), pygame.SRCALPHA); bg_surface.fill(TEXT_BG_COLOR); screen.blit(bg_surface, (bg_rect.left - 2, bg_rect.top - 2)); screen.blit(name_surf, bg_rect)
        if self.is_pressing: press_indicator_center = (int(self.x), int(self.y + self.body_height + self.leg_height + 10)); pygame.draw.circle(screen, TACKLE_INDICATOR_COLOR, press_indicator_center, 15, 3)
        if self.super_armor_timer > 0: pygame.draw.circle(screen, GOLD, (int(self.x), int(self.y)), 30, 2)
        
    def reset(self): self.x, self.y = self.home_position.x, self.home_position.y; self.rect.center = (self.x, self.y - self.head_radius + self.rect.height // 2) ; self.stamina = self.max_stamina; self.super_armor_timer = 0
    
    def tackle(self, ball, opponent_team):
        target_player = ball.owner
        if target_player in opponent_team and self.get_pos().distance_to(target_player.get_pos()) < TACKLE_RADIUS:
            tackle_success_prob = 1.0 if self.stats.get('Defense', 0) >= 18 else (self.stats.get('Defense', 10) / 20) * 0.7
            if hasattr(target_player, 'super_armor_timer') and target_player.super_armor_timer > 0: tackle_success_prob = 0
            if random.random() < tackle_success_prob: tackle_sound.play(); ball.owner = None; ball.last_toucher = self; ball.last_touch_time = pygame.time.get_ticks()
    
    def update_ai_movement(self, ball, team_has_ball, target_override=None):
        speed_multiplier = 1.0
        if not team_has_ball and self.stats.get('Dribbling', 0) >= 15 and self.stats.get('Passing', 0) >= 10: speed_multiplier = 1.35
        base_def_x = 200 if self.attack_direction == 1 else WIDTH - 200
        base_mid_x = 400 if self.attack_direction == 1 else WIDTH - 400
        base_fwd_x = 600 if self.attack_direction == 1 else WIDTH - 600
        
        if target_override: target_pos = target_override
        elif team_has_ball: # Attacking
            if self.position == 'FW': target_pos = pygame.Vector2(base_fwd_x + (100 * self.attack_direction), self.home_position.y)
            elif self.position == 'MF': target_pos = pygame.Vector2(base_mid_x, self.home_position.y)
            else: target_pos = pygame.Vector2(base_def_x, self.home_position.y)
        else: # Defending
            if self.position == 'FW': target_pos = self.home_position.lerp(pygame.Vector2(ball.x, ball.y), 0.2)
            elif self.position == 'MF': target_pos = self.home_position.lerp(pygame.Vector2(ball.x, ball.y), 0.5)
            else: target_pos = self.home_position.lerp(pygame.Vector2(ball.x, ball.y), 0.7)
        
        direction = target_pos - self.get_pos()
        if direction.length() > 20:
            direction.normalize_ip()
            calculated_speed = (BASE_PLAYER_SPEED + (self.pace * PACE_MODIFIER)) * 0.8
            current_speed = calculated_speed * speed_multiplier
            self.x += direction.x * current_speed; self.y += direction.y * current_speed
            self.rect.center = (self.x, self.y - self.head_radius + self.rect.height // 2)

class AIPlayer(Player):
    def update(self, ball, player_team, ai_team, is_presser, game_stats):
        self.is_pressing = is_presser
        if ball.owner == self:
            target_goal_x = WIDTH - 15 if self.attack_direction == 1 else 15
            goal_center = pygame.Vector2(target_goal_x, HEIGHT/2)
            dist_to_goal = self.get_pos().distance_to(goal_center); weights = {"shoot": self.stats.get('Shooting',10), "pass": self.stats.get('Passing',10), "dribble": self.stats.get('Dribbling',10)}
            if dist_to_goal < 300: weights['shoot'] *= 1.5
            action = random.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]
            
            if action == "shoot" and dist_to_goal < 400:
                game_stats["AI"]["Shots"] += 1; shot_angle = math.atan2(goal_center.y-self.y, goal_center.x-self.x); shot_prob = 0.8; speed = BALL_SPEED; spin = 0
                foot = self.stats.get('Preferred Foot', 'Right')
                if self.stats.get('Shooting', 0) >= 15 and self.stats.get('Passing', 0) >= 12: 
                    shot_prob += 0.15
                    if foot == 'Right': spin = -0.3
                    elif foot == 'Left': spin = 0.3
                    elif foot == 'Both': spin = random.choice([-0.3, 0.3])
                if self.stats.get('Shooting', 0) >= 18: speed *= 1.5
                shot_prob_final = (self.stats.get('Shooting', 10)/20) * shot_prob
                target_y_on_goal_line = self.y + math.sin(shot_angle) * abs(target_goal_x - self.x)
                if GOAL_Y_START < target_y_on_goal_line < GOAL_Y_START + GOAL_WIDTH: game_stats["AI"]["ShotsOnGoal"] += 1
                if random.random() > shot_prob_final: shot_angle += random.uniform(-0.4, 0.4)
                ball.shoot(shot_angle, speed, spin_effect=spin); return
            elif action == "pass":
                game_stats["AI"]["PassesAttempted"] += 1; teammate = find_best_pass_target(self, ai_team); angle = 0; pass_prob = 0.95
                if teammate: angle = math.atan2(teammate.y - self.y, teammate.x - self.x)
                if self.stats.get('Passing', 0) >= 18: pass_prob = 1.0
                pass_prob_final = (self.stats.get('Passing', 10)/20) * pass_prob
                if random.random() > pass_prob_final: angle += random.uniform(-0.5, 0.5)
                if teammate: ball.shoot(angle, BALL_SPEED * 0.8); return
            self.update_ai_movement(ball, True, goal_center)
        else:
            if is_presser: self.update_ai_movement(ball, False, pygame.Vector2(ball.x, ball.y)); self.tackle(ball, player_team)
            else: self.update_ai_movement(ball, False)
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
        target_y = ball.y; speed = 3.5
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
    def update(self):
        if self.owner:
            target_x = self.owner.rect.centerx + self.owner.direction_vector.x * DRIBBLE_DISTANCE; target_y = self.owner.rect.centery + self.owner.direction_vector.y * DRIBBLE_DISTANCE
            self.x += (target_x - self.x) * DRIBBLE_SPEED; self.y += (target_y - self.y) * DRIBBLE_SPEED; self.vx, self.vy = 0, 0
            self.spin_effect = 0
        else:
            self.x += self.vx; self.y += self.vy
            if self.spin_effect != 0:
                self.vy += self.spin_effect * abs(self.vx) * 0.3
                self.spin_effect *= 0.95
                if abs(self.spin_effect) < 0.001: self.spin_effect = 0
            self.vx *= 0.97; self.vy *= 0.97
        if self.y <= self.radius or self.y >= HEIGHT - self.radius: self.vy *= -0.8; self.spin_effect *= -0.5
        if self.x <= self.radius or self.x >= WIDTH - self.radius: self.vx *= -0.8; self.spin_effect = 0
        self.rect.center = (int(self.x), int(self.y))
    def shoot(self, angle, speed, spin_effect=0):
        kick_sound.play()
        if self.owner:
            self.last_toucher = self.owner; self.last_touch_time = pygame.time.get_ticks(); self.last_toucher_team = self.owner.team_name
        self.vx, self.vy = speed*math.cos(angle), speed*math.sin(angle); self.owner = None; self.spin_effect = spin_effect
    def draw(self, screen):
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius)
        if self.owner: pygame.draw.circle(screen, WHITE, (self.owner.rect.centerx, self.owner.rect.centery + 20), self.radius + 2, 2)
    def reset(self): self.x,self.y,self.vx,self.vy,self.owner = WIDTH//2,HEIGHT//2,0,0,None; self.last_toucher = None; self.last_toucher_team = None; self.spin_effect = 0

# --- HELPER & DRAWING FUNCTIONS ---
def draw_playing_field(screen): screen.fill(GREEN); pygame.draw.rect(screen, WHITE, (0, GOAL_Y_START, 15, GOAL_WIDTH)); pygame.draw.rect(screen, WHITE, (WIDTH - 15, GOAL_Y_START, 15, GOAL_WIDTH)); pygame.draw.line(screen, WHITE, (WIDTH // 2, 0), (WIDTH // 2, HEIGHT), 2); pygame.draw.circle(screen, WHITE, (WIDTH // 2, HEIGHT // 2), 70, 2)
def draw_hud(screen, player, score, timer, team_names, user_team_name=None): 
    font = pygame.font.SysFont(None, 40)
    p_color = TEAM_COLORS.get(team_names['player_code'], WHITE); ai_color = TEAM_COLORS.get(team_names['ai_code'], WHITE)
    if p_color == BLACK: p_color = (50, 50, 50) 
    if ai_color == BLACK: ai_color = (50, 50, 50)
    score_text = font.render(f"{team_names['player']} {score['Player']} - {score['AI']} {team_names['ai']}", True, WHITE)
    screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, 10))
    mins, secs = int(timer//60), int(timer%60); timer_text = font.render(f"{mins:02}:{secs:02}", True, WHITE); screen.blit(timer_text, (WIDTH-100, 10))
    pygame.draw.rect(screen, BLACK, (19,19,202,22)); pygame.draw.rect(screen, (0,255,0), (20,20, 200*(player.stamina/player.max_stamina), 20))
def draw_screen_title(screen, title): title_font = pygame.font.SysFont(None, 70); title_surf = title_font.render(title, True, WHITE); screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 60))
def find_closest_player_to_ball(team, ball, exclude_player=None): return min([p for p in team if p != exclude_player and isinstance(p, Player)], key=lambda p_to_check: p_to_check.get_pos().distance_to(pygame.Vector2(ball.x, ball.y)), default=None)
def find_best_pass_target(player, team):
    best_target, highest_score = None, -1
    for teammate in team:
        if teammate == player or not isinstance(teammate, Player): continue
        distance = player.get_pos().distance_to(teammate.get_pos())
        forwardness = (teammate.x - player.x) * player.attack_direction 
        if distance > 0: score = (100 / distance) + (forwardness * 0.1)
        if score > highest_score: highest_score, best_target = score, teammate
    return best_target

def draw_stats_screen(screen, game_objects):
    stats = game_objects.get('game_stats'); teams = game_objects.get('team_names'); score = game_objects.get('score')
    if not stats or not teams or not score: return
    total_time = stats['Player']['PossessionTime'] + stats['AI']['PossessionTime']; player_poss_pct = (stats['Player']['PossessionTime'] / total_time) * 100 if total_time > 0 else 50; ai_poss_pct = 100 - player_poss_pct
    all_players = game_objects.get('player_team', []) + game_objects.get('ai_team', [])
    mom = max([p for p in all_players if isinstance(p, Player)], key=lambda p: p.goals) if any(p.goals > 0 for p in all_players if isinstance(p, Player)) else None
    screen.fill((10, 20, 40)); draw_screen_title(screen, "Match Statistics")
    font_header = pygame.font.SysFont(None, 50); font_stat = pygame.font.SysFont(None, 36)
    player_team_color = TEAM_COLORS.get(game_objects['user_team'], TEAM_COLORS['default_player'])
    ai_team_color = TEAM_COLORS.get(game_objects.get('ai_team_name', 'default_ai'), TEAM_COLORS['default_ai'])
    player_header = font_header.render(teams['player'], True, player_team_color); ai_header = font_header.render(teams['ai'], True, ai_team_color)
    screen.blit(player_header, (WIDTH*0.25-player_header.get_width()//2, 150)); screen.blit(ai_header, (WIDTH*0.75-ai_header.get_width()//2, 150))
    stat_y = 220; stat_list = ["Score", "Shots", "Shots on Goal", "Possession", "Passes (Comp/Att)"]
    player_stats = [score['Player'], stats['Player']['Shots'], stats['Player']['ShotsOnGoal'], f"{player_poss_pct:.1f}%", f"{stats['Player']['PassesCompleted']}/{stats['Player']['PassesAttempted']}"]
    ai_stats = [score['AI'], stats['AI']['Shots'], stats['AI']['ShotsOnGoal'], f"{ai_poss_pct:.1f}%", f"{stats['AI']['PassesCompleted']}/{stats['AI']['PassesAttempted']}"]
    for i, stat_name in enumerate(stat_list):
        name_surf = font_header.render(stat_name, True, WHITE); screen.blit(name_surf, (WIDTH//2 - name_surf.get_width()//2, stat_y + i*50))
        player_stat_surf = font_stat.render(str(player_stats[i]), True, player_team_color); screen.blit(player_stat_surf, (WIDTH*0.25-player_stat_surf.get_width()//2, stat_y + i*50))
        ai_stat_surf = font_stat.render(str(ai_stats[i]), True, ai_team_color); screen.blit(ai_stat_surf, (WIDTH*0.75-ai_stat_surf.get_width()//2, stat_y + i*50))
    if mom: mom_text = f"Man of the Match: {mom.name} ({mom.goals} Goals)"; mom_surf = font_header.render(mom_text, True, GOLD); screen.blit(mom_surf, (WIDTH//2 - mom_surf.get_width()//2, HEIGHT-180))
    nav_font = pygame.font.SysFont(None, 30); nav_text = nav_font.render("Press ENTER to return to Menu", True, WHITE); screen.blit(nav_text, (WIDTH//2 - nav_text.get_width()//2, HEIGHT-80))

# --- RESET GAME FUNCTION ---
def reset_game(player_team_name, ai_team_name, selected_players):
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
    game_objects['particles'] = []
    game_objects['user_team'] = player_team_name
    game_objects['ai_team_name'] = ai_team_name # <<<<< FIXED: Don't overwrite 'ai_team' list
    return game_objects

# --- STATE HANDLERS ---
def handle_menu_state(events, mouse_pos, menu_buttons, tournament):
    for event in events:
        if menu_buttons['start'].is_clicked(event): return "TEAM_SELECTION", None
        if menu_buttons['mls_cup'].is_clicked(event): return "TEAM_SELECTION_TOURNAMENT", None # New signal
        if menu_buttons['quit'].is_clicked(event): return "QUIT", None
    screen.fill(GREEN); draw_screen_title(screen, "Data-Driven Soccer")
    for button in menu_buttons.values(): button.check_hover(mouse_pos); button.draw(screen)
    return "MENU", None

def handle_team_selection_state(events, mouse_pos, team_buttons, is_tournament=False):
    for event in events:
        for team_name, button in team_buttons.items():
            if button.is_clicked(event): return "PLAYER_SELECTION", team_name
    screen.fill(GREEN); draw_screen_title(screen, "Choose Your Team (MLS Cup)" if is_tournament else "Choose Your Team")
    for button in team_buttons.values(): button.check_hover(mouse_pos); button.draw(screen)
    return "TEAM_SELECTION" if not is_tournament else "TEAM_SELECTION_TOURNAMENT", None

def handle_player_selection_state(events, mouse_pos, user_team, player_cards, selected_players, start_match_button, is_tournament=False, tournament=None):
    for event in events:
        for card in player_cards:
            if card.is_clicked(event):
                if card.name in selected_players: selected_players.remove(card.name)
                elif len(selected_players) < 3: selected_players.append(card.name)
        if len(selected_players) == 3 and start_match_button.is_clicked(event):
            if is_tournament:
                # Init Tournament
                opponents = [t for t in player_profiles_df['Team'].unique() if t != user_team]
                random.shuffle(opponents)
                ai_teams = opponents[:3]
                tournament = Tournament(user_team, ai_teams)
                return "TOURNAMENT_BRACKET", tournament
            else:
                # Friendly Match
                opponents = [t for t in player_profiles_df['Team'].unique() if t != user_team]; ai_team = random.choice(opponents)
                game_objects = reset_game(user_team, ai_team, selected_players)
                if game_objects: whistle_sound.play(); return "PLAYING", game_objects

    screen.fill(GREEN); draw_screen_title(screen, "Select Your Squad (3 Players)")
    for card in player_cards: card.check_hover(mouse_pos); card.draw(screen, card.name in selected_players)
    if len(selected_players) == 3: start_match_button.check_hover(mouse_pos); start_match_button.draw(screen)
    return "PLAYER_SELECTION", None

def handle_tournament_bracket_state(events, mouse_pos, tournament, selected_players, play_match_button):
    for event in events:
        if tournament.current_round == "SEMI" or tournament.current_round == "FINAL":
             if tournament.user_status == "ALIVE" and play_match_button.is_clicked(event):
                opponent = tournament.get_opponent()
                game_objects = reset_game(tournament.user_team, opponent, selected_players)
                if game_objects: whistle_sound.play(); return "PLAYING", game_objects
        if tournament.user_status == "ELIMINATED" or tournament.user_status == "CHAMPION":
             if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN: return "MENU", None

    tournament.draw_bracket(screen)
    if tournament.user_status == "ALIVE":
        play_match_button.check_hover(mouse_pos); play_match_button.draw(screen)
    else:
        msg = "Eliminated! Press Enter." if tournament.user_status == "ELIMINATED" else "Champion! Press Enter."
        font = pygame.font.SysFont(None, 40)
        text = font.render(msg, True, WHITE)
        screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT - 100))
    
    return "TOURNAMENT_BRACKET", None

def handle_playing_state(events, keys, game_objects, active_idx, elapsed_time):
    # Same logic as before, just need to return score at end
    for event in events:
        if event.type == pygame.KEYDOWN:
            active_player, ball = game_objects['player_team'][active_idx], game_objects['ball']
            if event.key == pygame.K_q:
                new_player = find_closest_player_to_ball(game_objects['player_team'],ball,active_player)
                if new_player: active_idx = game_objects['player_team'].index(new_player)
            if event.key == pygame.K_s and ball.owner == active_player:
                game_objects['game_stats']['Player']['PassesAttempted'] += 1; teammate = find_best_pass_target(active_player, game_objects['player_team']); angle = 0; pass_prob = 0.95
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
                if active_player.stats.get('Shooting', 0) >= 18: speed *= 1.5
                shot_prob_final = (active_player.stats.get('Shooting', 10)/20) * shot_prob
                if GOAL_Y_START < active_player.y + math.sin(angle) * (WIDTH - active_player.x) < GOAL_Y_START + GOAL_WIDTH: game_objects['game_stats']['Player']['ShotsOnGoal'] += 1
                if random.random() > shot_prob_final: angle += random.uniform(-0.4, 0.4)
                ball.shoot(angle, speed, spin_effect=spin)

    player_team, ai_team, ball = game_objects['player_team'], game_objects['ai_team'], game_objects['ball']
    active_player = player_team[active_idx]; active_player.move(keys, ball.owner == active_player)
    if ball.owner in player_team: game_objects['game_stats']['Player']['PossessionTime'] += elapsed_time
    elif ball.owner in ai_team: game_objects['game_stats']['AI']['PossessionTime'] += elapsed_time
    is_pressing = keys[pygame.K_d]
    for p in player_team: p.is_pressing = False
    if is_pressing:
        active_player.is_pressing = True; active_player.tackle(ball, ai_team)
        teammate_for_press = find_closest_player_to_ball(player_team, ball, active_player)
        if teammate_for_press: teammate_for_press.is_pressing = True; teammate_for_press.update_ai_movement(ball, False, pygame.Vector2(ball.x, ball.y))
    player_has_ball = ball.owner in player_team
    for p in player_team:
        if p != active_player and not p.is_pressing: p.update_ai_movement(ball, player_has_ball)
    presser = find_closest_player_to_ball(ai_team, ball)
    for p in ai_team: p.update(ball, player_team, ai_team, is_presser=(p == presser), game_stats=game_objects['game_stats'])
    game_objects['player_goalie'].update(ball); game_objects['ai_goalie'].update(ball)
    current_time = pygame.time.get_ticks()
    for p in player_team + ai_team:
        if ball.owner is None and p.rect.colliderect(ball.rect) and (p != ball.last_toucher or current_time - ball.last_touch_time > 200):
            ball.owner = p
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
    
    ball.update()
    if game_objects['player_goalie'].rect.colliderect(ball.rect) or game_objects['ai_goalie'].rect.colliderect(ball.rect): ball.vx*=-0.5; ball.vy*=-0.5; ball.owner=None
    goal_scored = False
    if ball.rect.colliderect((WIDTH-15, GOAL_Y_START, 15, GOAL_WIDTH)): 
        if ball.last_toucher and ball.last_toucher.team_name == game_objects['user_team']: 
            game_objects['score']["Player"]+=1; goal_sound.play(); ball.last_toucher.goals += 1; goal_scored=True
    elif ball.rect.colliderect((0, GOAL_Y_START, 15, GOAL_WIDTH)): 
         # <<<<< FIXED: Check against 'ai_team_name', not 'ai_team' (which is the list)
         if ball.last_toucher and ball.last_toucher.team_name == game_objects.get('ai_team_name'):
            game_objects['score']["AI"]+=1; goal_sound.play(); ball.last_toucher.goals += 1; goal_scored=True
    if goal_scored: [p.reset() for p in player_team+ai_team]; ball.reset()
    timer = GAME_DURATION_SECONDS - ((pygame.time.get_ticks()-game_objects['start_ticks'])/1000)
    if timer <= 0: whistle_sound.play(); return "POST_GAME", active_idx

    draw_playing_field(screen)
    all_game_players = player_team + ai_team
    for p in all_game_players: p.draw(screen)
    for p in game_objects['particles']: p.draw(screen) 
    indicator_points = [(active_player.rect.centerx, active_player.rect.top-20), (active_player.rect.centerx-7, active_player.rect.top-13), (active_player.rect.centerx+7, active_player.rect.top-13)]
    pygame.draw.polygon(screen, GOLD, indicator_points)
    game_objects['player_goalie'].draw(screen); game_objects['ai_goalie'].draw(screen); ball.draw(screen)
    draw_hud(screen, active_player, game_objects['score'], timer, game_objects['team_names'])
    return "PLAYING", active_idx

def handle_post_game_state(events, game_objects, is_tournament, tournament):
    for event in events:
        if event.type == pygame.KEYDOWN and (event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER):
            if is_tournament:
                user_won = game_objects['score']['Player'] > game_objects['score']['AI']
                tournament.advance_tournament(user_won)
                return "TOURNAMENT_BRACKET"
            else:
                return "MENU"
    draw_stats_screen(screen, game_objects)
    return "POST_GAME"

# --- MAIN GAME LOOP ---
def main():
    clock = pygame.time.Clock(); game_state = "MENU"
    menu_buttons = {
        "start": Button(WIDTH//2-100, 300, 200, 60, "Friendly", BLUE, (0,100,255)),
        "mls_cup": Button(WIDTH//2-100, 400, 200, 60, "MLS Cup", ORANGE, (255,200,0)), # MLS Cup Button Added
        "quit": Button(WIDTH//2-100, 500, 200, 60, "Quit", RED, (255,100,100))
    }
    team_buttons = {team: Button(WIDTH//2-150, 200+i*80, 300, 60, team.replace('_',' ').title(), ORANGE, (255,200,0), 36) for i, team in enumerate(player_profiles_df['Team'].unique())}
    
    game_objects, active_idx, user_team, player_cards, selected_players = {}, 0, None, [], []
    start_match_button = Button(WIDTH//2-125, HEIGHT-100, 250, 60, "Start Match", BLUE, (0,100,255))
    play_match_button = Button(WIDTH//2-125, 550, 250, 60, "Play Match", BLUE, (0,100,255))
    
    tournament = None
    is_tournament_mode = False
    
    running = True
    while running:
        elapsed_time = clock.tick(FPS); mouse_pos = pygame.mouse.get_pos(); events = pygame.event.get(); keys = pygame.key.get_pressed()
        for event in events:
            if event.type == pygame.QUIT: running = False

        if game_state == "MENU":
            next_state, _ = handle_menu_state(events, mouse_pos, menu_buttons, tournament)
            if next_state == "QUIT": running = False
            elif next_state == "TEAM_SELECTION": game_state = "TEAM_SELECTION"; is_tournament_mode = False
            elif next_state == "TEAM_SELECTION_TOURNAMENT": game_state = "TEAM_SELECTION"; is_tournament_mode = True
            
        elif game_state == "TEAM_SELECTION":
            next_state, team_choice = handle_team_selection_state(events, mouse_pos, team_buttons, is_tournament_mode)
            if team_choice:
                user_team, game_state, selected_players = team_choice, next_state, []
                roster = player_profiles_df[player_profiles_df['Team'] == user_team]; player_cards = []
                card_width, card_height, gap = 140, 160, 20; num_cols = 5; total_width = (card_width + gap) * num_cols - gap; start_x = (WIDTH - total_width) // 2
                for i, p_data in enumerate(roster.iterrows()):
                    row, col = i // num_cols, i % num_cols; x, y = start_x + col * (card_width + gap), 150 + row * (card_height + gap)
                    player_cards.append(PlayerCard(x, y, card_width, card_height, p_data[1]))

        elif game_state == "PLAYER_SELECTION":
            next_state, result = handle_player_selection_state(events, mouse_pos, user_team, player_cards, selected_players, start_match_button, is_tournament_mode, tournament)
            if next_state == "PLAYING":
                 game_objects, game_state, active_idx = result, "PLAYING", 0
            elif next_state == "TOURNAMENT_BRACKET":
                 tournament, game_state = result, "TOURNAMENT_BRACKET"

        elif game_state == "TOURNAMENT_BRACKET":
            next_state, new_game_objects = handle_tournament_bracket_state(events, mouse_pos, tournament, selected_players, play_match_button)
            if next_state == "PLAYING":
                game_objects, game_state, active_idx = new_game_objects, "PLAYING", 0
            elif next_state == "MENU":
                game_state = "MENU"

        elif game_state == "PLAYING":
            game_state, active_idx = handle_playing_state(events, keys, game_objects, active_idx, elapsed_time)
            
        elif game_state == "POST_GAME":
            game_state = handle_post_game_state(events, game_objects, is_tournament_mode, tournament)
        
        pygame.display.flip()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()