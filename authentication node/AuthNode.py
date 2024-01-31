# All of the processing code has now been pulled into this file - the network code remains in the other file Abstract...
import os
import subprocess
import sys
import time
from collections import deque
from datetime import datetime
from AuthNetworkInterface import AuthNetworkInterface
import threading
import os, re
import socket

auth_microservice_count = 0


class abstractAuth:
    def __init__(self, host="127.0.0.1", port=50001):
        self.host = host
        self.port = port
        self.usable_ports = 50001
        self.networkHandler = AuthNetworkInterface()
        self.connection = None
        self.uiThread = threading.Thread(target=self.ui)
        self.running = True
        self.connected_clients = 0
        self.localip = None
        self.localport = None

        print("Authentication Node Initiated")
        # Get IP of AUTH node
        self.nodeIp = self.getNodeAddress()
        print(f"Authentication Node Hosted on: {self.nodeIp}")

        # Load balancer
        self.load_balancer_tasks = deque()
        self.load_balancer_lock = threading.Lock()
        self.max_concurrent_tasks = 2
        self.current_tasks = 0

        # Terminate microservice functions
        self.spawned_microservices = {}  # Dictionary to keep track of each individual auth_microservice_processes

    # Simple UI thread
    def ui(self):
        # Handle incoming messages from the server - at the moment that is simply "display them to the user"
        while self.running:
            if self.connection:
                message = self.connection.iBuffer.get()
                if message:
                    print()
                    # Break message loop
                    if message.startswith("cmd"):
                        parts = message.split(":")
                        if len(parts) >= 3 and parts[0] == "cmd":
                            if len(parts) >= 3:
                                after_node = parts[1]
                                if after_node == "spwn":
                                    print(f"Command received from bootstrap")
                                    print(message)
                                    after_node = parts[2]
                                    if after_node == "ms":
                                        # Incoming command from bootstrap to spawn microservice
                                        print(f"Spawn micro-service command received")
                                        self.authLoadBalancer(parts[1], None)
                                    if after_node == "connection":
                                        # Local IP save
                                        print(f"Current node details: {parts[3]}:{parts[4]}")
                                        self.localip = parts[3]
                                        self.localport = parts[4]
                                if after_node == "check":
                                    # Bootstrap token confirmation
                                    if parts[2] == "token":
                                        print(f"Command received from bootstrap")
                                        print(message)
                                        # Check client token
                                        token = parts[3]
                                        print(f"Token received from bootstrap: {token}")
                                        self.authLoadBalancer(parts[1], token)
                                # Stats incoming from bootstrap
                                if after_node == "stats":
                                    print(f"Current microservice details: {parts[2]}:{parts[3]}\n"
                                          f"Connected clients: {parts[4]}")
                                # Incoming request to terminate microservice
                                if after_node == "terminate":
                                    print(f"Terminate microservice command received: \n"
                                          f"{parts[2]}:{parts[3]}")
                                    self.terminateMicroservice(parts[2], parts[3])

    def process(self):
        # Start the UI thread and start the network components
        self.uiThread.start()
        self.connection = self.networkHandler.start_auth(self.host, self.port)
        # Message bootstrap that authentication node spawned
        message = "auth:cmd:load:" + str(self.nodeIp) + ":" + str(self.usable_ports)
        self.usable_ports += 1
        self.connection.oBuffer.put(message)

        while self.running:
            if self.connection:
                message = input()

        # stop the network components and the UI thread
        self.networkHandler.quit()
        self.uiThread.join()

    def getNodeAddress(self):
        try:
            # Get local IP - needs IP starting with 10.x.x.x
            # Should return a list of all IP addresses - find one that starts 10. and isn't ended with .0 or .254
            addresses = os.popen(
                'IPCONFIG | FINDSTR /R "Ethernet adapter Local Area Connection .* Address.*[0-9][0-9]*\.[0-9]['
                '0-9]*\.[0-9][0-9]*\.[0-9][0-9]*"')
            ip_list = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', addresses.read())

            # Filter and sort the IP addresses
            filtered_ips = [ip for ip in ip_list if
                            ip.startswith('10.') and not ip.endswith('.0') and not ip.endswith('.254')]

            if filtered_ips:
                # Return host if found
                return filtered_ips[0]
            else:
                # Get local host
                host_name = socket.gethostname()
                # Get the local IP address by resolving the host name
                local_ip = socket.gethostbyname(host_name)
                return local_ip
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
            msport = str(self.usable_ports)
            self.usable_ports += 1
            # Spawn microservice as detached microservice, in separate console.
            DETACHED_PROCESS = 0x00000008
            try:
                auth_microservice_process = subprocess.Popen(
                    [
                        sys.executable,
                        "../authentication node/AuthMicroservice.py",
                        msip,
                        msport
                    ],
                    creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP
                )

                # Store information about the spawned microservice in the dictionary
                self.spawned_microservices[(msip, msport)] = {
                    'process': auth_microservice_process,
                    'localip': msip,
                    'localport': msport
                }
            except Exception as ee:
                print(f"Error :) {ee}")
            message = "auth:cmd:spwnms:" + str(msip) + ":" + str(msport) + ":" + str(self.localip) + ":" + str(
                self.localport)
            if self.connection:
                self.connection.oBuffer.put(message)
        except Exception as ex:
            print(f"Errors: {ex}")
            pass

    def terminateMicroservice(self, msip, msport):
        try:
            if (msip, msport) in self.spawned_microservices:
                # Retrieve the process and terminate it
                microservice_process = self.spawned_microservices[(msip, msport)]['process']
                # Use taskkill to forcefully terminate the process and its descendants
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(microservice_process.pid)],
                               check=True)
                print("Microservice terminated.")
                # Delete entry from dictionary
                del self.spawned_microservices[(msip, msport)]
                # Free port (as last microservice from dictionary it just removes last port)
                self.usable_ports -= 1
                # Reply to bootstrap
                terminateReply = f"auth:cmd:terminated:{msip}:{msport}"
                self.connection.oBuffer.put(terminateReply)
            else:
                print("No microservice process to terminate.")
        except subprocess.CalledProcessError as e:
            print(f"Error terminating microservice: {e}")


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
                pass
        self.network.quit()


if __name__ == "__main__":
    # Hardcoded bootstrap prime node - ip, port - CHANGE IP TO BOOSTRAP IP
    # auth = abstractAuth("127.0.0.1", 50001)
    auth = abstractAuth("127.0.0.1", 50001)
    auth.process()
