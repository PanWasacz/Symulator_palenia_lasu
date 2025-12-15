import pygame
import random
import numpy as np
import math

# --- KONFIGURACJA STARTOWA ---
START_CELL_SIZE = 4
START_GRID_WIDTH = 300
START_GRID_HEIGHT = 200
FPS = 60

# Prawdopodobieństwa
P_SPREAD = 0.25
P_GROW = 0.0005
P_ASH_DECAY = 0.005
FIRE_DECAY = 0.15

# Stany komórek
EMPTY = 0
TREE_YOUNG = 1
TREE_MATURE = 2
TREE_OLD = 3
FIRE = 4
ASH = 6
WATER = 7
ROCK = 8  # Nowy stan: Góra/Skała

# Kolory
COLORS = {
    EMPTY: (15, 15, 15),
    TREE_YOUNG: (100, 255, 100),
    TREE_MATURE: (34, 139, 34),
    TREE_OLD: (0, 80, 0),
    FIRE: (255, 69, 0),
    ASH: (169, 169, 169),  # Jasny szary (popiół)
    WATER: (30, 100, 200),
    ROCK: (90, 90, 90)  # Ciemny szary (skała)
}

# --- INICJALIZACJA PYGAME ---
pygame.init()
pygame.display.set_caption("Symulacja Pożaru Lasu v5.0 - Góry i Rzeki")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 26)
small_font = pygame.font.Font(None, 20)


