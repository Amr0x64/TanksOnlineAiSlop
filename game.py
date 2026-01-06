import pygame
import math
import json

# Инициализация pygame (будет выполнена при создании экрана)

# Константы
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TANK_SIZE = 30
TANK_SPEED = 3
BULLET_SIZE = 5
BULLET_SPEED = 8
WALL_COLOR = (100, 100, 100)
SPAWN_POINTS = [(50, 50), (750, 550)]

# Цвета танков
TANK_COLORS = [(255, 0, 0), (0, 0, 255)]  # Красный и синий

class Wall:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
    
    def draw(self, screen):
        pygame.draw.rect(screen, WALL_COLOR, self.rect)

class Bullet:
    def __init__(self, x, y, angle, owner_id):
        self.x = x
        self.y = y
        self.angle = angle
        self.owner_id = owner_id
        self.rect = pygame.Rect(x - BULLET_SIZE//2, y - BULLET_SIZE//2, BULLET_SIZE, BULLET_SIZE)
    
    def update(self):
        dx = math.cos(self.angle) * BULLET_SPEED
        dy = math.sin(self.angle) * BULLET_SPEED
        self.x += dx
        self.y += dy
        self.rect.x = self.x - BULLET_SIZE//2
        self.rect.y = self.y - BULLET_SIZE//2
    
    def draw(self, screen):
        pygame.draw.circle(screen, (255, 255, 0), (int(self.x), int(self.y)), BULLET_SIZE)
    
    def to_dict(self):
        return {
            'x': self.x,
            'y': self.y,
            'angle': self.angle,
            'owner_id': self.owner_id
        }
    
    @staticmethod
    def from_dict(data):
        bullet = Bullet(data['x'], data['y'], data['angle'], data['owner_id'])
        return bullet

class Tank:
    def __init__(self, tank_id, x, y, color):
        self.id = tank_id
        self.x = x
        self.y = y
        self.angle = 0
        self.color = color
        self.rect = pygame.Rect(x - TANK_SIZE//2, y - TANK_SIZE//2, TANK_SIZE, TANK_SIZE)
        self.spawn_x = x
        self.spawn_y = y
        self.alive = True
        self.kills = 0  # Счетчик убийств
        self.invulnerability_time = 2.0  # Время неуязвимости в секундах
        self.spawn_time = 0.0  # Время спавна (для отсчета неуязвимости)
    
    def update(self, dx, dy, angle, walls, dt=0.016):
        if not self.alive:
            return
        
        self.angle = angle
        
        # Обновление времени неуязвимости
        if self.spawn_time > 0:
            self.spawn_time -= dt
            if self.spawn_time < 0:
                self.spawn_time = 0
        
        # Проверка столкновений со стенами
        old_x, old_y = self.x, self.y
        self.x += dx
        self.y += dy
        
        self.rect.x = self.x - TANK_SIZE//2
        self.rect.y = self.y - TANK_SIZE//2
        
        # Проверка столкновений
        for wall in walls:
            if self.rect.colliderect(wall.rect):
                self.x = old_x
                self.y = old_y
                self.rect.x = self.x - TANK_SIZE//2
                self.rect.y = self.y - TANK_SIZE//2
                break
        
        # Ограничение границами экрана
        self.x = max(TANK_SIZE//2, min(SCREEN_WIDTH - TANK_SIZE//2, self.x))
        self.y = max(TANK_SIZE//2, min(SCREEN_HEIGHT - TANK_SIZE//2, self.y))
        self.rect.x = self.x - TANK_SIZE//2
        self.rect.y = self.y - TANK_SIZE//2
    
    def draw(self, screen):
        if not self.alive:
            return
        
        # Убеждаемся, что цвет - это tuple
        color = self.color
        if isinstance(color, list):
            color = tuple(color)
        
        # Визуальный эффект неуязвимости (мигание)
        is_invulnerable = self.is_invulnerable()
        if is_invulnerable:
            # Мигание: прозрачность меняется от 50% до 100%
            # Используем pygame.time.get_ticks() для плавного мигания (5 раз в секунду)
            blink_speed = 5.0  # Частота мигания
            current_time = pygame.time.get_ticks() / 1000.0  # Конвертируем в секунды
            alpha = int(128 + 127 * math.sin(current_time * blink_speed * 2 * math.pi))
            # Создаем поверхность с прозрачностью
            tank_surface = pygame.Surface((TANK_SIZE + 4, TANK_SIZE + 4), pygame.SRCALPHA)
            
            # Корпус танка с прозрачностью и эффектом свечения
            tank_rect_on_surface = pygame.Rect(2, 2, TANK_SIZE, TANK_SIZE)
            # Смешиваем цвет с белым для эффекта свечения
            glow_color = tuple(min(255, c + 80) for c in color)
            # Внешнее свечение
            outer_glow = tuple(min(255, c + 100) for c in color)
            pygame.draw.rect(tank_surface, (*outer_glow, alpha // 2), pygame.Rect(0, 0, TANK_SIZE + 4, TANK_SIZE + 4))
            pygame.draw.rect(tank_surface, (*glow_color, alpha), tank_rect_on_surface)
            pygame.draw.rect(tank_surface, (255, 255, 255, alpha), tank_rect_on_surface, 2)
            
            # Пушка с прозрачностью
            center_x, center_y = (TANK_SIZE + 4) // 2, (TANK_SIZE + 4) // 2
            gun_length = TANK_SIZE
            gun_end_x = center_x + math.cos(self.angle) * gun_length
            gun_end_y = center_y + math.sin(self.angle) * gun_length
            pygame.draw.line(tank_surface, (*glow_color, alpha), 
                           (center_x, center_y), 
                           (int(gun_end_x), int(gun_end_y)), 4)
            
            # Рисуем поверхность на экране
            screen.blit(tank_surface, (int(self.x - TANK_SIZE//2 - 2), int(self.y - TANK_SIZE//2 - 2)))
        else:
            # Обычная отрисовка
            tank_rect = pygame.Rect(int(self.x - TANK_SIZE//2), int(self.y - TANK_SIZE//2), TANK_SIZE, TANK_SIZE)
            pygame.draw.rect(screen, color, tank_rect)
            pygame.draw.rect(screen, (0, 0, 0), tank_rect, 2)
            
            # Пушка
            gun_length = TANK_SIZE
            gun_end_x = self.x + math.cos(self.angle) * gun_length
            gun_end_y = self.y + math.sin(self.angle) * gun_length
            pygame.draw.line(screen, color, (int(self.x), int(self.y)), (int(gun_end_x), int(gun_end_y)), 4)
    
    def shoot(self):
        if not self.alive:
            return None
        
        bullet_x = self.x + math.cos(self.angle) * (TANK_SIZE//2 + BULLET_SIZE)
        bullet_y = self.y + math.sin(self.angle) * (TANK_SIZE//2 + BULLET_SIZE)
        return Bullet(bullet_x, bullet_y, self.angle, self.id)
    
    def respawn(self):
        self.x = self.spawn_x
        self.y = self.spawn_y
        self.angle = 0
        self.rect.x = self.x - TANK_SIZE//2
        self.rect.y = self.y - TANK_SIZE//2
        self.alive = True
        self.spawn_time = self.invulnerability_time  # Активируем неуязвимость
    
    def is_invulnerable(self):
        """Проверка, неуязвим ли танк"""
        return self.spawn_time > 0
    
    def take_damage(self):
        self.alive = False
        self.respawn()
    
    def to_dict(self):
        return {
            'id': self.id,
            'x': self.x,
            'y': self.y,
            'angle': self.angle,
            'color': self.color,
            'spawn_x': self.spawn_x,
            'spawn_y': self.spawn_y,
            'alive': self.alive,
            'kills': self.kills,
            'spawn_time': self.spawn_time
        }
    
    @staticmethod
    def from_dict(data):
        # Убеждаемся, что цвет - это tuple
        color = data['color']
        if isinstance(color, list):
            color = tuple(color)
        
        tank = Tank(data['id'], data['x'], data['y'], color)
        tank.angle = data['angle']
        tank.spawn_x = data['spawn_x']
        tank.spawn_y = data['spawn_y']
        tank.alive = data['alive']
        tank.kills = data.get('kills', 0)
        tank.spawn_time = data.get('spawn_time', 0.0)
        # Обновляем rect
        tank.rect.x = tank.x - TANK_SIZE//2
        tank.rect.y = tank.y - TANK_SIZE//2
        return tank

class Game:
    def __init__(self, create_screen=True):
        self.walls = []
        self.tanks = {}
        self.bullets = []
        self.create_maze()
        self.screen = None
        if create_screen:
            if not pygame.get_init():
                pygame.init()
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.display.set_caption("Tanks Battle")
        
        # Таймер игры (60 секунд)
        self.game_time = 60.0  # В секундах
        self.game_started = False
        self.game_ended = False
    
    def create_maze(self):
        # Создание простого лабиринта
        wall_thickness = 20
        
        # Внешние стены
        self.walls.append(Wall(0, 0, SCREEN_WIDTH, wall_thickness))
        self.walls.append(Wall(0, 0, wall_thickness, SCREEN_HEIGHT))
        self.walls.append(Wall(0, SCREEN_HEIGHT - wall_thickness, SCREEN_WIDTH, wall_thickness))
        self.walls.append(Wall(SCREEN_WIDTH - wall_thickness, 0, wall_thickness, SCREEN_HEIGHT))
        
        # Внутренние стены - лабиринт
        self.walls.append(Wall(200, 100, wall_thickness, 150))
        self.walls.append(Wall(400, 200, 150, wall_thickness))
        self.walls.append(Wall(600, 150, wall_thickness, 200))
        self.walls.append(Wall(150, 300, 200, wall_thickness))
        self.walls.append(Wall(450, 350, wall_thickness, 150))
        self.walls.append(Wall(250, 450, 300, wall_thickness))
        self.walls.append(Wall(100, 500, 100, wall_thickness))
    
    def add_tank(self, tank_id, spawn_index=None):
        if spawn_index is None:
            spawn_index = len(self.tanks) % len(SPAWN_POINTS)
        
        x, y = SPAWN_POINTS[spawn_index]
        color = TANK_COLORS[tank_id % len(TANK_COLORS)]
        tank = Tank(tank_id, x, y, color)
        tank.spawn_time = tank.invulnerability_time  # Даем неуязвимость при первом спавне
        self.tanks[tank_id] = tank
        return tank
    
    def update_bullets(self):
        bullets_to_remove = []
        
        for bullet in self.bullets:
            bullet.update()
            
            # Удаление пуль за границами
            if bullet.x < 0 or bullet.x > SCREEN_WIDTH or bullet.y < 0 or bullet.y > SCREEN_HEIGHT:
                bullets_to_remove.append(bullet)
                continue
            
            # Проверка столкновения со стенами
            for wall in self.walls:
                if bullet.rect.colliderect(wall.rect):
                    bullets_to_remove.append(bullet)
                    break
            
            # Проверка попадания в танк
            for tank_id, tank in self.tanks.items():
                if (tank.id != bullet.owner_id and tank.alive and 
                    bullet.rect.colliderect(tank.rect) and 
                    not tank.is_invulnerable()):  # Проверка неуязвимости
                    # Увеличиваем счетчик убийств у владельца пули
                    if bullet.owner_id in self.tanks:
                        self.tanks[bullet.owner_id].kills += 1
                    tank.take_damage()
                    bullets_to_remove.append(bullet)
                    break
        
        for bullet in bullets_to_remove:
            self.bullets.remove(bullet)
    
    def update(self, dt=0.016):
        if not self.game_ended and self.game_started:
            self.game_time -= dt
            if self.game_time <= 0:
                self.game_time = 0
                self.game_ended = True
        
        # Обновление танков (для таймера неуязвимости)
        for tank in self.tanks.values():
            if tank.alive:
                # Обновляем только таймер неуязвимости, не позицию
                if tank.spawn_time > 0:
                    tank.spawn_time -= dt
                    if tank.spawn_time < 0:
                        tank.spawn_time = 0
        
        self.update_bullets()
    
    def start_game(self):
        self.game_started = True
        self.game_ended = False
        self.game_time = 60.0
    
    def reset_game(self):
        """Сброс игры: очистка пуль, сброс позиций танков, счетчиков и таймера"""
        # Очистка пуль
        self.bullets = []
        
        # Сброс всех танков на точки спавна
        for tank_id, tank in self.tanks.items():
            tank.x = tank.spawn_x
            tank.y = tank.spawn_y
            tank.angle = 0
            tank.alive = True
            tank.kills = 0  # Сброс счетчика убийств
            tank.spawn_time = tank.invulnerability_time  # Активируем неуязвимость при перезапуске
            tank.rect.x = tank.x - TANK_SIZE//2
            tank.rect.y = tank.y - TANK_SIZE//2
        
        # Сброс таймера
        self.game_time = 60.0
        self.game_started = False
        self.game_ended = False
    
    def get_time_remaining(self):
        return max(0, self.game_time)
    
    def draw(self, screen=None, font=None):
        if screen is None:
            screen = self.screen
        
        if screen is None:
            return  # Нет экрана для отрисовки
        
        screen.fill((50, 50, 50))
        
        # Рисование стен
        for wall in self.walls:
            wall.draw(screen)
        
        # Рисование танков
        for tank in self.tanks.values():
            tank.draw(screen)
        
        # Рисование пуль
        for bullet in self.bullets:
            bullet.draw(screen)
        
        # Рисование UI (таймер и счет)
        if font:
            time_text = f"Время: {int(self.game_time)}s"
            time_surface = font.render(time_text, True, (255, 255, 255))
            screen.blit(time_surface, (10, 10))
            
            # Очки каждого игрока
            y_offset = 40
            for tank_id, tank in sorted(self.tanks.items()):
                color = tank.color
                if isinstance(color, list):
                    color = tuple(color)
                
                kills_text = f"Игрок {tank_id + 1}: {tank.kills} убийств"
                kills_surface = font.render(kills_text, True, color)
                screen.blit(kills_surface, (10, y_offset))
                y_offset += 30
            
            # Подсказка о перезапуске (только если игра не началась или окончена)
            if not self.game_started or self.game_ended:
                hint_text = "Нажмите R для перезапуска игры"
                hint_surface = font.render(hint_text, True, (200, 200, 200))
                screen.blit(hint_surface, (10, SCREEN_HEIGHT - 40))
        
        pygame.display.flip()
    
    def draw_game_over(self, screen, font):
        """Отрисовка экрана окончания игры"""
        if screen is None:
            return
        
        # Полупрозрачный фон
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
        
        # Заголовок
        title_text = "ИГРА ОКОНЧЕНА!"
        title_font = pygame.font.Font(None, 72)
        title_surface = title_font.render(title_text, True, (255, 255, 0))
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH//2, 150))
        screen.blit(title_surface, title_rect)
        
        # Результаты
        results_text = "Результаты:"
        results_surface = font.render(results_text, True, (255, 255, 255))
        results_rect = results_surface.get_rect(center=(SCREEN_WIDTH//2, 220))
        screen.blit(results_surface, results_rect)
        
        # Список очков игроков
        y_offset = 270
        sorted_tanks = sorted(self.tanks.items(), key=lambda x: x[1].kills, reverse=True)
        
        for rank, (tank_id, tank) in enumerate(sorted_tanks, 1):
            color = tank.color
            if isinstance(color, list):
                color = tuple(color)
            
            rank_text = f"{rank}. Игрок {tank_id + 1}: {tank.kills} убийств"
            rank_surface = font.render(rank_text, True, color)
            rank_rect = rank_surface.get_rect(center=(SCREEN_WIDTH//2, y_offset))
            screen.blit(rank_surface, rank_rect)
            y_offset += 40
        
        # Определение победителя
        if len(sorted_tanks) > 0:
            winner_id, winner = sorted_tanks[0]
            if winner.kills > 0:
                winner_text = f"ПОБЕДИТЕЛЬ: Игрок {winner_id + 1}!"
                winner_color = winner.color
                if isinstance(winner_color, list):
                    winner_color = tuple(winner_color)
                winner_surface = font.render(winner_text, True, winner_color)
                winner_rect = winner_surface.get_rect(center=(SCREEN_WIDTH//2, y_offset + 30))
                screen.blit(winner_surface, winner_rect)
            else:
                draw_text = "НИЧЬЯ!"
                draw_surface = font.render(draw_text, True, (255, 255, 255))
                draw_rect = draw_surface.get_rect(center=(SCREEN_WIDTH//2, y_offset + 30))
                screen.blit(draw_surface, draw_rect)
        
        # Подсказка о перезапуске
        restart_text = "Нажмите R для перезапуска игры"
        restart_surface = font.render(restart_text, True, (150, 150, 150))
        restart_rect = restart_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 50))
        screen.blit(restart_surface, restart_rect)
        
        pygame.display.flip()
    
    def get_state(self):
        return {
            'tanks': {tid: tank.to_dict() for tid, tank in self.tanks.items()},
            'bullets': [bullet.to_dict() for bullet in self.bullets],
            'game_time': self.game_time,
            'game_started': self.game_started,
            'game_ended': self.game_ended
        }
    
    def set_state(self, state):
        # Обновление или создание танков
        for tid, tank_data in state.get('tanks', {}).items():
            tid = int(tid)  # Убеждаемся, что это int
            if tid in self.tanks:
                # Обновляем существующий танк
                tank = self.tanks[tid]
                tank.x = tank_data['x']
                tank.y = tank_data['y']
                tank.angle = tank_data['angle']
                tank.alive = tank_data['alive']
                tank.kills = tank_data.get('kills', 0)
                tank.spawn_time = tank_data.get('spawn_time', 0.0)
                tank.rect.x = tank.x - TANK_SIZE//2
                tank.rect.y = tank.y - TANK_SIZE//2
            else:
                # Создаем новый танк
                tank = Tank.from_dict(tank_data)
                self.tanks[tid] = tank
        
        # Обновление пуль
        self.bullets = [Bullet.from_dict(b) for b in state.get('bullets', [])]
        
        # Обновление состояния игры
        if 'game_time' in state:
            self.game_time = state['game_time']
        if 'game_started' in state:
            self.game_started = state['game_started']
        if 'game_ended' in state:
            self.game_ended = state['game_ended']

