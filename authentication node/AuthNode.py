# All of the processing code has now been pulled into this file - the network code remains in the other file Abstract...
import os
import subprocess
import sys
import time
from collections import deque
from datetime import datetime
from AuthNetworkInterface import AuthNetworkInterface
import threading
import netifaces

auth_microservice_count = 0

nodePort = 50001

class abstractAuth:
    def __init__(self, host="127.0.0.1", port=50001):
        self.host = host
        self.port = port
        self.networkHandler = AuthNetworkInterface()
        self.connection = None
        self.uiThread = threading.Thread(target=self.ui)
        self.running = True
        print("Authentication Node Initiated")
        # Get IP of CONTENT node
        self.nodeIp = self.getNodeAddress()

        # Load balancer
        self.load_balancer_tasks = deque()
        self.load_balancer_lock = threading.Lock()
        self.max_concurrent_tasks = 2
        self.current_tasks = 0

    # Simple UI thread
    def ui(self):
        # Handle incoming messages from the server - at the moment that is simply "display them to the user"
        while self.running:
            if self.connection:
                message = self.connection.iBuffer.get()
                if message:
                    print()
                    print(message)
                    # Break message loop
                    if message.startswith("cmd"):
                        parts = message.split(":")
                        if len(parts) >= 3 and parts[0] == "cmd":
                            print(f"Command received from bootstrap")
                            if len(parts) >= 3:
                                after_node = parts[1]
                                if after_node == "spwn":
                                    after_node = parts[2]
                                    if after_node == "ms":
                                        print(f"Spawn micro-service command received")
                                        self.authLoadBalancer(parts[1], None)
                                if after_node == "check":
                                    if parts[2] == "token":
                                        # Check client token
                                        token = parts[3]
                                        print(f"Token received from bootstrap: {token}")
                                        self.authLoadBalancer(parts[1], token)

    def process(self):
        # Start the UI thread and start the network components
        self.uiThread.start()
        self.connection = self.networkHandler.start_auth(self.host, self.port)

        while self.running:
            global nodePort
            message = "auth:cmd:load:" + str(self.nodeIp) +":"+ str(nodePort)
            nodePort ++ 1
            if self.connection:
                self.connection.oBuffer.put(message)
                message = input()

        # stop the network components and the UI thread
        self.networkHandler.quit()
        self.uiThread.join()

    def getNodeAddress(self):
        try:
            for interface in netifaces.interfaces():
                addresses = netifaces.ifaddresses(interface).get(netifaces.AF_INET, [])
                for addr_info in addresses:
                    ipv4_address = addr_info.get('addr', '')
                    if ipv4_address.startswith('10.'):
                        print(f"Node hosted on: {ipv4_address}")
                        return ipv4_address
        except:
            pass

    def authLoadBalancer(self, command, extra):
        # Append the parameters to the circular list
        self.load_balancer_tasks.append((command, extra))
        # Call load_balancer_exe with the parameters from the circular list
        self.load_balancer_exe()

    def load_balancer_exe(self):
        with self.load_balancer_lock:
            # Check if the maximum number of concurrent tasks is reached
            if self.current_tasks >= self.max_concurrent_tasks:
                return

            if self.load_balancer_tasks:
                command, extra = self.load_balancer_tasks.popleft()

                # Execute the task in a separate thread
                threading.Thread(target=self.execute_task, args=(command, extra)).start()
                self.current_tasks += 1

    def execute_task(self, command, extra):
        global auth_microservice_count
        if command == "spwn":
            # Spawn microservice node command
            if auth_microservice_count == 0:
                time.sleep(2)
                self.spawnMicroservice()
        elif command == "check":
            # Check token command
            token = extra
            if self.find_token_in_file(token):
                print(f"Token '{token}' found in the file.")
                tokenReply = f"auth:cmd:token:0:{token}"
            else:
                print(f"Token '{token}' not found in the file.")
                tokenReply = f"auth:cmd:token:-1"
            self.connection.oBuffer.put(tokenReply)

        # Introduce a delay between tasks (adjust the sleep duration as needed)
        time.sleep(1)

        with self.load_balancer_lock:
            self.current_tasks -= 1

        # Continue with the next task
        self.load_balancer_exe()
        return

    def find_token_in_file(self, token_to_find):
        # If authentication node has client token savedS
        try:
            # Get the absolute path of the script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            user_data_file = os.path.join(script_dir, 'userData.txt')
            with open(user_data_file, 'r') as file:
                for line in file:
                    # Extract the 'Token:' value from the line
                    if 'Token: ' in line:
                        token_in_file = line.split('Token: ')[1].strip()

                        # Compare with the local variable
                        if token_in_file == token_to_find:
                            return True  # Token found in the file
            return False  # Token not found in the file
        except Exception as ex:
            print(ex)
            return False

    def spawnMicroservice(self):
        print("Spawn microservice")
        # Start Microservice
        try:
            msip = self.nodeIp
            msport = str(self.port + 1)
            DETACHED_PROCESS = 0x00000008
            auth_microservice_processes = subprocess.Popen(
                [
                    sys.executable,
                    "../authentication node/AuthMicroservice.py",
                    msip,
                    msport
                ],
                creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP
            ).pid
            message = "auth:cmd:spwnms:" + str(msip) +":"+ str(msport)
            if self.connection:
                self.connection.oBuffer.put(message)
        except:
            pass


class AuthFunctionalityHandler:
    def __init__(self, network):
        self.network = network
        self.running = True
        self.connections = []

    def add(self, connection):
        self.connections.append(connection)
        handler_thread = threading.Thread(target=self.process, args=(connection,))
        handler_thread.start()

    def process(self, connection=None):
        while self.running:
            if connection:
                #                Heartbeat update
                # ------------------------------------------------
                self.update_heartbeat(connection)

                # if not connection.iBuffer.empty():
                #     message = connection.iBuffer.get()
                #     if message:
                #         if message.startswith("ping"):
                #             connection.oBuffer.put("pong")
                #         else:
                #             connection.oBuffer.put(f"Echoing: {message}")
        self.network.quit()


if __name__ == "__main__":
    # Hardcoded bootstrap prime node - ip, port - CHANGE IP TO BOOSTRAP IP
    auth = abstractAuth("127.0.0.1", 50001)
    auth.process()
