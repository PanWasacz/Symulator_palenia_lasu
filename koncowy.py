import pygame
import random
import numpy as np

# --- KONFIGURACJA ---
CELL_SIZE = 4
GRID_WIDTH = 300
GRID_HEIGHT = 200
WIDTH = GRID_WIDTH * CELL_SIZE + 250  # Dodatkowe miejsce na UI
HEIGHT = GRID_HEIGHT * CELL_SIZE
FPS = 60

# Prawdopodobieństwa
P_GROW = 0.005
P_LIGHTNING = 0.0
P_SPREAD = 0.2

# Stany komórek
EMPTY = 0
TREE_YOUNG = 1
TREE_MATURE = 2
TREE_OLD = 3
FIRE = 4
BURNING = 5
ASH = 6
WATER = 7

# Kolory
COLORS = {
    EMPTY: (20, 20, 20),
    TREE_YOUNG: (100, 255, 100),
    TREE_MATURE: (34, 139, 34),
    TREE_OLD: (0, 80, 0),
    FIRE: (255, 100, 0),
    BURNING: (255, 180, 50),
    ASH: (80, 80, 80),
    WATER: (30, 100, 200)
}

# --- INICJALIZACJA ---
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Symulacja Pozaru Lasu")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 24)
small_font = pygame.font.Font(None, 18)

