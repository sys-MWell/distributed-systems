# All of the processing code has now been pulled into this file - the network code remains in the other file Abstract...
import time
from datetime import datetime
from AuthNetworkInterface import AuthNetworkInterface
import threading
import netifaces

class abstractAuth:
    def __init__(self, host="127.0.0.1", port=50000):
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
                    print(message)

    def process(self):
        # Start the UI thread and start the network components
        self.uiThread.start()
        self.connection = self.networkHandler.start_auth(self.host, self.port)

        while self.running:
            message = "auth"
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
                    return(link['addr'])
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
    auth = abstractAuth("127.0.0.1", 50001)
    auth.process()