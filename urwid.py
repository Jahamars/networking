import os
import subprocess
import sys
import re
import urwid

CONFIG_FILE_PATH = "/etc/network/interfaces"
BACKUP_FILE_PATH = "/etc/network/interfaces.back"

def require_root():
    if os.geteuid() != 0:
        print("Эта программа должна быть запущена от имени root.")
        sys.exit(1)

def get_wireless_interfaces():
    result = subprocess.run(["iwconfig"], capture_output=True, text=True).stdout
    interfaces = re.findall(r"(\w+)\s+IEEE 802.11", result)
    return interfaces

def scan_wifi_networks(interface):
    result = subprocess.run(["iwlist", interface, "scan"], capture_output=True, text=True).stdout
    networks = re.findall(r"ESSID:\"([^\"]+)\"", result)
    return list(set(networks))  # Убираем дубликаты

def create_network_config(device, ssid, password):
    # Создание резервной копии файла конфигурации
    if os.path.exists(CONFIG_FILE_PATH):
        os.rename(CONFIG_FILE_PATH, BACKUP_FILE_PATH)

    # Создание нового файла interfaces с обновленными настройками
    new_content = f"""
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

    # Создание дополнительного файла с информацией о сети и пароле
    with open(f"/etc/network/{ssid}_credentials", 'w') as cred_file:
        cred_file.write(f"SSID: {ssid}\nPassword: {password}\n")

def restart_networking():
    try:
        subprocess.run(["systemctl", "restart", "networking"], check=True)
        print("Служба networking успешно перезапущена.")
    except subprocess.CalledProcessError:
        print("Не удалось перезапустить службу networking. Проверьте права доступа.")

# Интерфейс с использованием urwid
def main_menu(interfaces):
    body = [urwid.Text("Выберите беспроводной интерфейс:"), urwid.Divider()]
    options = []

    for interface in interfaces:
        button = urwid.Button(interface)
        urwid.connect_signal(button, 'click', select_interface, interface)
        options.append(urwid.AttrMap(button, None, focus_map='reversed'))
    
    body.extend(options)
    return urwid.ListBox(urwid.SimpleFocusListWalker(body))

def select_interface(button, interface):
    networks = scan_wifi_networks(interface)
    if not networks:
        main.original_widget = urwid.Text("Wi-Fi сети не найдены. Вернитесь и выберите другой интерфейс.")
    else:
        main.original_widget = network_menu(interface, networks)

def network_menu(interface, networks):
    body = [urwid.Text(f"Доступные Wi-Fi сети для {interface}:"), urwid.Divider()]
    options = []

    for ssid in networks:
        button = urwid.Button(ssid)
        urwid.connect_signal(button, 'click', select_network, (interface, ssid))
        options.append(urwid.AttrMap(button, None, focus_map='reversed'))

    body.extend(options)
    return urwid.ListBox(urwid.SimpleFocusListWalker(body))

def select_network(button, data):
    interface, ssid = data
    password_edit = urwid.Edit("Введите пароль сети (PSK): ")

    def save_password(button):
        password = password_edit.edit_text
        create_network_config(interface, ssid, password)
        restart_networking()
        main.original_widget = urwid.Text("Конфигурация обновлена и служба networking перезапущена.")

    save_button = urwid.Button("Сохранить")
    urwid.connect_signal(save_button, 'click', save_password)

    main.original_widget = urwid.Pile([password_edit, save_button])

require_root()
interfaces = get_wireless_interfaces()
if not interfaces:
    print("Беспроводные интерфейсы не найдены.")
else:
    main = urwid.Padding(main_menu(interfaces), left=2, right=2)
    top = urwid.Overlay(main, urwid.SolidFill(), align='center', width=('relative', 80), valign='middle', height=('relative', 80))
    urwid.MainLoop(top, palette=[('reversed', 'standout', '')]).run()
