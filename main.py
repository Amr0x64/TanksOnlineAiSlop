import sys
import subprocess

def main():
    print("=== Игра Танки в Лабиринте ===")
    print("1. Запустить сервер")
    print("2. Запустить клиент (подключиться к серверу)")
    print("3. Выход")
    
    choice = input("Выберите опцию (1/2/3): ").strip()
    
    if choice == '1':
        print("\nЗапуск сервера...")
        print("Ожидание подключения клиентов...")
        import server
        server = server.GameServer()
        try:
            server.run()
        except KeyboardInterrupt:
            print("\nОстановка сервера...")
            server.running = False
    
    elif choice == '2':
        server_host = input("Введите адрес сервера (Enter для localhost): ").strip()
        if not server_host:
            server_host = 'localhost'
        
        print(f"\nПодключение к серверу {server_host}...")
        import client
        from game import TANK_SPEED
        import math
        
        client_obj = client.GameClient(server_host)
        client_obj.run()
    
    elif choice == '3':
        print("Выход...")
        sys.exit(0)
    
    else:
        print("Неверный выбор!")

if __name__ == '__main__':
    main()

