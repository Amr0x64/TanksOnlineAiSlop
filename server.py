import socket
import threading
import json
import time
from game import Game

HOST = '0.0.0.0'
PORT = 5555

class GameServer:
    def __init__(self):
        # Создаем игру без окна (headless режим)
        self.game = Game(create_screen=False)
        self.clients = {}
        self.next_tank_id = 0
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((HOST, PORT))
        self.socket.listen(2)
        print(f"Сервер запущен на {HOST}:{PORT}")
        print("Сервер работает в фоновом режиме (без окна)")
    
    def handle_client(self, conn, addr, tank_id):
        print(f"Клиент {addr} подключен как танк {tank_id}")
        self.clients[tank_id] = conn
        buffer = ''
        
        try:
            while self.running:
                try:
                    data = conn.recv(1024).decode('utf-8')
                    if not data:
                        break
                    
                    buffer += data
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if not line:
                            continue
                        
                        message = json.loads(line)
                        
                        if message['type'] == 'move':
                            # Обновление позиции танка
                            if tank_id in self.game.tanks:
                                tank = self.game.tanks[tank_id]
                                dx = message.get('dx', 0)
                                dy = message.get('dy', 0)
                                angle = message.get('angle', tank.angle)
                                tank.update(dx, dy, angle, self.game.walls, 0.016)
                        
                        elif message['type'] == 'shoot':
                            # Выстрел
                            if tank_id in self.game.tanks:
                                tank = self.game.tanks[tank_id]
                                bullet = tank.shoot()
                                if bullet:
                                    self.game.bullets.append(bullet)
                        
                        elif message['type'] == 'restart':
                            # Перезапуск игры
                            print(f"Игрок {tank_id} запросил перезапуск игры")
                            self.game.reset_game()
                            # Запускаем игру снова, если есть минимум 2 игрока
                            if len(self.game.tanks) >= 2:
                                self.game.start_game()
                                print("Игра перезапущена!")
                
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"Ошибка обработки сообщения от {addr}: {e}")
                    break
        
        except Exception as e:
            print(f"Ошибка соединения с {addr}: {e}")
        finally:
            if tank_id in self.clients:
                del self.clients[tank_id]
            if tank_id in self.game.tanks:
                del self.game.tanks[tank_id]
            conn.close()
            print(f"Клиент {addr} отключен")
    
    def game_loop(self):
        last_time = time.time()
        while self.running:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            
            self.game.update(dt)
            time.sleep(0.033)  # ~30 FPS, синхронизировано с broadcast_loop
    
    def broadcast_loop(self):
        while self.running:
            state = self.game.get_state()
            message = json.dumps({'type': 'state', 'data': state})
            
            disconnected = []
            for tank_id, conn in self.clients.items():
                try:
                    conn.sendall((message + '\n').encode('utf-8'))
                except:
                    disconnected.append(tank_id)
            
            for tank_id in disconnected:
                if tank_id in self.clients:
                    del self.clients[tank_id]
                if tank_id in self.game.tanks:
                    del self.game.tanks[tank_id]
            
            time.sleep(0.033)  # ~30 обновлений в секунду для снижения сетевой задержки
    
    def run(self):
        # Запуск игрового цикла
        game_thread = threading.Thread(target=self.game_loop, daemon=True)
        game_thread.start()
        
        # Запуск цикла рассылки
        broadcast_thread = threading.Thread(target=self.broadcast_loop, daemon=True)
        broadcast_thread.start()
        
        # Принятие подключений
        while self.running:
            try:
                conn, addr = self.socket.accept()
                tank_id = self.next_tank_id
                self.next_tank_id += 1
                
                # Добавление танка
                self.game.add_tank(tank_id)
                
                # Запускаем игру, если подключился второй игрок
                if len(self.game.tanks) == 2 and not self.game.game_started:
                    self.game.start_game()
                    print("Игра началась! Таймер: 60 секунд")
                
                # Отправка начального состояния
                initial_message = json.dumps({
                    'type': 'init',
                    'tank_id': tank_id,
                    'state': self.game.get_state()
                })
                conn.sendall((initial_message + '\n').encode('utf-8'))
                
                # Запуск обработки клиента
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr, tank_id),
                    daemon=True
                )
                client_thread.start()
            
            except Exception as e:
                if self.running:
                    print(f"Ошибка принятия подключения: {e}")
        
        self.socket.close()

if __name__ == '__main__':
    server = GameServer()
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nОстановка сервера...")
        server.running = False

