import pygame
import random
import math

WIDTH, HEIGHT = 1000, 800
CELL_COUNT = 30
FOOD_COUNT = 80
WALL_MARGIN = 40
FOOD_ENERGY = 25

BACKGROUND_COLOR = (15, 20, 25)
TEXT_COLOR = (255, 255, 255)
FOOD_COLOR = (255, 220, 50)
CELL_MEMBRANE_COLOR = (30, 80, 100)
CELL_NUCLEAR_REFLECTION_COLOR = (220, 255, 255)

CELL_MAX_ENERGY = 150.0
CELL_ENERGY_PER_FRAME = 0.055
CELL_PREDATION_ENERGY_THRESHOLD = 45.0

CELL_REPRODUCE_ENERGY_THRESHOLD = 110.0
CELL_REPRODUCE_AGE_THRESHOLD = 150
CELL_REPRODUCE_RADIUS_THRESHOLD = 10.0

REPRODUCTION_ENERGY_COST = 0.22
REPRODUCTION_COOLDOWN = 420

FOOD_RESPAWN_CHANCE = 0.035
MIN_FOOD_COUNT = 60

MIN_SPEED = 0.3
MAX_SPEED = 4.0

COLLISION_ITERATIONS = 3
COLLISION_RESTITUTION = 0.15

STUCK_CHECK_INTERVAL = 30
STUCK_DISTANCE_THRESHOLD = 3.0

FPS = 60

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Single Cell Ecosystem")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)

def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))

def distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)

def normalize(x, y):
    length = math.hypot(x, y)

    if length <= 0.000001:
        return 0.0, 0.0
    
    return x / length, y / length

def random_direction():
    angle = random.uniform(0, math.tau)
    return math.cos(angle), math.sin(angle)

class Food:
    def __init__(self, cells = None):
        self.energy = FOOD_ENERGY

        while True:
            self.x = random.uniform(WALL_MARGIN, WIDTH - WALL_MARGIN)
            self.y = random.uniform(WALL_MARGIN, HEIGHT - WALL_MARGIN)

            if not cells:
                break

            valid_position = True

            for cell in cells:
                if distance(self.x, self.y, cell.x, cell.y) < cell.radius + 10:
                    valid_position = False
                    break

            if valid_position:
                break

    def draw(self, surface):
        pygame.draw.circle(surface, FOOD_COLOR, (int(self.x), int(self.y)), 3)

