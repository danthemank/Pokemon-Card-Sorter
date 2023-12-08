import time
import subprocess
from wifi import Cell, Scheme
import requests
from bs4 import BeautifulSoup

class servoSetup:

    def run_command(command):
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Command error: {e.stderr}"

    def get_current_network():
        list_command = ["wpa_cli", "-i", "wlan0", "list_networks"]
        networks_info = servoSetup.run_command(list_command).splitlines()[1:]  # Remove header line
        print(networks_info)

        network_id = None
        last_ssid=''
        original_ssid=''
        for line in networks_info:
            fields = line.split()
            last_ssid = fields[1]
            state = fields[3]
            if 'CURRENT' in state:
                original_ssid=last_ssid
                break
        if original_ssid=='':
            original_ssid=last_ssid
        print(f"current network {original_ssid}")
        return original_ssid

    def select_wifi_network(network_name):
        list_command = ["wpa_cli", "-i", "wlan0", "list_networks"]
        networks_info = servoSetup.run_command(list_command).splitlines()[1:]  # Remove header line
        #print(networks_info)

        network_id = None
        for line in networks_info:
            fields = line.split()
            ssid = fields[1]
            if ssid == network_name:
                network_id = fields[0]
                break

        if network_id is not None:
            select_command = ["wpa_cli", "-i", "wlan0", "select_network", network_id]
            #enable_command = ["wpa_cli", "-i", "wlan0", "enable_network", "all"]
            enable_command = ["wpa_cli", "-i", "wlan0", "enable_network", network_id]
            servoSetup.run_command(select_command)
            servoSetup.run_command(enable_command)

            #networks_info = servoSetup.run_command(list_command).splitlines()[1:]  # Remove header line
            #print(networks_info)

            return "Selected and enabled network: " + network_name
        else:
            return "Network not found: " + network_name


    def connect_to_wifi(network_name):
        result = servoSetup.select_wifi_network(network_name)
        print(result)

    def execute_command_servo_driver(command):
        original_ssid = ""
        original_ssid = servoSetup.get_current_network()
        motor_ssid = "ESP32_DEV"
        
        # Connect to the motor network and make the web request
        print("swtiching to servo control board wifi network")
        servoSetup.connect_to_wifi(motor_ssid)

        # Make your web request here
        i=0
        while i < 3:
            try:
                servoSetup.make_http_request(command)
                print('command sent successfully')
                break
            except:
                print('error connecting, retrying in 10 seconds...')
                time.sleep(10)
                i=i+1
        
        # Disconnect from the motor network and reconnect to the original network
        print("swtiching back to normal wifi")
        servoSetup.connect_to_wifi(original_ssid)
        
    def make_http_request(command):
        print(f"driver board sending command: {command}")

        url = "http://192.168.4.1/"
        #url = settings["servo_driver_board"]

        print(f"url {url}")

        # Make a GET request to the webpage
        response = requests.get(url,timeout=5)

        #print(response.content)
        print ('Initial Request\n\n')
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        #print(soup)
        print (f'Response {response.status_code}')
        if response.status_code != 200:
            raise Exception('Coudnt connect to servo control board')

        ajax_url = url+"cmd"

        # Parameters to be sent in the request

        if command == 'start_serial_forwarding':
            inputT = 1
            inputI = 14
            inputA = 0
            inputB = 0
        elif command == 'stop_serial_forwarding':
            inputT = 1
            inputI = 15
            inputA = 0
            inputB = 0
        elif command == "move_to_middle_position":
              inputT = 1
              inputI = 1
              inputA = 0
              inputB = 0

        params = {
            "inputT": inputT,
            "inputI": inputI,
            "inputA": inputA,
            "inputB": inputB
        }
        
        # Make a GET request
        print('making ajax request.....')
        print(url, params)
        try:
            response = requests.get(ajax_url, params=params)
        
        except requests.exceptions.ConnectionError:
            print("ConnectionError: Ignoring the connection issue.")
        return

        # Print the response content
        #print (f'Response {response.status_coden}')
        print(response.content)
        # Parse the HTML content
        #soup = BeautifulSoup(response.content, 'html.parser')
        #print(soup)

if __name__ == "__main__":
    servoSetup.execute_command_servo_driver('stop_serial_forwarding')
    time.sleep(5)
    servoSetup.execute_command_servo_driver('start_serial_forwarding')