# --- KLASA SYMULACJI ---
class ForestFireSimulation:
    def __init__(self):
        self.grid = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.int8)
        self.age_grid = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.int16)
        self.fire_intensity = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32)
        self.wind_direction = [1, 0]  # Domyślnie wiatr w prawo
        self.wind_strength = 0.5
        self.step_count = 0
        self.fire_started = False
        self.wind_mode = False  # Tryb ustawiania wiatru
        
        # Statystyki
        self.stats = {
            'trees': 0,
            'fire': 0,
            'burned': 0,
            'total_burned': 0,
            'young': 0,
            'mature': 0,
            'old': 0
        }
        
        self.initialize_forest()
        
    def generate_lakes(self, num_lakes=5):
        """Generuje losowe jeziora na mapie"""
        for _ in range(num_lakes):
            center_x = random.randint(20, GRID_WIDTH - 20)
            center_y = random.randint(20, GRID_HEIGHT - 20)
            radius = random.randint(5, 15)
            
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    dist = (dx*dx + dy*dy)**0.5
                    if dist <= radius + random.randint(-3, 3):
                        nx = center_x + dx
                        ny = center_y + dy
                        
                        if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                            self.grid[ny][nx] = WATER
        
    def initialize_forest(self, density=0.7):
        """Inicjalizacja lasu z różnymi typami drzew i jeziorami"""
        self.grid.fill(EMPTY)
        self.age_grid.fill(0)
        self.fire_intensity.fill(0)
        self.fire_started = False
        self.step_count = 0
        self.stats['total_burned'] = 0
        
        self.generate_lakes(num_lakes=random.randint(3, 8))
        
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.grid[y][x] != WATER:
                    if random.random() < density:
                        tree_type = random.choices(
                            [TREE_YOUNG, TREE_MATURE, TREE_OLD],
                            weights=[0.4, 0.4, 0.2]
                        )[0]
                        self.grid[y][x] = tree_type
                        self.age_grid[y][x] = random.randint(0, 50)
    
    def set_wind_from_mouse(self, mouse_x, mouse_y):
        """Ustaw kierunek wiatru na podstawie pozycji myszy"""
        # Środek planszy
        center_x = (GRID_WIDTH * CELL_SIZE) / 2
        center_y = (GRID_HEIGHT * CELL_SIZE) / 2
        
        # Wektor od środka do myszy
        dx = mouse_x - center_x
        dy = mouse_y - center_y
        
        # Normalizacja
        length = (dx*dx + dy*dy)**0.5
        if length > 10:  # Minimalna odległość od środka
            self.wind_direction = [dx / length, dy / length]
    
    def get_neighbors(self, x, y, include_diagonals=True):
        """Zwraca sąsiadów komórki z uwzględnieniem wiatru"""
        neighbors = []
        
        if include_diagonals:
            directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
        else:
            directions = [(-1,0), (1,0), (0,-1), (0,1)]
        
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                wind_factor = 1.0
                if self.wind_strength > 0:
                    # Iloczyn skalarny - jak bardzo kierunek jest zgodny z wiatrem
                    dot_product = (dx * self.wind_direction[0] + dy * self.wind_direction[1])
                    if dot_product > 0:
                        # Zwiększ szansę w kierunku wiatru
                        wind_factor = 1.0 + self.wind_strength * 2.0 * dot_product
                    else:
                        # Zmniejsz szansę przeciwko wiatrowi
                        wind_factor = 1.0 + self.wind_strength * 0.5 * dot_product
                
                neighbors.append((nx, ny, wind_factor))
        
        return neighbors
    
    def update(self):
        """Główna logika aktualizacji"""
        if not self.fire_started:
            return
        
        self._update_step()
    
    def _update_step(self):
        """Pojedynczy krok symulacji"""
        new_grid = self.grid.copy()
        new_fire_intensity = self.fire_intensity.copy()
        self.step_count += 1
        
        total_burned = self.stats['total_burned']
        self.stats = {
            'trees': 0,
            'fire': 0,
            'burned': 0,
            'total_burned': total_burned,
            'young': 0,
            'mature': 0,
            'old': 0
        }
        
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                state = self.grid[y][x]
                
                if state == WATER:
                    continue
                
                elif state == FIRE or state == BURNING:
                    self.stats['fire'] += 1
                    self.fire_intensity[y][x] -= 0.15
                    
                    if self.fire_intensity[y][x] <= 0:
                        new_grid[y][x] = ASH
                        new_fire_intensity[y][x] = 0
                        self.stats['total_burned'] += 1
                    else:
                        for nx, ny, wind_factor in self.get_neighbors(x, y):
                            neighbor_state = self.grid[ny][nx]
                            
                            if neighbor_state == WATER:
                                continue
                            
                            if neighbor_state in [TREE_YOUNG, TREE_MATURE, TREE_OLD]:
                                if neighbor_state == TREE_YOUNG:
                                    spread_prob = P_SPREAD * 0.3 * wind_factor
                                elif neighbor_state == TREE_MATURE:
                                    spread_prob = P_SPREAD * wind_factor
                                elif neighbor_state == TREE_OLD:
                                    spread_prob = P_SPREAD * 2.0 * wind_factor
                                
                                spread_prob = min(1.0, spread_prob)
                                
                                if random.random() < spread_prob:
                                    new_grid[ny][nx] = FIRE
                                    new_fire_intensity[ny][nx] = 1.0
                
                elif state in [TREE_YOUNG, TREE_MATURE, TREE_OLD]:
                    self.stats['trees'] += 1
                    
                    if state == TREE_YOUNG:
                        self.stats['young'] += 1
                    elif state == TREE_MATURE:
                        self.stats['mature'] += 1
                    elif state == TREE_OLD:
                        self.stats['old'] += 1
                    
                    self.age_grid[y][x] += 1
                    if state == TREE_YOUNG and self.age_grid[y][x] > 100:
                        new_grid[y][x] = TREE_MATURE
                    elif state == TREE_MATURE and self.age_grid[y][x] > 300:
                        new_grid[y][x] = TREE_OLD
                
                elif state == ASH:
                    self.stats['burned'] += 1
                    if random.random() < 0.01:
                        new_grid[y][x] = EMPTY
                
                elif state == EMPTY:
                    if random.random() < P_GROW:
                        new_grid[y][x] = TREE_YOUNG
                        self.age_grid[y][x] = 0
        
        self.grid = new_grid
        self.fire_intensity = new_fire_intensity
    
    def start_fire(self, x, y, radius=2):
        """Rozpocznij pożar w danym miejscu"""
        self.fire_started = True
        
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx*dx + dy*dy <= radius*radius:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                        if self.grid[ny][nx] in [TREE_YOUNG, TREE_MATURE, TREE_OLD]:
                            self.grid[ny][nx] = FIRE
                            self.fire_intensity[ny][nx] = 1.0
    
    def draw(self, surface):
        """Rysowanie siatki"""
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                state = self.grid[y][x]
                
                if state == FIRE or state == BURNING:
                    intensity = self.fire_intensity[y][x]
                    r = int(255 * intensity)
                    g = int(100 * intensity)
                    color = (r, g, 0)
                else:
                    color = COLORS.get(state, COLORS[EMPTY])
                
                pygame.draw.rect(
                    surface,
                    color,
                    (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                )
        
        # Rysuj wskaźnik wiatru na środku mapy (jeśli w trybie wiatru)
        if self.wind_mode:
            center_x = (GRID_WIDTH * CELL_SIZE) / 2
            center_y = (GRID_HEIGHT * CELL_SIZE) / 2
            
            # Okrąg w środku
            pygame.draw.circle(surface, (100, 100, 255), (int(center_x), int(center_y)), 30, 3)
            
            # Strzałka kierunku wiatru
            arrow_len = 80
            end_x = center_x + self.wind_direction[0] * arrow_len
            end_y = center_y + self.wind_direction[1] * arrow_len
            
            pygame.draw.line(surface, (255, 255, 100), 
                           (center_x, center_y), (end_x, end_y), 4)
            
            # Grot strzałki
            angle = np.arctan2(self.wind_direction[1], self.wind_direction[0])
            arrow_size = 15
            pygame.draw.polygon(surface, (255, 255, 100), [
                (end_x, end_y),
                (end_x - arrow_size * np.cos(angle - 0.4), 
                 end_y - arrow_size * np.sin(angle - 0.4)),
                (end_x - arrow_size * np.cos(angle + 0.4), 
                 end_y - arrow_size * np.sin(angle + 0.4))
            ])
    
    def draw_ui(self, surface):
        """Rysowanie interfejsu użytkownika"""
        ui_x = GRID_WIDTH * CELL_SIZE + 10
        y_offset = 20
        
        # Tytuł
        title = font.render("STATYSTYKI", True, (255, 255, 255))
        surface.blit(title, (ui_x, y_offset))
        y_offset += 40
        
        # Informacja o rozpoczęciu pożaru
        if not self.fire_started:
            info = small_font.render("Kliknij LPM aby", True, (255, 255, 100))
            surface.blit(info, (ui_x, y_offset))
            y_offset += 20
            info2 = small_font.render("rozpoczac pozar!", True, (255, 255, 100))
            surface.blit(info2, (ui_x, y_offset))
            y_offset += 30
        
        # Tryb wiatru
        if self.wind_mode:
            wind_info = small_font.render("TRYB WIATRU", True, (255, 255, 100))
            surface.blit(wind_info, (ui_x, y_offset))
            y_offset += 20
            wind_info2 = small_font.render("Kliknij aby", True, (255, 255, 100))
            surface.blit(wind_info2, (ui_x, y_offset))
            y_offset += 20
            wind_info3 = small_font.render("ustawic kierunek", True, (255, 255, 100))
            surface.blit(wind_info3, (ui_x, y_offset))
            y_offset += 30
        
        # Legenda kolorów
        legend_y = y_offset
        pygame.draw.rect(surface, COLORS[TREE_YOUNG], (ui_x, legend_y, 15, 15))
        legend_text = small_font.render("- Mlode (6%)", True, (200, 200, 200))
        surface.blit(legend_text, (ui_x + 20, legend_y))
        legend_y += 20
        
        pygame.draw.rect(surface, COLORS[TREE_MATURE], (ui_x, legend_y, 15, 15))
        legend_text = small_font.render("- Dojrzale (20%)", True, (200, 200, 200))
        surface.blit(legend_text, (ui_x + 20, legend_y))
        legend_y += 20
        
        pygame.draw.rect(surface, COLORS[TREE_OLD], (ui_x, legend_y, 15, 15))
        legend_text = small_font.render("- Stare (40%)", True, (200, 200, 200))
        surface.blit(legend_text, (ui_x + 20, legend_y))
        legend_y += 20
        
        pygame.draw.rect(surface, COLORS[WATER], (ui_x, legend_y, 15, 15))
        legend_text = small_font.render("- Jezioro", True, (200, 200, 200))
        surface.blit(legend_text, (ui_x + 20, legend_y))
        legend_y += 20
        
        pygame.draw.rect(surface, COLORS[ASH], (ui_x, legend_y, 15, 15))
        legend_text = small_font.render("- Popiol", True, (200, 200, 200))
        surface.blit(legend_text, (ui_x + 20, legend_y))
        y_offset = legend_y + 30
        
        # Wiatr
        wind_angle = np.degrees(np.arctan2(self.wind_direction[1], self.wind_direction[0]))
        wind_dirs = {
            (0, 45): "E", (45, 90): "SE", (90, 135): "S", (135, 180): "SW",
            (-180, -135): "SW", (-135, -90): "W", (-90, -45): "NW", (-45, 0): "N"
        }
        wind_dir_text = "E"
        for (low, high), direction in wind_dirs.items():
            if low <= wind_angle < high:
                wind_dir_text = direction
                break
        
        wind_text = small_font.render(f"Wiatr: {wind_dir_text}", True, (200, 200, 200))
        surface.blit(wind_text, (ui_x, y_offset))
        y_offset += 20
        
        strength_text = small_font.render(f"Sila: {self.wind_strength:.1f}", True, (200, 200, 200))
        surface.blit(strength_text, (ui_x, y_offset))
        y_offset += 30
        
        # Statystyki
        stats_text = [
            f"Krok: {self.step_count}",
            "",
            f"Mlode: {self.stats['young']}",
            f"Dojrzale: {self.stats['mature']}",
            f"Stare: {self.stats['old']}",
            f"Razem: {self.stats['trees']}",
            "",
            f"Ogien: {self.stats['fire']}",
            f"Popiol: {self.stats['burned']}",
            f"Spalone: {self.stats['total_burned']}",
            "",
            "STEROWANIE:",
            "",
            "LPM - Pozar",
            "PPM - Drzewa",
            "Scroll - Nowa mapa",
            "W - Tryb wiatru",
            "+/- Sila wiatru",
        ]
        
        for text in stats_text:
            rendered = small_font.render(text, True, (200, 200, 200))
            surface.blit(rendered, (ui_x, y_offset))
            y_offset += 20
        
        # Status
        if not self.fire_started:
            status = "OCZEKIWANIE"
            status_color = (255, 255, 100)
        else:
            status = "DZIALA"
            status_color = (100, 255, 100)
            
        status_text = font.render(status, True, status_color)
        surface.blit(status_text, (ui_x, HEIGHT - 40))

# --- GŁÓWNA PĘTLA ---
sim = ForestFireSimulation()
running = True
mouse_down = False
right_mouse_down = False

while running:
    clock.tick(FPS)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                sim.wind_mode = not sim.wind_mode
            elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                sim.wind_strength = min(2.0, sim.wind_strength + 0.1)
            elif event.key == pygame.K_MINUS:
                sim.wind_strength = max(0.0, sim.wind_strength - 0.1)
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # LPM
                mouse_down = True
            elif event.button == 3:  # PPM
                right_mouse_down = True
            elif event.button == 4 or event.button == 5:  # Scroll
                sim.initialize_forest()
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                mouse_down = False
            elif event.button == 3:
                right_mouse_down = False
    
    # Obsługa myszy
    mx, my = pygame.mouse.get_pos()
    
    if sim.wind_mode:
        # W trybie wiatru - ustaw kierunek
        sim.set_wind_from_mouse(mx, my)
        if mouse_down:
            sim.wind_mode = False  # Kliknięcie potwierdza i wychodzi z trybu
    else:
        # Normalny tryb
        if mouse_down or right_mouse_down:
            x = mx // CELL_SIZE
            y = my // CELL_SIZE
            
            if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT:
                if mouse_down:
                    sim.start_fire(x, y, radius=2)
                elif right_mouse_down:
                    for dy in range(-2, 3):
                        for dx in range(-2, 3):
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                                if sim.grid[ny][nx] != WATER:
                                    sim.grid[ny][nx] = TREE_MATURE
                                    sim.age_grid[ny][nx] = 50
    
    # Aktualizacja symulacji
    sim.update()
    
    # Rysowanie
    screen.fill((20, 20, 20))
    sim.draw(screen)
    sim.draw_ui(screen)
    
    pygame.display.flip()

pygame.quit()