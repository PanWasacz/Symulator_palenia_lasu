import pygame
import random
import numpy as np
import math

# --- KONFIGURACJA STARTOWA ---
START_CELL_SIZE = 5
START_GRID_WIDTH = 300
START_GRID_HEIGHT = 200
FPS = 60

# Prawdopodobieństwa BAZOWE
P_SPREAD_BASE = 0.25
P_GROW_BASE = 0.0005
P_ASH_DECAY_BASE = 0.005
FIRE_DECAY_BASE = 0.15
P_DESERT_SPREAD = 0.03  # Bardzo wolne rozprzestrzenianie pustyni

# Stany komórek
EMPTY = 0
TREE_YOUNG = 1
TREE_MATURE = 2
TREE_OLD = 3
FIRE = 4
ASH = 6
WATER = 7
ROCK = 8
FIREBREAK = 9
DESERT = 10

# Kolory z wariacjami dla lepszej grafiki
def get_water_color(x, y, step):
    """Animowane fale wody z jaśniejszymi smugami"""
    wave1 = math.sin((x * 0.3 + y * 0.2 + step * 0.08)) * 20
    wave2 = math.cos((x * 0.2 - y * 0.3 + step * 0.05)) * 15
    
    combined_wave = wave1 + wave2
    
    r = max(20, min(60, 30 + int(combined_wave * 0.3)))
    g = max(80, min(130, 100 + int(combined_wave * 0.5)))
    b = max(180, min(255, 220 + int(combined_wave)))
    
    return (r, g, b)

def get_rock_color(x, y):
    """Zróżnicowane kolory skał - różne odcienie szarości"""
    seed_val = hash((x, y)) % 100
    
    if seed_val < 20:
        base = 50 + (seed_val % 15)
        return (base, base, base + 5)
    elif seed_val < 60:
        base = 70 + (seed_val % 25)
        return (base, base - 5, base)
    else:
        base = 95 + (seed_val % 30)
        return (base, base, base + 10)

def get_tree_color(state, age):
    """Kolory drzew z wiekiem"""
    if state == TREE_YOUNG:
        green_val = 220 + (age % 35)
        return (80, min(255, green_val), 80)
    elif state == TREE_MATURE:
        green_val = 139 - (age % 20)
        return (34, green_val, 34)
    else:  # OLD
        green_val = 60 + (age % 20)
        return (0, green_val, 0)

def get_desert_color(x, y):
    """Zróżnicowane kolory pustyni - odcienie żółtego/piaskowego"""
    seed_val = hash((x, y)) % 100
    
    if seed_val < 30:
        return (194, 178, 128)  # Jasny piasek
    elif seed_val < 60:
        return (210, 180, 140)  # Tan
    elif seed_val < 85:
        return (222, 184, 135)  # Burly wood
    else:
        return (238, 203, 173)  # Jasny beż

# Podstawowe kolory (fallback)
COLORS = {
    EMPTY: (15, 15, 15),
    TREE_YOUNG: (100, 255, 100),
    TREE_MATURE: (34, 139, 34),
    TREE_OLD: (0, 80, 0),
    FIRE: (255, 69, 0),
    ASH: (80, 80, 80),
    WATER: (30, 100, 200),
    ROCK: (90, 90, 90),
    FIREBREAK: (139, 90, 43),
    DESERT: (210, 180, 140)
}

# PRESETY WARUNKÓW POGODOWYCH
WEATHER_PRESETS = {
    'very_wet': {
        'name': 'Bardzo wilgotny',
        'multiplier': 0.3,
        'color': (100, 150, 255)
    },
    'wet': {
        'name': 'Wilgotny',
        'multiplier': 0.6,
        'color': (150, 200, 255)
    },
    'normal': {
        'name': 'Normalny',
        'multiplier': 1.0,
        'color': (200, 200, 200)
    },
    'dry': {
        'name': 'Suchy',
        'multiplier': 1.5,
        'color': (255, 200, 100)
    },
    'very_dry': {
        'name': 'Bardzo suchy',
        'multiplier': 2.2,
        'color': (255, 150, 50)
    },
    'extreme': {
        'name': 'EKSTREMALNY',
        'multiplier': 3.5,
        'color': (255, 50, 0)
    }
}