class Cell:
    def __init__(self, x, y, energy):
        self.x = float(x)
        self.y = float(y)

        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-0.5, 0.5)

        self.energy = clamp(float(energy), 0.0, CELL_MAX_ENERGY)
        self.age = 0

        self.radius = random.uniform(7.0, 9.0)
        self.max_radius = random.uniform(13.0, 15.0)

        self.base_speed = random.uniform(1.5, 2.8)
        self.speed = self.base_speed
        self.vision = random.uniform(90, 160)

        self.reproduction_rate = random.uniform(0.0012, 0.0025)
        self.max_age = random.randint(1400, 2200)
        self.reproduction_cooldown = random.randint(0, 180)

        self.alive = True

        self.wander_dx, self.wander_dy = random_direction()
        self.wander_timer = random.randint(30, 100)

        self.stuck_timer = 0
        self.last_check_x = self.x
        self.last_check_y = self.y
        self.escape_timer = 0

    def is_full(self):
        return self.energy >= CELL_MAX_ENERGY - 0.01

    def find_target(self, foods, cells):
        if self.is_full():
            return None

        target = None
        closest_distance = self.vision

        for food in foods:
            d = distance(self.x, self.y, food.x, food.y)
            if d < closest_distance:
                closest_distance = d
                target = food.x, food.y, "food"

        if target is not None or self.energy >= CELL_PREDATION_ENERGY_THRESHOLD:
            return target

        for other in cells:
            if other is self or not other.alive or other.radius >= self.radius - 1:
                continue

            d = distance(self.x, self.y, other.x, other.y)

            if d < closest_distance:
                closest_distance = d
                target = other.x, other.y, "cell"

        return target

    def update_wander_direction(self):
        self.wander_timer -= 1

        if self.wander_timer > 0:
            return

        angle = math.atan2(self.wander_dy, self.wander_dx) + random.uniform(-0.5, 0.5)
        self.wander_dx = math.cos(angle)
        self.wander_dy = math.sin(angle)
        self.wander_timer = random.randint(30, 100)

    def move(self, target):
        self.update_wander_direction()

        if target:
            target_dx, target_dy = normalize(target[0] - self.x, target[1] - self.y)

            if target_dx == 0 and target_dy == 0:
                target_dx, target_dy = self.wander_dx, self.wander_dy
        else:
            target_dx, target_dy = self.wander_dx, self.wander_dy

        wall_zone = WALL_MARGIN + 30
        wall_dx = 0.0
        wall_dy = 0.0

        if self.x < wall_zone:
            wall_dx = (wall_zone - self.x) / wall_zone

        elif self.x > WIDTH - wall_zone:
            wall_dx = -(self.x - WIDTH + wall_zone) / wall_zone

        if self.y < wall_zone:
            wall_dy = (wall_zone - self.y) / wall_zone

        elif self.y > HEIGHT - wall_zone:
            wall_dy = -(self.y - HEIGHT + wall_zone) / wall_zone

        escape_dx = escape_dy = 0.0

        if self.escape_timer > 0:
            escape_dx, escape_dy = random.uniform(-1, 1), random.uniform(-1, 1)
            self.escape_timer -= 1

        move_dx, move_dy = normalize(target_dx + self.wander_dx * 0.3 + wall_dx * 2.8 + escape_dx * 0.8, target_dy + self.wander_dy * 0.3 + wall_dy * 2.8 + escape_dy * 0.8)

        target_speed = self.speed

        if target:
            target_distance = distance(self.x, self.y, target[0], target[1])

            if target_distance < self.radius * 3:
                target_speed *= 0.45

            elif target_distance < self.radius * 6:
                target_speed *= 0.7

        target_vx = move_dx * target_speed
        target_vy = move_dy * target_speed
        steering = 0.22

        self.vx += (target_vx - self.vx) * steering
        self.vy += (target_vy - self.vy) * steering

        velocity = math.hypot(self.vx, self.vy)

        if velocity < MIN_SPEED:
            self.vx = self.wander_dx * MIN_SPEED
            self.vy = self.wander_dy * MIN_SPEED
        elif velocity > MAX_SPEED:
            scale = MAX_SPEED / velocity
            self.vx *= scale
            self.vy *= scale

        self.x += self.vx
        self.y += self.vy

    def eat_food(self, foods):
        if self.is_full():
            return

        for food in foods:
            if distance(self.x, self.y, food.x, food.y) <= self.radius + 5:
                self.energy = min(CELL_MAX_ENERGY, self.energy + food.energy)
                foods.remove(food)
                return

    def eat_cells(self, cells):
        if self.energy >= CELL_PREDATION_ENERGY_THRESHOLD:
            return

        for other in cells:
            if other is self or not other.alive or other.radius >= self.radius - 1:
                continue

            if distance(self.x, self.y, other.x, other.y) <= self.radius + other.radius:
                self.energy = min(CELL_MAX_ENERGY, self.energy + other.energy * 0.75)
                other.alive = False
                return

    def update_attributes(self):
        energy_ratio = clamp(self.energy / CELL_MAX_ENERGY, 0.0, 1.0)
        target_radius = 7.0 + (self.max_radius - 7.0) * energy_ratio

        if target_radius > self.radius:
            self.radius += 0.07

        elif target_radius < self.radius:
            self.radius -= 0.025

        self.radius = clamp(self.radius, 7.0, self.max_radius)

        speed_factor = clamp(self.energy / CELL_MAX_ENERGY, 0.55, 1.0)
        self.speed = clamp(self.base_speed * speed_factor, MIN_SPEED, MAX_SPEED)

    def reproduce(self):
        if self.reproduction_cooldown > 0:
            return None

        if self.energy < CELL_REPRODUCE_ENERGY_THRESHOLD or self.age < CELL_REPRODUCE_AGE_THRESHOLD or self.radius < CELL_REPRODUCE_RADIUS_THRESHOLD or random.random() > self.reproduction_rate:
            return None

        child_energy = self.energy * REPRODUCTION_ENERGY_COST
        mother_energy = self.energy - child_energy

        if mother_energy < CELL_REPRODUCE_ENERGY_THRESHOLD * 0.65:
            return None

        self.energy = mother_energy

        dx, dy = random_direction()
        spawn_distance = self.radius + 18

        child = Cell(clamp(self.x + dx * spawn_distance, 10, WIDTH - 10), clamp(self.y + dy * spawn_distance, 10, HEIGHT - 10), child_energy)

        child.base_speed = clamp(self.base_speed * random.uniform(0.95, 1.05), 1.2, 3.2)
        child.vision = clamp(self.vision * random.uniform(0.95, 1.05), 60, 200)
        child.reproduction_rate = clamp(self.reproduction_rate * random.uniform(0.9, 1.1), 0.0007, 0.003)
        child.max_radius = clamp(self.max_radius * random.uniform(0.95, 1.05), 12, 17)
        child.max_age = int(self.max_age * random.uniform(0.95, 1.05))

        child.vx = self.vx * 0.35 + dx * 0.65
        child.vy = self.vy * 0.35 + dy * 0.65

        self.reproduction_cooldown = REPRODUCTION_COOLDOWN
        child.reproduction_cooldown = REPRODUCTION_COOLDOWN

        return child

    def check_stuck(self):
        self.stuck_timer += 1

        if self.stuck_timer < STUCK_CHECK_INTERVAL:
            return

        moved_distance = distance(self.x, self.y, self.last_check_x, self.last_check_y)

        if moved_distance < STUCK_DISTANCE_THRESHOLD:
            self.wander_dx, self.wander_dy = random_direction()
            self.vx += self.wander_dx * 0.8
            self.vy += self.wander_dy * 0.8
            self.escape_timer = 15

        self.last_check_x = self.x
        self.last_check_y = self.y
        self.stuck_timer = 0

    def update(self, foods, cells):
        if not self.alive:
            return

        self.age += 1
        self.energy -= CELL_ENERGY_PER_FRAME

        if self.reproduction_cooldown > 0:
            self.reproduction_cooldown -= 1

        if self.energy <= 0:
            self.energy = 0
            self.alive = False
            return

        self.move(self.find_target(foods, cells))

        if self.energy < CELL_MAX_ENERGY:
            self.eat_food(foods)

        self.update_attributes()

        self.x = clamp(self.x, self.radius, WIDTH - self.radius)
        self.y = clamp(self.y, self.radius, HEIGHT - self.radius)

        self.check_stuck()

        if self.age >= self.max_age:
            self.alive = False

    def draw(self, surface):
        energy_ratio = clamp(self.energy / CELL_MAX_ENERGY, 0.0, 1.0)
        energy_visual = int(energy_ratio * 255)

        x = int(self.x)
        y = int(self.y)
        radius = max(1, int(self.radius))
        glow_size = radius + 15

        glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)

        for r in range(radius + 8, radius, -2):
            alpha = max(0, 25 - (r - radius) * 3)
            pygame.draw.circle(glow, (50, energy_visual, 120, alpha), (glow_size, glow_size), r)

        surface.blit(glow, (x - glow_size, y - glow_size))

        pygame.draw.circle(surface, CELL_MEMBRANE_COLOR, (x, y), radius)

        inner_green = min(255, int(80 + energy_ratio * 140))
        pygame.draw.circle(surface, (40, inner_green, 130), (x, y), max(1, radius - 2))

        nucleus_red = int(80 + energy_ratio * 140)
        nucleus_blue = int(150 + energy_ratio * 100)

        pygame.draw.circle(surface, (nucleus_red, 40, min(255, nucleus_blue)), (x, y), max(2, radius // 3))
        pygame.draw.circle(surface, CELL_NUCLEAR_REFLECTION_COLOR, (x - 1, y - 1), 1)

def get_alive_cells(cells):
    alive_cells = []

    for cell in cells:
        if cell.alive:
            alive_cells.append(cell)

    return alive_cells

def resolve_collisions(cells):
    alive_cells = get_alive_cells(cells)

    if len(alive_cells) < 2:
        return

    for _ in range(COLLISION_ITERATIONS):
        for i, cell_1 in enumerate(alive_cells):
            for cell_2 in alive_cells[i + 1:]:
                if not cell_1.alive or not cell_2.alive:
                    continue

                dx = cell_2.x - cell_1.x
                dy = cell_2.y - cell_1.y
                current_distance = math.hypot(dx, dy)
                min_distance = cell_1.radius + cell_2.radius

                if current_distance >= min_distance:
                    continue

                if current_distance < 0.000001:
                    nx, ny = random_direction()
                    current_distance = 0.000001

                else:
                    nx = dx / current_distance
                    ny = dy / current_distance

                correction = (min_distance - current_distance) * 0.52

                cell_1.x -= nx * correction
                cell_1.y -= ny * correction
                cell_2.x += nx * correction
                cell_2.y += ny * correction

                relative_vx = cell_2.vx - cell_1.vx
                relative_vy = cell_2.vy - cell_1.vy
                relative_normal_velocity = relative_vx * nx + relative_vy * ny

                if relative_normal_velocity < 0:
                    impulse = -(1 + COLLISION_RESTITUTION) * relative_normal_velocity / 2
                    ix = nx * impulse
                    iy = ny * impulse

                    cell_1.vx -= ix
                    cell_1.vy -= iy
                    cell_2.vx += ix
                    cell_2.vy += iy

                tangent_x = -ny
                tangent_y = nx

                cell_1_tangent = cell_1.vx * tangent_x + cell_1.vy * tangent_y
                cell_2_tangent = cell_2.vx * tangent_x + cell_2.vy * tangent_y

                if abs(cell_1_tangent) < 0.15:
                    cell_1.vx += tangent_x * 0.08
                    cell_1.vy += tangent_y * 0.08

                if abs(cell_2_tangent) < 0.15:
                    cell_2.vx -= tangent_x * 0.08
                    cell_2.vy -= tangent_y * 0.08

    for cell in alive_cells:
        cell.x = clamp(cell.x, cell.radius, WIDTH - cell.radius)
        cell.y = clamp(cell.y, cell.radius, HEIGHT - cell.radius)

def create_cells():
    cells = []

    for _ in range(CELL_COUNT):
        x = random.randint(50, WIDTH - 50)
        y = random.randint(50, HEIGHT - 50)

        while True:
            valid_position = True

            for cell in cells:
                if distance(x, y, cell.x, cell.y) < cell.radius + 15:
                    valid_position = False
                    break

            if valid_position:
                break

            x = random.randint(50, WIDTH - 50)
            y = random.randint(50, HEIGHT - 50)

        cells.append(Cell(x, y, random.uniform(85, 120)))

    return cells

def create_food(cells):
    foods = []

    for _ in range(FOOD_COUNT):
        foods.append(Food(cells))

    return foods

def spawn_food(foods, cells):
    if len(foods) < FOOD_COUNT and random.random() < FOOD_RESPAWN_CHANCE:
        foods.append(Food(cells))

def reset():
    cells = create_cells()
    return cells, create_food(cells)

cells, foods = reset()
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    for cell in cells:
        cell.update(foods, cells)

    for cell in cells:
        if cell.alive:
            cell.eat_cells(cells)

    resolve_collisions(cells)

    new_cells = []

    for cell in cells:
        if cell.alive:
            child = cell.reproduce()

            if child:
                new_cells.append(child)

    cells.extend(new_cells)
    cells = alive_cells = get_alive_cells(cells)

    while len(foods) < MIN_FOOD_COUNT:
        foods.append(Food(cells))

    spawn_food(foods, cells)

    screen.fill(BACKGROUND_COLOR)

    for food in foods:
        food.draw(screen)

    for cell in cells:
        cell.draw(screen)

    screen.blit(font.render(f"Cells: {len(cells)}  Food: {len(foods)}", True, TEXT_COLOR), (10, 10))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
