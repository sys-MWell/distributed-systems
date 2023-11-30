from ServerNetworkInterface import ServerNetworkInterface
import time
from datetime import datetime
import threading
from colorama import Fore, Back, Style
import os
import json


class FunctionalityHandler:
    def __init__(self, network):
        self.network = network
        self.running = True
        self.connections = []

    # Add new client connection - new thread for every client
    def add(self, connection, ip, port):
        self.connections.append(connection)
        handler_thread = threading.Thread(target=self.process, args=(ip, port, connection,))
        handler_thread.start()

    def update_heartbeat(self, connection, ip, port):
        duration = connection.time_since_last_message()
        self.ip = ip
        self.port = port

        # You should perform your disconnect / ping as appropriate here.
        if duration > 5:
            connection.update_time()
            connection.add_timeout()
            try:
                ip, port = connection.sock.getpeername()
                print(f"{Fore.BLUE}{datetime.now()}{Style.RESET_ALL} ", end="")
                print(
                    f"{Fore.RED}The last message from {Fore.GREEN}{ip}:{port}{Fore.RED} sent more than 5 seconds ago, {connection.get_timeouts()} have occurred{Style.RESET_ALL}")
            except OSError as e:
                if e.errno == 10038:  # WinError 10038: An operation was attempted on something that is not a socket
                    # Handle the error gracefully
                    print(f"{Fore.RED}Connection closed {self.ip}:{self.port} disconnected...{Style.RESET_ALL}", end="")
                    self.connections.remove(connection)
                    print()
                    exit()

    def process(self, ip, port, connection=None):
        while self.running:
            if connection:
                #                Heartbeat update
                # ------------------------------------------------
                self.update_heartbeat(connection, ip, port)

                # Commands from nodes
                try:
                    if not connection.iBuffer.empty():
                        message = connection.iBuffer.get()
                        if message:
                            if message.startswith("ping"):
                                connection.oBuffer.put("pong")

                            ### CLIENT NODE
                            # User contextual menu input
                            if message.startswith("conOptCom"):
                                print(f"{Fore.YELLOW}Received contextual menu input from: "
                                      f"{Fore.GREEN}{ip}:{port} {Fore.YELLOW}message being {message} {Style.RESET_ALL}", end="")
                                print()
                            ### AUTH NODE
                            if message.startswith("auth"):
                                print(f"{Fore.RED}AUTHENTICATION NODE DETECTED{Style.RESET_ALL}", end="")
                                print()
                                connection.oBuffer.put("pong")
                                name = "auth"
                                self.handle_functional_nodes(connection, name, ip, port)
                            else:
                                connection.oBuffer.put(f"Echoing: {message}")

                except ConnectionResetError:
                    # Handle client node disconnect gracefully
                    self.connections.remove(connection)
                    break
        self.network.quit()

    def handle_functional_nodes(self, connection, name, ip, port):
        condition = connection.add_node_to_json(name, ip, port)
        if condition:
            print(f"{Fore.GREEN}Auth {ip}:{port} {Fore.YELLOW}saved successfully {Style.RESET_ALL}", end="")
        else:
            print(f"{Fore.RED}Auth {ip}:{port} {Fore.YELLOW}saved unsuccessfully {Style.RESET_ALL}", end="")
        print()

class AbstractServer:
    def __init__(self, host="127.0.0.1", port=50000):
        self.networkHandler = ServerNetworkInterface()
        self.functionalityHandler = FunctionalityHandler(self.networkHandler)
        self.host = host
        self.port = port

    def client_handler(self, clientConnection):
        self.functionalityHandler.add(clientConnection, self.host, self.port)

    def process(self):
        self.create_or_replace_json()
        # Handle connection to server process
        self.networkHandler.start_server(self.host, self.port, self.client_handler)
        # while True:
        #     clients = self.networkHandler.get_clients()
        #     if len(clients) > 0:
        #         print(f"{Fore.BLUE}{datetime.now()}{Style.RESET_ALL}")
        #         for client in clients:
        #             ip, port = client.sock.getpeername()
        #             print(f"{Fore.YELLOW}{ip}:{port} {Style.RESET_ALL}", end="")
        #         print()
        #     time.sleep(2)

    def create_or_replace_json(self, filename='nodes.json'):
        # If JSON file exists remove and replace with fresh one
        if os.path.exists(filename):
            os.remove(filename)
        with open(filename, 'w') as file:
            # If it doesn't, create a new JSON object
            data = {"connections": []}
            json.dump(data, file, indent=2)

if __name__ == "__main__":
    # Hardcoded bootstrap prime node - ip, port - CHANGE IP TO BOOSTRAP IP
    server = AbstractServer("127.0.0.1", 50005)
    server.process()