# --- INICJALIZACJA PYGAME ---
pygame.init()
pygame.display.set_caption("Symulacja Pozaru Lasu")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 38)
small_font = pygame.font.Font(None, 28)
tiny_font = pygame.font.Font(None, 22)


# --- KLASA SYMULACJI ---
class ForestFireSimulation:
    def __init__(self, width, height, cell_size):
        self.grid_width = width
        self.grid_height = height
        self.cell_size = cell_size
        self.ui_width = 320

        self.update_window_size()

        self.wind_direction = [1, 0]
        self.wind_strength = 1.0
        self.wind_mode = False
        self.cutting_mode = False

        self.paused = False
        self.simulation_speed = 1.0
        self.update_counter = 0

        self.current_weather = 'normal'
        self.burn_rate_multiplier = WEATHER_PRESETS['normal']['multiplier']

        self.update_burn_parameters()
        self.initialize_arrays()
        self.initialize_forest()

    def update_burn_parameters(self):
        """Aktualizuje wszystkie parametry spalania"""
        self.p_spread = P_SPREAD_BASE * self.burn_rate_multiplier
        self.p_grow = P_GROW_BASE / self.burn_rate_multiplier
        self.p_ash_decay = P_ASH_DECAY_BASE * self.burn_rate_multiplier
        self.fire_decay = FIRE_DECAY_BASE * self.burn_rate_multiplier

    def set_weather_preset(self, preset_key):
        """Ustawia preset pogodowy"""
        if preset_key in WEATHER_PRESETS:
            self.current_weather = preset_key
            self.burn_rate_multiplier = WEATHER_PRESETS[preset_key]['multiplier']
            self.update_burn_parameters()

    def update_window_size(self):
        self.window_width = self.grid_width * self.cell_size + self.ui_width
        self.window_height = self.grid_height * self.cell_size
        if self.window_height < 800:
            self.window_height = 800
        self.screen = pygame.display.set_mode((self.window_width, self.window_height))

    def initialize_arrays(self):
        self.grid = np.zeros((self.grid_height, self.grid_width), dtype=np.int8)
        self.age_grid = np.zeros((self.grid_height, self.grid_width), dtype=np.int16)
        self.fire_intensity = np.zeros((self.grid_height, self.grid_width), dtype=np.float32)
        self.water_width = np.zeros((self.grid_height, self.grid_width), dtype=np.float32)

    def change_grid_size(self, dw, dh):
        new_w = max(50, self.grid_width + dw)
        new_h = max(50, self.grid_height + dh)
        if new_w != self.grid_width or new_h != self.grid_height:
            self.grid_width = new_w
            self.grid_height = new_h
            self.initialize_arrays()
            self.update_window_size()
            self.initialize_forest()

    def change_cell_size(self, amount):
        new_size = max(1, min(20, self.cell_size + amount))
        if new_size != self.cell_size:
            self.cell_size = new_size
            self.update_window_size()

    def draw_circle_safe(self, cx, cy, radius, state, store_width=None):
        """
        Bezpieczne rysowanie kół - ZAKTUALIZOWANE
        NIE nadpisuje już istniejących obiektów (woda, góry, pustynia)
        """
        min_y = max(0, int(cy - radius))
        max_y = min(self.grid_height, int(cy + radius + 1))
        min_x = max(0, int(cx - radius))
        max_x = min(self.grid_width, int(cx + radius + 1))

        for y in range(min_y, max_y):
            for x in range(min_x, max_x):
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2:
                    current_state = self.grid[y][x]
                    
                    # NOWA LOGIKA: Chronione tereny
                    protected_states = {WATER, ROCK, DESERT}
                    
                    # Jeśli próbujemy narysować wodę
                    if state == WATER:
                        # Woda nie może być na: pustyni, górach, innej wodzie
                        if current_state in {DESERT, ROCK, WATER}:
                            continue
                    
                    # Jeśli próbujemy narysować góry
                    elif state == ROCK:
                        # Góry nie mogą być na: wodzie, pustyni, innych górach
                        if current_state in {WATER, DESERT, ROCK}:
                            continue
                    
                    # Jeśli próbujemy narysować pustynię
                    elif state == DESERT:
                        # Pustynia nie może być na: wodzie, górach, innej pustyni
                        if current_state in {WATER, ROCK, DESERT}:
                            continue
                    
                    # Rysuj tylko na pustych polach lub dozwolonych
                    if current_state == EMPTY or (state not in protected_states):
                        self.grid[y][x] = state
                        if state == WATER and store_width is not None:
                            self.water_width[y][x] = store_width

    def generate_natural_blob(self, count, state, min_r, max_r, roughness=10):
        """Generuje naturalne kształty (jeziora, góry, pustynie)"""
        for _ in range(count):
            # Większe marginesy żeby uniknąć nakładania na brzegach
            margin = 30
            cx = random.randint(margin, self.grid_width - margin)
            cy = random.randint(margin, self.grid_height - margin)

            base_radius = random.randint(min_r, max_r)
            self.draw_circle_safe(cx, cy, base_radius, state, store_width=base_radius)

            num_blobs = random.randint(roughness, roughness + 8)
            for _ in range(num_blobs):
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(base_radius * 0.4, base_radius * 1.1)

                ox = cx + math.cos(angle) * dist
                oy = cy + math.sin(angle) * dist

                blob_r = random.uniform(2, base_radius * 0.5)
                self.draw_circle_safe(ox, oy, blob_r, state, store_width=blob_r)

    def generate_rivers(self, num_rivers=2):
        """Generuje meandrujące rzeki z naturalnymi zakrętami"""
        for _ in range(num_rivers):
            edge = random.randint(0, 3)
            
            if edge == 0:
                x, y = random.randint(0, self.grid_width - 1), 0
                angle = random.uniform(math.pi * 0.25, math.pi * 0.75)
            elif edge == 1:
                x, y = random.randint(0, self.grid_width - 1), self.grid_height - 1
                angle = random.uniform(-math.pi * 0.75, -math.pi * 0.25)
            elif edge == 2:
                x, y = 0, random.randint(0, self.grid_height - 1)
                angle = random.uniform(-math.pi * 0.25, math.pi * 0.25)
            else:
                x, y = self.grid_width - 1, random.randint(0, self.grid_height - 1)
                angle = random.uniform(math.pi * 0.75, math.pi * 1.25)

            width = random.uniform(2.5, 4.5)
            steps = 0
            max_steps = max(self.grid_width, self.grid_height) * 3
            
            meander_frequency = random.uniform(0.03, 0.08)
            meander_amplitude = random.uniform(0.15, 0.3)

            while 0 <= x < self.grid_width and 0 <= y < self.grid_height and steps < max_steps:
                self.draw_circle_safe(x, y, width, WATER, store_width=width)
                
                angle += random.uniform(-meander_amplitude, meander_amplitude)
                
                if random.random() < meander_frequency:
                    angle += random.uniform(-0.6, 0.6)
                
                step_size = random.uniform(0.8, 1.5)
                x += math.cos(angle) * step_size
                y += math.sin(angle) * step_size
                
                width = max(2.0, min(6.0, width + random.uniform(-0.3, 0.3)))
                
                steps += 1

    def generate_desert(self):
        """Generuje pustynię która wolno się rozszerza"""
        # Większe marginesy dla pustyni
        margin = 50
        cx = random.randint(margin, self.grid_width - margin)
        cy = random.randint(margin, self.grid_height - margin)
        
        initial_radius = random.randint(15, 25)
        
        for dy in range(-initial_radius, initial_radius + 1):
            for dx in range(-initial_radius, initial_radius + 1):
                if dx*dx + dy*dy <= initial_radius*initial_radius:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                        # Używamy draw_circle_safe który już chroni wodę i góry
                        if self.grid[ny][nx] == EMPTY:
                            self.grid[ny][nx] = DESERT

    def cut_forest_area(self, x, y, radius=3):
        """Wycina las (tworzy pas ochronny)"""
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                    if self.grid[ny][nx] in [TREE_YOUNG, TREE_MATURE, TREE_OLD]:
                        self.grid[ny][nx] = FIREBREAK
                        self.age_grid[ny][nx] = 0

    def plant_trees_area(self, x, y, radius=2):
        """Sadzi drzewa w małym kółku (promień 2)"""
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                # DODANE: Sprawdzenie czy jest w kółku
                if dx*dx + dy*dy <= radius*radius:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                        # Można sadzić na: pustej przestrzeni, popiele, pustyni
                        if self.grid[ny][nx] in [EMPTY, ASH, DESERT]:
                            self.grid[ny][nx] = TREE_MATURE
                            self.age_grid[ny][nx] = 50

    def initialize_forest(self, density=0.75):
        """Inicjalizacja lasu - POPRAWIONA KOLEJNOŚĆ"""
        self.grid.fill(EMPTY)
        self.age_grid.fill(0)
        self.fire_intensity.fill(0)
        self.water_width.fill(0)
        self.fire_started = False
        self.step_count = 0
        self.counts = {}
        self.has_desert = False

        # KROK 1: Co trzecia symulacja - dodaj pustynię NAJPIERW
        if random.random() < 0.33:
            self.generate_desert()
            self.has_desert = True

        # KROK 2: POTEM woda i rzeki (nie nachodzą na pustynię dzięki draw_circle_safe)
        self.generate_natural_blob(random.randint(3, 7), WATER, 8, 20, roughness=8)
        self.generate_rivers(random.randint(2, 4))
        
        # KROK 3: POTEM góry (nie nachodzą na wodę ani pustynię)
        r_mountains = random.random()
        if r_mountains < 0.1:
            num_mountains = 0
        elif r_mountains < 0.85:
            num_mountains = 1
        else:
            num_mountains = 2

        self.generate_natural_blob(num_mountains, ROCK, 15, 30, roughness=15)

        # KROK 4: NA KOŃCU drzewa (nie na wodzie, górach ani pustyni)
        random_mask = np.random.random((self.grid_height, self.grid_width)) < density
        occupied_mask = (self.grid != EMPTY)
        tree_mask = random_mask & (~occupied_mask)

        tree_types = np.random.choice(
            [TREE_YOUNG, TREE_MATURE, TREE_OLD],
            size=(self.grid_height, self.grid_width),
            p=[0.3, 0.5, 0.2]
        )

        self.grid[tree_mask] = tree_types[tree_mask]
        self.age_grid[tree_mask] = np.random.randint(0, 100, size=np.count_nonzero(tree_mask))

        self.update_stats()

    def get_neighbors(self, x, y):
        neighbors = []
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                wind_mod = 1.0
                if self.wind_strength > 0:
                    dot = dx * self.wind_direction[0] + dy * self.wind_direction[1]
                    if dot > 0:
                        wind_mod += self.wind_strength * 3.0 * dot
                    else:
                        wind_mod *= 0.2
                neighbors.append((nx, ny, wind_mod))
        return neighbors

    def update_stats(self):
        unique, counts = np.unique(self.grid, return_counts=True)
        self.counts = dict(zip(unique, counts))
        for k in COLORS.keys():
            if k not in self.counts:
                self.counts[k] = 0

    def update(self):
        if self.paused or not self.fire_started:
            return

        self.update_counter += self.simulation_speed

        if self.update_counter < 1.0:
            return

        steps_to_do = int(self.update_counter)
        self.update_counter -= steps_to_do

        for _ in range(steps_to_do):
            self._do_simulation_step()

    def is_near_water(self, x, y, max_distance=8):
        """Sprawdza czy komórka jest blisko wody"""
        for dy in range(-max_distance, max_distance + 1):
            for dx in range(-max_distance, max_distance + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                    if self.grid[ny][nx] == WATER:
                        dist = (dx*dx + dy*dy)**0.5
                        if dist <= max_distance:
                            return True
        return False

    def can_fire_cross_water(self, x, y, wind_factor):
        """Sprawdza czy ogień może przeskoczyć przez wodę przy silnym wietrze"""
        if self.grid[y][x] != WATER:
            return False
        
        water_w = self.water_width[y][x]
        
        if water_w < 3.5 and wind_factor > 3.0:
            jump_chance = (wind_factor - 3.0) * 0.4 * (3.5 - water_w) / 3.5
            if random.random() < jump_chance:
                return True
        
        return False

    def _do_simulation_step(self):
        """Pojedynczy krok symulacji"""
        self.step_count += 1
        new_grid = self.grid.copy()
        new_fire = self.fire_intensity.copy()

        rows, cols = self.grid.shape

        for y in range(rows):
            for x in range(cols):
                state = self.grid[y][x]

                if state == FIRE:
                    new_fire[y][x] -= self.fire_decay

                    if new_fire[y][x] <= 0:
                        new_grid[y][x] = ASH
                        new_fire[y][x] = 0
                    else:
                        for nx, ny, w_factor in self.get_neighbors(x, y):
                            n_state = self.grid[ny][nx]

                            if n_state in [ROCK, FIREBREAK, DESERT]:
                                continue

                            if n_state == WATER:
                                if not self.can_fire_cross_water(nx, ny, w_factor):
                                    continue

                            if n_state in [TREE_YOUNG, TREE_MATURE, TREE_OLD]:
                                base_prob = self.p_spread

                                if n_state == TREE_YOUNG:
                                    prob = base_prob * 0.5
                                elif n_state == TREE_MATURE:
                                    prob = base_prob * 1.0
                                else:
                                    prob = base_prob * 1.8

                                prob *= w_factor
                                prob = min(1.0, prob)

                                if random.random() < prob:
                                    new_grid[ny][nx] = FIRE
                                    new_fire[ny][nx] = 1.0

                elif state == ASH:
                    if random.random() < self.p_ash_decay:
                        new_grid[y][x] = EMPTY

                elif state == EMPTY:
                    if random.random() < self.p_grow:
                        has_desert_neighbor = False
                        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                                if self.grid[ny][nx] == DESERT:
                                    has_desert_neighbor = True
                                    break
                        
                        if not has_desert_neighbor:
                            new_grid[y][x] = TREE_YOUNG
                            self.age_grid[y][x] = 0

                elif state in [TREE_YOUNG, TREE_MATURE]:
                    self.age_grid[y][x] += 1
                    age = self.age_grid[y][x]
                    if state == TREE_YOUNG and age > 80:
                        new_grid[y][x] = TREE_MATURE
                    elif state == TREE_MATURE and age > 250:
                        new_grid[y][x] = TREE_OLD

                elif state == DESERT:
                    if random.random() < P_DESERT_SPREAD:
                        dx, dy = random.choice([(-1,0), (1,0), (0,-1), (0,1)])
                        nx, ny = x + dx, y + dy
                        
                        if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                            neighbor_state = self.grid[ny][nx]
                            
                            if neighbor_state in [TREE_YOUNG, TREE_MATURE, TREE_OLD, EMPTY, ASH]:
                                if not self.is_near_water(nx, ny, max_distance=8):
                                    new_grid[ny][nx] = DESERT

        self.grid = new_grid
        self.fire_intensity = new_fire
        self.update_stats()

    def start_fire(self, x, y, r=2):
        self.fire_started = True
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                    if self.grid[ny][nx] in [TREE_YOUNG, TREE_MATURE, TREE_OLD]:
                        self.grid[ny][nx] = FIRE
                        self.fire_intensity[ny][nx] = 1.0

    def draw(self, surface):
        """Rysowanie mapy z ulepszoną grafiką"""
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                state = self.grid[y][x]
                
                if state == WATER:
                    color = get_water_color(x, y, self.step_count)
                elif state == ROCK:
                    color = get_rock_color(x, y)
                elif state == DESERT:
                    color = get_desert_color(x, y)
                elif state in [TREE_YOUNG, TREE_MATURE, TREE_OLD]:
                    color = get_tree_color(state, self.age_grid[y][x])
                elif state == FIRE:
                    intensity = self.fire_intensity[y][x]
                    g = int(255 * intensity)
                    color = (255, max(0, min(255, g)), 0)
                else:
                    color = COLORS.get(state, (0, 0, 0))

                pygame.draw.rect(surface, color,
                                 (x * self.cell_size, y * self.cell_size,
                                  self.cell_size, self.cell_size))

        if self.wind_mode:
            cx, cy = (self.grid_width * self.cell_size) // 2, (self.grid_height * self.cell_size) // 2
            pygame.draw.circle(surface, (50, 50, 200), (cx, cy), 40, 2)
            wx, wy = self.wind_direction
            end_x = cx + wx * 60
            end_y = cy + wy * 60
            pygame.draw.line(surface, (255, 255, 0), (cx, cy), (end_x, end_y), 3)

        if self.cutting_mode:
            text_surf = font.render("WYCINANIE", True, (255, 200, 0))
            surface.blit(text_surf, (10, 10))

        if self.paused:
            pause_surf = font.render("PAUZA", True, (255, 255, 0))
            pause_rect = pause_surf.get_rect(center=(self.grid_width * self.cell_size // 2, 30))
            bg_rect = pause_rect.inflate(20, 10)
            pygame.draw.rect(surface, (0, 0, 0), bg_rect)
            pygame.draw.rect(surface, (255, 255, 0), bg_rect, 2)
            surface.blit(pause_surf, pause_rect)

        if self.simulation_speed != 1.0:
            if self.simulation_speed < 1.0:
                speed_text = f"{self.simulation_speed:.1f}x"
                speed_color = (100, 150, 255)
            else:
                speed_text = f"{self.simulation_speed:.1f}x"
                speed_color = (255, 100, 100)

            speed_surf = small_font.render(speed_text, True, speed_color)
            speed_rect = speed_surf.get_rect(topleft=(10, 50))
            bg_rect = speed_rect.inflate(10, 5)
            pygame.draw.rect(surface, (0, 0, 0), bg_rect)
            pygame.draw.rect(surface, speed_color, bg_rect, 2)
            surface.blit(speed_surf, speed_rect)

    def draw_ui(self, surface):
        """Odświeżony interfejs z większymi napisami"""
        ui_x = self.grid_width * self.cell_size + 10
        y = 15
        total_cells = self.grid_width * self.grid_height

        # === SEKCJA POGODY ===
        weather_info = WEATHER_PRESETS[self.current_weather]
        
        weather_box = pygame.Rect(ui_x - 5, y - 5, self.ui_width - 20, 70)
        pygame.draw.rect(surface, (25, 25, 25), weather_box)
        pygame.draw.rect(surface, weather_info['color'], weather_box, 3)

        weather_text = small_font.render(f"{weather_info['name']}", True, weather_info['color'])
        surface.blit(weather_text, (ui_x + 3, y))
        y += 28

        mult_text = tiny_font.render(f"Spalanie: {self.burn_rate_multiplier}x", True, (220, 220, 220))
        surface.blit(mult_text, (ui_x + 3, y))
        y += 24

        spread_text = tiny_font.render(f"Rozprz.: {self.p_spread:.2f}", True, (180, 180, 180))
        surface.blit(spread_text, (ui_x + 3, y))
        y += 28

        # === LEGENDA ===
        pygame.draw.line(surface, (60, 60, 60), (ui_x, y), (ui_x + self.ui_width - 20, y), 1)
        y += 8
        
        legend_title = small_font.render("LEGENDA", True, (255, 255, 255))
        surface.blit(legend_title, (ui_x, y))
        y += 26

        legend_items = [
            ("Mlode", TREE_YOUNG),
            ("Dojrzale", TREE_MATURE),
            ("Stare", TREE_OLD),
            ("Gory", ROCK),
            ("Woda", WATER),
            ("Pustynia", DESERT),
            ("Ogien", FIRE),
            ("Popiol", ASH),
        ]

        for name, state_id in legend_items:
            count = self.counts.get(state_id, 0)
            pct = (count / total_cells) * 100

            pygame.draw.rect(surface, COLORS[state_id], (ui_x, y, 16, 16))
            pygame.draw.rect(surface, (80, 80, 80), (ui_x, y, 16, 16), 1)

            text = tiny_font.render(f"{name}: {pct:.1f}%", True, (200, 200, 200))
            surface.blit(text, (ui_x + 20, y + 1))
            y += 21

        y += 6
        pygame.draw.line(surface, (60, 60, 60), (ui_x, y), (ui_x + self.ui_width - 20, y), 1)
        y += 8

        # === PARAMETRY ===
        params_title = small_font.render("PARAMETRY", True, (255, 255, 255))
        surface.blit(params_title, (ui_x, y))
        y += 26

        wind_strength_text = f"Wiatr: {self.wind_strength:.1f}"
        if self.wind_strength > 3.0:
            wind_color = (255, 50, 50)
            wind_strength_text += " EKSTR!"
        elif self.wind_strength > 2.5:
            wind_color = (255, 100, 50)
            wind_strength_text += " Silny"
        elif self.wind_strength > 2.0:
            wind_color = (255, 150, 50)
        elif self.wind_strength > 1.5:
            wind_color = (255, 200, 100)
        else:
            wind_color = (180, 180, 180)

        params = [
            f"Mapa: {self.grid_width}x{self.grid_height}",
            f"Zoom: {self.cell_size}px",
            (wind_strength_text, wind_color),
            f"Krok: {self.step_count}",
            f"Predkosc: {self.simulation_speed:.1f}x",
        ]

        for param in params:
            if isinstance(param, tuple):
                t = tiny_font.render(param[0], True, param[1])
            else:
                t = tiny_font.render(param, True, (180, 180, 180))
            surface.blit(t, (ui_x, y))
            y += 20

        if self.has_desert:
            desert_warning = tiny_font.render("! PUSTYNIA AKTYWNA !", True, (255, 200, 50))
            surface.blit(desert_warning, (ui_x, y))
            y += 20

        y += 6
        pygame.draw.line(surface, (60, 60, 60), (ui_x, y), (ui_x + self.ui_width - 20, y), 1)
        y += 8

        # === STEROWANIE ===
        controls_title = small_font.render("STEROWANIE", True, (255, 200, 50))
        surface.blit(controls_title, (ui_x, y))
        y += 26

        controls = [
            "POGODA: 1-6",
            "",
            "CZAS:",
            "  SPACJA - Pauza",
            "  [ - Wolniej",
            "  ] - Szybciej",
            "",
            "PODSTAWY:",
            "  LPM - Podpal",
            "  PPM - Sadz 3x3",
            "  C - Wytnij",
            "  W - Wiatr",
            "  +/- Sila wiatru",
            "  SCROLL - Reset",
        ]

        for c in controls:
            if c.startswith("POGODA") or c.startswith("CZAS") or c.startswith("PODSTAWY"):
                t = tiny_font.render(c, True, (255, 220, 100))
            else:
                t = tiny_font.render(c, True, (170, 170, 170))
            surface.blit(t, (ui_x, y))
            y += 17

    def set_wind_from_mouse(self, mx, my):
        cx, cy = (self.grid_width * self.cell_size) / 2, (self.grid_height * self.cell_size) / 2
        dx, dy = mx - cx, my - cy
        length = (dx * dx + dy * dy) ** 0.5
        if length > 0:
            self.wind_direction = [dx / length, dy / length]


# --- START ---
sim = ForestFireSimulation(START_GRID_WIDTH, START_GRID_HEIGHT, START_CELL_SIZE)
running = True
mouse_btn = [False, False, False]

while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                sim.paused = not sim.paused

            elif event.key == pygame.K_LEFTBRACKET:
                sim.simulation_speed = max(0.1, sim.simulation_speed * 0.5)
            elif event.key == pygame.K_RIGHTBRACKET:
                sim.simulation_speed = min(10.0, sim.simulation_speed * 2.0)
            elif event.key == pygame.K_0:
                sim.simulation_speed = 1.0

            elif event.key == pygame.K_1:
                sim.set_weather_preset('very_wet')
            elif event.key == pygame.K_2:
                sim.set_weather_preset('wet')
            elif event.key == pygame.K_3:
                sim.set_weather_preset('normal')
            elif event.key == pygame.K_4:
                sim.set_weather_preset('dry')
            elif event.key == pygame.K_5:
                sim.set_weather_preset('very_dry')
            elif event.key == pygame.K_6:
                sim.set_weather_preset('extreme')

            elif event.key == pygame.K_c:
                sim.cutting_mode = not sim.cutting_mode
                if sim.cutting_mode:
                    sim.wind_mode = False
            elif event.key == pygame.K_w:
                sim.wind_mode = not sim.wind_mode
                if sim.wind_mode:
                    sim.cutting_mode = False
            elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                sim.wind_strength = min(5.0, sim.wind_strength + 0.2)
            elif event.key == pygame.K_MINUS:
                sim.wind_strength = max(0.0, sim.wind_strength - 0.2)

            elif event.key == pygame.K_RIGHT:
                sim.change_grid_size(20, 0)
            elif event.key == pygame.K_LEFT:
                sim.change_grid_size(-20, 0)
            elif event.key == pygame.K_DOWN:
                sim.change_grid_size(0, 20)
            elif event.key == pygame.K_UP:
                sim.change_grid_size(0, -20)

            elif event.key == pygame.K_PAGEUP:
                sim.change_cell_size(1)
            elif event.key == pygame.K_PAGEDOWN:
                sim.change_cell_size(-1)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_btn[0] = True
            elif event.button == 3:
                mouse_btn[2] = True
            elif event.button == 4 or event.button == 5:
                sim.initialize_forest()
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                mouse_btn[0] = False
            elif event.button == 3:
                mouse_btn[2] = False

    mx, my = pygame.mouse.get_pos()

    if sim.wind_mode:
        sim.set_wind_from_mouse(mx, my)
        if mouse_btn[0]:
            sim.wind_mode = False
    elif sim.cutting_mode:
        gx, gy = mx // sim.cell_size, my // sim.cell_size
        if 0 <= gx < sim.grid_width and 0 <= gy < sim.grid_height:
            if mouse_btn[0]:
                sim.cut_forest_area(gx, gy, radius=3)
    else:
        gx, gy = mx // sim.cell_size, my // sim.cell_size
        if 0 <= gx < sim.grid_width and 0 <= gy < sim.grid_height:
            if mouse_btn[0]:
                sim.start_fire(gx, gy, 2)
            elif mouse_btn[2]:
                # ZMIENIONE: Sadzenie drzew w obszarze 9x9 (radius=4)
                sim.plant_trees_area(gx, gy, radius=2)

    sim.update()

    sim.screen.fill((20, 20, 20))
    sim.draw(sim.screen)
    sim.draw_ui(sim.screen)

    pygame.display.flip()

pygame.quit()