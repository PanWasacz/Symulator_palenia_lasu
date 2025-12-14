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

# Prawdopodobieństwa - ZMNIEJSZONE
P_GROW = 0.005
P_LIGHTNING = 0.0
P_SPREAD = 0.2  # ZMNIEJSZONE z 0.5 na 0.2

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
    EMPTY: (20, 20, 20),           # Prawie czarny
    TREE_YOUNG: (100, 255, 100),   # JASNA ZIELEŃ - młode drzewa
    TREE_MATURE: (34, 139, 34),    # ŚREDNIA ZIELEŃ - dojrzałe drzewa
    TREE_OLD: (0, 80, 0),          # CIEMNA ZIELEŃ - stare drzewa
    FIRE: (255, 100, 0),           # Pomarańczowy ogień
    BURNING: (255, 180, 50),       # Jasny płomień
    ASH: (80, 80, 80),             # Szary popiół
    WATER: (30, 100, 200)          # Niebieska woda
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
        self.wind_direction = [0, 0]
        self.wind_strength = 0.3
        self.step_count = 0
        self.fire_started = False
        
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
            # Losowa pozycja jeziora
            center_x = random.randint(20, GRID_WIDTH - 20)
            center_y = random.randint(20, GRID_HEIGHT - 20)
            
            # Losowy rozmiar jeziora
            radius = random.randint(5, 15)
            
            # Losowy kształt (bardziej organiczny)
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    # Dodaj trochę losowości do kształtu
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
        
        # Najpierw generuj jeziora
        self.generate_lakes(num_lakes=random.randint(3, 8))
        
        # Potem dodaj drzewa (ale nie na wodzie)
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.grid[y][x] != WATER:  # Nie nadpisuj wody
                    if random.random() < density:
                        tree_type = random.choices(
                            [TREE_YOUNG, TREE_MATURE, TREE_OLD],
                            weights=[0.4, 0.4, 0.2]
                        )[0]
                        self.grid[y][x] = tree_type
                        self.age_grid[y][x] = random.randint(0, 50)
    
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
                    dot_product = (dx * self.wind_direction[0] + dy * self.wind_direction[1])
                    if dot_product > 0:
                        wind_factor = 1.0 + self.wind_strength * dot_product
                
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
        
        # Reset statystyk
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
                
                # Woda - nic się nie dzieje
                if state == WATER:
                    continue
                
                # Ogień
                elif state == FIRE or state == BURNING:
                    self.stats['fire'] += 1
                    self.fire_intensity[y][x] -= 0.15  # Wolniejsze spalanie
                    
                    if self.fire_intensity[y][x] <= 0:
                        new_grid[y][x] = ASH
                        new_fire_intensity[y][x] = 0
                        self.stats['total_burned'] += 1
                    else:
                        # Rozprzestrzenianie ognia
                        for nx, ny, wind_factor in self.get_neighbors(x, y):
                            neighbor_state = self.grid[ny][nx]
                            
                            # Ogień NIE rozprzestrzenia się na wodę
                            if neighbor_state == WATER:
                                continue
                            
                            if neighbor_state in [TREE_YOUNG, TREE_MATURE, TREE_OLD]:
                                # ZMNIEJSZONE wartości dla wolniejszego rozprzestrzeniania
                                if neighbor_state == TREE_YOUNG:
                                    # Młode drzewa - bardzo trudno się zapalają (6%)
                                    spread_prob = P_SPREAD * 0.3 * wind_factor
                                elif neighbor_state == TREE_MATURE:
                                    # Dojrzałe drzewa - normalna palność (20%)
                                    spread_prob = P_SPREAD * wind_factor
                                elif neighbor_state == TREE_OLD:
                                    # Stare drzewa - łatwo się zapalają (40%)
                                    spread_prob = P_SPREAD * 2.0 * wind_factor
                                
                                # Upewnij się że prawdopodobieństwo nie przekracza 1.0
                                spread_prob = min(1.0, spread_prob)
                                
                                if random.random() < spread_prob:
                                    new_grid[ny][nx] = FIRE
                                    new_fire_intensity[ny][nx] = 1.0
                
                # Drzewa
                elif state in [TREE_YOUNG, TREE_MATURE, TREE_OLD]:
                    self.stats['trees'] += 1
                    
                    # Zliczanie typów drzew
                    if state == TREE_YOUNG:
                        self.stats['young'] += 1
                    elif state == TREE_MATURE:
                        self.stats['mature'] += 1
                    elif state == TREE_OLD:
                        self.stats['old'] += 1
                    
                    # Starzenie się drzew
                    self.age_grid[y][x] += 1
                    if state == TREE_YOUNG and self.age_grid[y][x] > 100:
                        new_grid[y][x] = TREE_MATURE
                    elif state == TREE_MATURE and self.age_grid[y][x] > 300:
                        new_grid[y][x] = TREE_OLD
                
                # Popiół
                elif state == ASH:
                    self.stats['burned'] += 1
                    if random.random() < 0.01:
                        new_grid[y][x] = EMPTY
                
                # Pusta przestrzeń
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
                        # Nie podpalaj wody!
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
        
        # Legenda kolorów z szansami zapłonu
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
        ]
        
        for text in stats_text:
            rendered = small_font.render(text, True, (200, 200, 200))
            surface.blit(rendered, (ui_x, y_offset))
            y_offset += 22
        
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
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # LPM
                mouse_down = True
            elif event.button == 3:  # PPM
                right_mouse_down = True
            elif event.button == 4 or event.button == 5:  # Scroll - nowa mapa
                sim.initialize_forest()
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                mouse_down = False
            elif event.button == 3:
                right_mouse_down = False
    
    # Obsługa myszy
    if mouse_down or right_mouse_down:
        mx, my = pygame.mouse.get_pos()
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
                            # Nie nadpisuj wody
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