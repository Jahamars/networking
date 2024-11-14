import os
import subprocess
import sys
import re

CONFIG_FILE_PATH = "/etc/network/interfaces"

def require_root():
    if os.geteuid() != 0:
        print("Эта программа должна быть запущена от имени root.")
        sys.exit(1)

def get_user_input(prompt):
    return input(prompt)

def get_wireless_interfaces():
    result = subprocess.run(["iwconfig"], capture_output=True, text=True).stdout
    interfaces = re.findall(r"(\w+)\s+IEEE 802.11", result)
    return interfaces

def scan_wifi_networks(interface):
    result = subprocess.run(["iwlist", interface, "scan"], capture_output=True, text=True).stdout
    networks = re.findall(r"ESSID:\"([^\"]+)\"", result)
    return list(set(networks))  # Убираем дубликаты

def show_current_config():
    print("\n=== Текущая конфигурация сетевого интерфейса ===\n")
    try:
        with open(CONFIG_FILE_PATH, 'r') as file:
            print(file.read())
    except FileNotFoundError:
        print(f"Файл конфигурации {CONFIG_FILE_PATH} не найден.")
    except PermissionError:
        print(f"Нет доступа к файлу {CONFIG_FILE_PATH}.")

def update_network_config(device, ssid, password):
    with open(CONFIG_FILE_PATH, 'r') as file:
        lines = file.readlines()
    
    new_content = ""
    for line in lines:
        if line.strip() and not line.startswith("#"):
            new_content += f"# {line}"
        else:
            new_content += line
    
    new_content += f"""
# Автоматически добавлено конфигуратором WiFi
auto lo
iface lo inet loopback

# Основной сетевой интерфейс
allow-hotplug {device}
iface {device} inet dhcp
    wpa-ssid {ssid}
    wpa-psk {password}
"""

    with open(CONFIG_FILE_PATH, 'w') as file:
        file.write(new_content)

    print("Конфигурация обновлена.")

def restart_networking():
    try:
        subprocess.run(["systemctl", "restart", "networking"], check=True)
        print("Служба networking успешно перезапущена.")
    except subprocess.CalledProcessError:
        print("Не удалось перезапустить службу networking. Проверьте права доступа.")

def main():
    require_root()
    print("=== Конфигуратор WiFi ===")
    choice = get_user_input("Выберите действие:\n1. Показать текущие настройки\n2. Изменить настройки соединения\nВаш выбор: ")

    if choice == '1':
        show_current_config()
    elif choice == '2':
        interfaces = get_wireless_interfaces()
        if not interfaces:
            print("Беспроводные интерфейсы не найдены.")
            return

        print("\nДоступные беспроводные интерфейсы:")
        for idx, interface in enumerate(interfaces, start=1):
            print(f"{idx}. {interface}")

        interface_idx = int(get_user_input("Выберите интерфейс (введите номер): ")) - 1
        device = interfaces[interface_idx]

        networks = scan_wifi_networks(device)
        if not networks:
            print("Wi-Fi сети не найдены.")
            return

        print("\nДоступные Wi-Fi сети:")
        for idx, network in enumerate(networks, start=1):
            print(f"{idx}. {network}")

        network_idx = int(get_user_input("Выберите сеть (введите номер): ")) - 1
        ssid = networks[network_idx]

        password = get_user_input("Введите пароль сети (PSK): ")

        update_network_config(device, ssid, password)
        restart_networking()
    else:
        print("Неверный выбор. Попробуйте снова.")

if __name__ == "__main__":
    main()
  