# --- KLASA SYMULACJI ---
class ForestFireSimulation:
    def __init__(self, width, height, cell_size):
        self.grid_width = width
        self.grid_height = height
        self.cell_size = cell_size
        self.ui_width = 350

        self.update_window_size()

        self.wind_direction = [1, 0]
        self.wind_strength = 1.0
        self.wind_mode = False

        self.p_grow = P_GROW
        self.p_ash_decay = P_ASH_DECAY

        self.initialize_arrays()
        self.initialize_forest()

    def update_window_size(self):
        self.window_width = self.grid_width * self.cell_size + self.ui_width
        self.window_height = self.grid_height * self.cell_size
        if self.window_height < 600:
            self.window_height = 600
        self.screen = pygame.display.set_mode((self.window_width, self.window_height))

    def initialize_arrays(self):
        self.grid = np.zeros((self.grid_height, self.grid_width), dtype=np.int8)
        self.age_grid = np.zeros((self.grid_height, self.grid_width), dtype=np.int16)
        self.fire_intensity = np.zeros((self.grid_height, self.grid_width), dtype=np.float32)

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

    # --- SYSTEM TERENU (GÓRY I WODA) ---

    def draw_circle_safe(self, cx, cy, radius, state):
        """Bezpieczne rysowanie koła na siatce"""
        min_y = max(0, int(cy - radius))
        max_y = min(self.grid_height, int(cy + radius + 1))
        min_x = max(0, int(cx - radius))
        max_x = min(self.grid_width, int(cx + radius + 1))

        for y in range(min_y, max_y):
            for x in range(min_x, max_x):
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2:
                    # Nie nadpisuj wody skałami i odwrotnie (pierwszeństwo ma to co już jest)
                    if self.grid[y][x] == EMPTY:
                        self.grid[y][x] = state

    def generate_natural_blob(self, count, state, min_r, max_r, roughness=10):
        """Uniwersalna funkcja do generowania nieregularnych plam (Jeziora/Góry)"""
        for _ in range(count):
            cx = random.randint(20, self.grid_width - 20)
            cy = random.randint(20, self.grid_height - 20)

            base_radius = random.randint(min_r, max_r)
            self.draw_circle_safe(cx, cy, base_radius, state)

            # Dodajemy mniejsze koła na obwodzie, żeby postrzępić krawędź
            num_blobs = random.randint(roughness, roughness + 8)
            for _ in range(num_blobs):
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(base_radius * 0.4, base_radius * 1.1)

                ox = cx + math.cos(angle) * dist
                oy = cy + math.sin(angle) * dist

                blob_r = random.uniform(2, base_radius * 0.5)
                self.draw_circle_safe(ox, oy, blob_r, state)

    def generate_rivers(self, num_rivers=2):
        for _ in range(num_rivers):
            if random.random() < 0.5:  # Lewo -> Prawo
                x, y = 0, random.randint(0, self.grid_height - 1)
                dx, dy = 1, 0
            else:  # Góra -> Dół
                x, y = random.randint(0, self.grid_width - 1), 0
                dx, dy = 0, 1

            width = random.uniform(2, 4)

            while 0 <= x < self.grid_width and 0 <= y < self.grid_height:
                self.draw_circle_safe(x, y, width, WATER)
                x += dx
                y += dy

                meander = random.uniform(-0.6, 0.6)
                if dx != 0:
                    y += meander
                    width = max(1.5, min(5, width + random.uniform(-0.2, 0.2)))
                else:
                    x += meander
                    width = max(1.5, min(5, width + random.uniform(-0.2, 0.2)))

    # --- INICJALIZACJA LASU ---

    def initialize_forest(self, density=0.75):
        self.grid.fill(EMPTY)
        self.age_grid.fill(0)
        self.fire_intensity.fill(0)
        self.fire_started = False
        self.step_count = 0
        self.counts = {}

        # 1. Góry (Skały)
        # Losowanie liczby gór:
        # 0.1 (10%) -> 0 gór
        # 0.75 (75%) -> 1 góra
        # 0.15 (15%) -> 2 góry
        r_mountains = random.random()
        if r_mountains < 0.1:
            num_mountains = 0
        elif r_mountains < 0.85:
            num_mountains = 1
        else:
            num_mountains = 2

        self.generate_natural_blob(num_mountains, ROCK, 15, 30, roughness=15)

        # 2. Jeziora
        self.generate_natural_blob(random.randint(3, 7), WATER, 8, 20, roughness=8)

        # 3. Rzeki
        self.generate_rivers(random.randint(1, 3))

        # 4. Drzewa (tylko na EMPTY)
        random_mask = np.random.random((self.grid_height, self.grid_width)) < density
        occupied_mask = (self.grid != EMPTY)  # Woda lub Skały

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
                        wind_mod += self.wind_strength * 2.5 * dot
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
        if not self.fire_started:
            return

        self.step_count += 1
        new_grid = self.grid.copy()
        new_fire = self.fire_intensity.copy()

        rows, cols = self.grid.shape

        for y in range(rows):
            for x in range(cols):
                state = self.grid[y][x]

                if state == FIRE:
                    new_fire[y][x] -= FIRE_DECAY
                    if new_fire[y][x] <= 0:
                        new_grid[y][x] = ASH
                        new_fire[y][x] = 0
                    else:
                        for nx, ny, w_factor in self.get_neighbors(x, y):
                            n_state = self.grid[ny][nx]

                            # Woda i Skały blokują ogień
                            if n_state == WATER or n_state == ROCK:
                                continue

                            if n_state in [TREE_YOUNG, TREE_MATURE, TREE_OLD]:
                                base_prob = P_SPREAD
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
                        new_grid[y][x] = TREE_YOUNG
                        self.age_grid[y][x] = 0

                elif state in [TREE_YOUNG, TREE_MATURE]:
                    self.age_grid[y][x] += 1
                    age = self.age_grid[y][x]
                    if state == TREE_YOUNG and age > 80:
                        new_grid[y][x] = TREE_MATURE
                    elif state == TREE_MATURE and age > 250:
                        new_grid[y][x] = TREE_OLD

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
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                state = self.grid[y][x]
                color = COLORS.get(state, (0, 0, 0))

                if state == FIRE:
                    intensity = self.fire_intensity[y][x]
                    g = int(255 * intensity)
                    color = (255, max(0, min(255, g)), 0)

                pygame.draw.rect(surface, color,
                                 (x * self.cell_size, y * self.cell_size, self.cell_size, self.cell_size))

        if self.wind_mode:
            cx, cy = (self.grid_width * self.cell_size) // 2, (self.grid_height * self.cell_size) // 2
            pygame.draw.circle(surface, (50, 50, 200), (cx, cy), 40, 2)
            wx, wy = self.wind_direction
            end_x = cx + wx * 60
            end_y = cy + wy * 60
            pygame.draw.line(surface, (255, 255, 0), (cx, cy), (end_x, end_y), 3)

    def draw_ui(self, surface):
        ui_x = self.grid_width * self.cell_size + 20
        y = 20
        total_cells = self.grid_width * self.grid_height

        title = font.render("PANEL KONTROLNY", True, (255, 255, 255))
        surface.blit(title, (ui_x, y))
        y += 40

        legend_items = [
            ("Młode Drzewa", TREE_YOUNG),
            ("Dojrzałe", TREE_MATURE),
            ("Stare Drzewa", TREE_OLD),
            ("Skały/Góry", ROCK),  # Dodane do legendy
            ("Woda", WATER),
            ("Ogień", FIRE),
            ("Popiół", ASH),
            ("Puste/Gleba", EMPTY)
        ]

        for name, state_id in legend_items:
            count = self.counts.get(state_id, 0)
            pct = (count / total_cells) * 100

            pygame.draw.rect(surface, COLORS[state_id], (ui_x, y, 20, 20))
            pygame.draw.rect(surface, (100, 100, 100), (ui_x, y, 20, 20), 1)

            text_str = f"{name}: {pct:.2f}%"
            text = small_font.render(text_str, True, (200, 200, 200))
            surface.blit(text, (ui_x + 30, y + 3))
            y += 25

        y += 10
        pygame.draw.line(surface, (50, 50, 50), (ui_x, y), (self.window_width - 20, y), 2)
        y += 15

        dims = [
            f"Mapa: {self.grid_width}x{self.grid_height}",
            f"Zoom: {self.cell_size}px",
            f"Wiatr: {self.wind_strength:.1f}",
            "",
            "USTAWIENIA:",
            f"Wzrost: {self.p_grow:.4f}",
            f"Popiół: {self.p_ash_decay:.3f}",
        ]

        for line in dims:
            t = small_font.render(line, True, (180, 180, 180))
            surface.blit(t, (ui_x, y))
            y += 20

        y += 10
        controls = [
            "STRZAŁKI: Rozmiar mapy (Nowy teren)",
            "PgUp/PgDn: Zoom",
            "LPM: Podpal | PPM: Sadź",
            "SCROLL: Nowa mapa",
            "W: Zmień wiatr | +/-: Siła"
        ]
        for c in controls:
            t = small_font.render(c, True, (255, 255, 100))
            surface.blit(t, (ui_x, y))
            y += 20

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
            if event.key == pygame.K_w:
                sim.wind_mode = not sim.wind_mode
            elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                sim.wind_strength = min(3.0, sim.wind_strength + 0.1)
            elif event.key == pygame.K_MINUS:
                sim.wind_strength = max(0.0, sim.wind_strength - 0.1)

            elif event.key == pygame.K_r:
                sim.p_grow = min(0.01, sim.p_grow * 1.5)
            elif event.key == pygame.K_f:
                sim.p_grow = max(0.00001, sim.p_grow * 0.5)
            elif event.key == pygame.K_e:
                sim.p_ash_decay = min(0.1, sim.p_ash_decay * 1.5)
            elif event.key == pygame.K_d:
                sim.p_ash_decay = max(0.0001, sim.p_ash_decay * 0.5)

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
        if mouse_btn[0]: sim.wind_mode = False
    else:
        gx, gy = mx // sim.cell_size, my // sim.cell_size
        if 0 <= gx < sim.grid_width and 0 <= gy < sim.grid_height:
            if mouse_btn[0]:
                sim.start_fire(gx, gy, 2)
            elif mouse_btn[2]:
                if sim.grid[gy][gx] != WATER and sim.grid[gy][gx] != ROCK:
                    sim.grid[gy][gx] = TREE_MATURE

    sim.update()

    sim.screen.fill((30, 30, 30))
    sim.draw(sim.screen)
    sim.draw_ui(sim.screen)

    pygame.display.flip()

pygame.quit()