# All of the processing code has now been pulled into this file - the network code remains in the other file Abstract...
import subprocess
import sys
import time
from collections import deque
from datetime import datetime
from FDNNetworkInterface import FDNNetworkInterface
import threading
import netifaces

fdn_microservice_count = 0
nodePort = 50001

class abstractFDN:
    def __init__(self, host="127.0.0.1", port=50000):
        self.host = host
        self.port = port
        self.networkHandler = FDNNetworkInterface()
        self.connection = None
        self.uiThread = threading.Thread(target=self.ui)
        self.running = True
        print("File Distribution Node Initiated")
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
                                        self.fdnLoadBalancer(parts[1], None)

    def process(self):
        # Start the UI thread and start the network components
        self.uiThread.start()
        self.connection = self.networkHandler.start_FDN(self.host, self.port)

        while self.running:
            global nodePort
            message = "fdn:cmd:load:" + str(self.nodeIp) +":"+ str(nodePort)
            nodePort ++ 1
            if self.connection:
                self.connection.oBuffer.put(message)
                message = input()

        # stop the network components and the UI thread
        self.networkHandler.quit()

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

    def fdnLoadBalancer(self, command, extra):
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
        global fdn_microservice_count
        if command == "spwn":
            # Spawn microservice node command
            if fdn_microservice_count == 0:
                time.sleep(2)
                self.spawnMicroservice()

    def spawnMicroservice(self):
        print("Spawn fdn microservice")
        # Start Microservice
        try:
            msip = self.nodeIp
            msport = str(self.port + 2)
            DETACHED_PROCESS = 0x00000008
            fdn_microservice_processes = subprocess.Popen(
                [
                    sys.executable,
                    "../file distribution node/FDNMicroservice.py",
                    msip,
                    msport
                ],
                creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP
            ).pid
            message = "fdn:cmd:spwnms:" + str(msip) + ":" + str(msport)
            if self.connection:
                self.connection.oBuffer.put(message)
        except:
            pass


class FDNFunctionalityHandler:
    def __init__(self, network):
        self.network = network
        self.running = True
        self.connections = []

    def add(self, connection):
        self.connections.append(connection)
        handler_thread = threading.Thread(target=self.process, args=(connection,))
        handler_thread.start()

    def update_heartbeat(self, connection):
        duration = connection.time_since_last_message()

        # You should perform your disconnect / ping as appropriate here.
        if duration > 5:
            connection.update_time()
            connection.add_timeout()
            ip, port = connection.sock.getpeername()
            print(f"{datetime.now()} ", end="")
            print(
                f"The last message from {ip}:{port} sent more than 5 seconds ago, {connection.get_timeouts()} have occurred")

    def process(self, connection=None):
        while self.running:
            if connection:
                #                Heartbeat update
                # ------------------------------------------------
                self.update_heartbeat(connection)

                if not connection.iBuffer.empty():
                    message = connection.iBuffer.get()
                    if message:
                        if message.startswith("ping"):
                            connection.oBuffer.put("pong")
                        else:
                            connection.oBuffer.put(f"Echoing: {message}")
        self.network.quit()

if __name__ == "__main__":
    # Hardcoded bootstrap prime node - ip, port - CHANGE IP TO BOOSTRAP IP
    FDN = abstractFDN("127.0.0.1", 50001)
    FDN.process()