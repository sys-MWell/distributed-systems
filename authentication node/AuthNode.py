# All of the processing code has now been pulled into this file - the network code remains in the other file Abstract...
import subprocess
import sys
import time
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

    # Simple UI thread
    def ui(self):
        # Handle incoming messages from the server - at the moment that is simply "display them to the user"
        while self.running:
            if self.connection:
                message = self.connection.iBuffer.get()
                if message:
                    # Break message loop
                    if message.startswith("cmd"):
                        parts = message.split(":")
                        if len(parts) >= 3 and parts[0] == "cmd":
                            print()
                            print(f"Command received from bootstrap")
                            if len(parts) >= 3:
                                after_node = parts[1]
                                if after_node == "spwn":
                                    after_node = parts[2]
                                    if after_node == "ms":
                                        print(f"Spawn micro-service command received")
                                        self.authLoadBalancer()

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
                for link in netifaces.ifaddresses(interface)[netifaces.AF_INET]:
                    print(f"Node hosted on: {link['addr']}")
                    return (link['addr'])
        except:
            pass

    def authLoadBalancer(self):
        global auth_microservice_count
        if auth_microservice_count == 0:
            time.sleep(2)
            self.spawnMicroservice()

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
