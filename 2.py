import os
import subprocess
import sys
import re

CONFIG_FILE_PATH = "/etc/network/interfaces"

# Цвета для вывода текста
class Color:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def require_root():
    if os.geteuid() != 0:
        print(f"{Color.FAIL}Эта программа должна быть запущена от имени root.{Color.ENDC}")
        sys.exit(1)

def get_user_input(prompt):
    return input(f"{Color.OKCYAN}{prompt}{Color.ENDC}")

def get_wireless_interfaces():
    result = subprocess.run(["iwconfig"], capture_output=True, text=True).stdout
    interfaces = re.findall(r"(\w+)\s+IEEE 802.11", result)
    return interfaces

def scan_wifi_networks(interface):
    result = subprocess.run(["iwlist", interface, "scan"], capture_output=True, text=True).stdout
    networks = re.findall(r"ESSID:\"([^\"]+)\"", result)
    return list(set(networks))  # Убираем дубликаты

def show_current_config():
    print(f"\n{Color.HEADER}=== Текущая конфигурация сетевого интерфейса ==={Color.ENDC}\n")
    try:
        with open(CONFIG_FILE_PATH, 'r') as file:
            print(f"{Color.OKGREEN}{file.read()}{Color.ENDC}")
    except FileNotFoundError:
        print(f"{Color.FAIL}Файл конфигурации {CONFIG_FILE_PATH} не найден.{Color.ENDC}")
    except PermissionError:
        print(f"{Color.FAIL}Нет доступа к файлу {CONFIG_FILE_PATH}.{Color.ENDC}")

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

    print(f"{Color.OKGREEN}Конфигурация обновлена успешно.{Color.ENDC}")

def restart_networking():
    try:
        subprocess.run(["systemctl", "restart", "networking"], check=True)
        print(f"{Color.OKGREEN}Служба networking успешно перезапущена.{Color.ENDC}")
    except subprocess.CalledProcessError:
        print(f"{Color.FAIL}Не удалось перезапустить службу networking. Проверьте права доступа.{Color.ENDC}")

def main():
    require_root()
    print(f"{Color.BOLD}=== Конфигуратор WiFi ==={Color.ENDC}")
    choice = get_user_input("Выберите действие:\n1. Показать текущие настройки\n2. Изменить настройки соединения\nВаш выбор: ")

    if choice == '1':
        show_current_config()
    elif choice == '2':
        interfaces = get_wireless_interfaces()
        if not interfaces:
            print(f"{Color.WARNING}Беспроводные интерфейсы не найдены.{Color.ENDC}")
            return

        print(f"\n{Color.HEADER}Доступные беспроводные интерфейсы:{Color.ENDC}")
        for idx, interface in enumerate(interfaces, start=1):
            print(f"{Color.OKBLUE}{idx}. {interface}{Color.ENDC}")

        try:
            interface_idx = int(get_user_input("Выберите интерфейс (введите номер): ")) - 1
            device = interfaces[interface_idx]
        except (ValueError, IndexError):
            print(f"{Color.FAIL}Неверный выбор. Попробуйте снова.{Color.ENDC}")
            return

        networks = scan_wifi_networks(device)
        if not networks:
            print(f"{Color.WARNING}Wi-Fi сети не найдены.{Color.ENDC}")
            return

        print(f"\n{Color.HEADER}Доступные Wi-Fi сети:{Color.ENDC}")
        for idx, network in enumerate(networks, start=1):
            print(f"{Color.OKBLUE}{idx}. {network}{Color.ENDC}")

        try:
            network_idx = int(get_user_input("Выберите сеть (введите номер): ")) - 1
            ssid = networks[network_idx]
        except (ValueError, IndexError):
            print(f"{Color.FAIL}Неверный выбор сети. Попробуйте снова.{Color.ENDC}")
            return

        password = get_user_input("Введите пароль сети (PSK): ")

        update_network_config(device, ssid, password)
        restart_networking()
    else:
        print(f"{Color.FAIL}Неверный выбор. Попробуйте снова.{Color.ENDC}")

if __name__ == "__main__":
    main()

