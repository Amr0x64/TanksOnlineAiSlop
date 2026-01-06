import pygame
import socket
import json
import threading
import math
from game import Game, TANK_SPEED

HOST = 'localhost'
PORT = 5555

class GameClient:
    def __init__(self, server_host=HOST):
        self.server_host = server_host
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Tanks Battle - Client")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        
        self.game = Game()
        # Переопределяем экран игры на наш экран клиента
        self.game.screen = self.screen
        
        self.tank_id = None
        self.socket = None
        self.running = True
        self.last_state = None
    
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, PORT))
            print(f"Подключено к серверу {self.server_host}:{PORT}")
            
            # Получение начального состояния (может прийти частями)
            buffer = ''
            while True:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    break
                
                buffer += data
                if '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            message = json.loads(line)
                            if message['type'] == 'init':
                                self.tank_id = message['tank_id']
                                self.game.set_state(message['state'])
                                print(f"Ваш танк ID: {self.tank_id}")
                                print(f"Танков в игре: {len(self.game.tanks)}")
                                if self.tank_id in self.game.tanks:
                                    tank = self.game.tanks[self.tank_id]
                                    print(f"Позиция танка: ({tank.x}, {tank.y}), цвет: {tank.color}, жив: {tank.alive}")
                                return True
                        except json.JSONDecodeError:
                            continue
            
            return False
        
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_message(self, message):
        if self.socket:
            try:
                self.socket.sendall((json.dumps(message) + '\n').encode('utf-8'))
            except Exception as e:
                print(f"Ошибка отправки сообщения: {e}")
    
    def receive_loop(self):
        buffer = ''
        while self.running:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            message = json.loads(line)
                            if message['type'] == 'state':
                                self.last_state = message['data']
                        except json.JSONDecodeError:
                            continue
            
            except Exception as e:
                if self.running:
                    print(f"Ошибка получения данных: {e}")
                break
    
    def handle_input(self):
        keys = pygame.key.get_pressed()
        
        if self.tank_id is None:
            return
        
        # Всегда отправляем обновление угла, даже если танк еще не создан
        mouse_x, mouse_y = pygame.mouse.get_pos()
        
        # Получаем текущие координаты танка из состояния игры
        if self.tank_id in self.game.tanks:
            tank = self.game.tanks[self.tank_id]
            tank_x, tank_y = tank.x, tank.y
        else:
            # Если танк еще не создан, используем центр экрана
            tank_x, tank_y = 400, 300
        
        dx, dy = 0, 0
        
        # Движение
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy = -TANK_SPEED
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy = TANK_SPEED
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx = -TANK_SPEED
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx = TANK_SPEED
        
        # Поворот пушки
        angle = math.atan2(mouse_y - tank_y, mouse_x - tank_x)
        
        # Отправляем обновление, если есть движение или значительное изменение угла
        if dx != 0 or dy != 0:
            self.send_message({
                'type': 'move',
                'dx': dx,
                'dy': dy,
                'angle': angle
            })
        elif self.tank_id in self.game.tanks:
            tank = self.game.tanks[self.tank_id]
            if abs(angle - tank.angle) > 0.05:
                self.send_message({
                    'type': 'move',
                    'dx': 0,
                    'dy': 0,
                    'angle': angle
                })
    
    def run(self):
        if not self.connect():
            return
        
        # Запуск потока получения данных
        receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
        receive_thread.start()
        
            # Игровой цикл
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Левая кнопка мыши
                        if not self.game.game_ended:
                            self.send_message({'type': 'shoot'})
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:  # Клавиша R для перезапуска
                        print("Запрос перезапуска игры...")
                        self.send_message({'type': 'restart'})
            
            # Применение последнего состояния от сервера
            if self.last_state:
                self.game.set_state(self.last_state)
                self.last_state = None
            
            # Обработка ввода только если игра не окончена
            if not self.game.game_ended:
                self.handle_input()
            
            # Отрисовка
            if self.game.game_ended:
                self.game.draw_game_over(self.screen, self.font)
            else:
                self.game.draw(screen=self.screen, font=self.font)
            
            self.clock.tick(60)
        
        if self.socket:
            self.socket.close()
        pygame.quit()

if __name__ == '__main__':
    import sys
    
    server_host = sys.argv[1] if len(sys.argv) > 1 else HOST
    client = GameClient(server_host)
    client.run()

