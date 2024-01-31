# All of the processing code has now been pulled into this file - the network code remains in the other file Abstract...
import time
from datetime import datetime
from ContentNetworkInterface import ContentNetworkInterface
import threading
import sys
import subprocess
import os, re
import socket

nodePort = 50000


class abstractContent:
    def __init__(self, host="127.0.0.1", port=50000):
        self.host = host
        self.port = port
        self.networkHandler = ContentNetworkInterface()
        self.connection = None
        self.uiThread = threading.Thread(target=self.ui)
        self.running = True

        # Get IP of CONTENT node
        self.nodeIp = self.getNodeAddress()
        print(f"Content Node hosted on: {self.nodeIp}")

    # Simple UI thread
    def ui(self):
        # Handle incoming messages from the server - at the moment that is simply "display them to the user"
        while self.running:
            if self.connection:
                message = self.connection.iBuffer.get()
                if message:
                    if message.startswith("cmd"):
                        print()
                        print("Command received from bootstrap node")
                        # Split the command using ":" as the delimiter
                        parts = message.split(":")
                        if len(parts) >= 3 and parts[0] == "cmd":
                            print(f"Spawn node command received from bootstrap")
                            if len(parts) >= 3:
                                after_node = parts[2]
                                print(f"Extracted node type: {after_node}")
                                # Spawn detached processes as separate console
                                if after_node == "auth":
                                    # Authentication
                                    print("Spawning authentication node")
                                    DETACHED_PROCESS = 0x00000008
                                    pid = subprocess.Popen([sys.executable, "../authentication node/AuthNode.py"],
                                                           creationflags=subprocess.CREATE_NEW_CONSOLE |
                                                                         subprocess.CREATE_NEW_PROCESS_GROUP).pid

                                if after_node == "fdn":
                                    # File distribution
                                    print("Spawning file distribution node")
                                    DETACHED_PROCESS = 0x00000008
                                    pid = subprocess.Popen([sys.executable, "../file distribution node/FDNNode.py"],
                                                           creationflags=subprocess.CREATE_NEW_CONSOLE |
                                                                         subprocess.CREATE_NEW_PROCESS_GROUP).pid
                            else:
                                print("Invalid command format.")
                        else:
                            print("Invalid command format.")

    def process(self):
        # Start the UI thread and start the network components
        global nodePort
        self.uiThread.start()
        self.connection = self.networkHandler.start_content(self.host, self.port)

        while self.running:
            # Send message to bootstrap that content node has been spawned.
            message = "content:cmd:spawn:" + str(self.nodeIp) + ":" + str(self.port)
            if self.connection:
                self.connection.oBuffer.put(message)
                message = input()

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
                # Return host
                return filtered_ips[0]
            else:
                # Return local host
                host_name = socket.gethostname()
                # Get the local IP address by resolving the host name
                local_ip = socket.gethostbyname(host_name)
                return local_ip
        except:
            pass


class ContentFunctionalityHandler:
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
                pass
        self.network.quit()


if __name__ == "__main__":
    # Hardcoded bootstrap prime node - ip, port - CHANGE IP TO BOOSTRAP IP
    content = abstractContent("127.0.0.1", 50001)
    content.process()
