from ServerNetworkInterface import ServerNetworkInterface
import time
from datetime import datetime
import threading
import queue
import subprocess
import os
import json

MAX_AUTH_NODES = 4  # Maximum number of authentication nodes
content_node = 0
content_nodes = []  # List to keep track of content nodes
auth_ms_nodes = []  # List to keep track of authentication node processes
filedist_nodes = []  # List to keep track of file distribution node processes


class ContentNodes:
    def __init__(self, contentNumber, ip, port, functionalNodeType):
        self.contentNumber = contentNumber
        self.ip = ip
        self.port = port
        self.functionalNodes = functionalNodeType

    def display_info(self):
        """
        Display information about the ContentNodes instance.
        """
        print(f"Content Number: {self.contentNumber}")
        print(f"IP Address: {self.ip}")
        print(f"Port Number: {self.port}")
        print(f"Functional: {self.functionalNodes}")

class Nodes:
    def __init__(self, nodeNumber, nodeType, ip, port):
        self.nodeNumber = nodeNumber
        self.nodeType = nodeType
        self.ip = ip
        self.port = port

    def display_info(self):
        """
        Display information about the ContentNodes instance.
        """
        print(f"Content Number: {self.nodeNumber}")
        print(f"Node type: {self.nodeType}")
        print(f"IP Address: {self.ip}")
        print(f"Port Number: {self.port}")

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
        if duration > 15:
            connection.update_time()
            connection.add_timeout()
            try:
                ip, port = connection.sock.getpeername()
                # print(f"{datetime.now()} ", end="")
                # print(
                #     f"The last message from {ip}:{port} sent more than 15 seconds ago, "
                #     f"{connection.get_timeouts()} have occurred")
            except OSError as e:
                if e.errno == 10038:  # WinError 10038: An operation was attempted on something that is not a socket
                    # Handle the error gracefully
                    print(f"Connection closed {self.ip}:{self.port} disconnected...", end="")
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
                    global content_nodes
                    if not connection.iBuffer.empty():
                        message = connection.iBuffer.get()
                        if message:
                            ip, port = connection.sock.getpeername()
                            if message.startswith("ping"):
                                connection.oBuffer.put("pong")

                            ### CLIENT NODE
                            elif message.startswith("client"):
                                cmdparts = message.split(":")
                                if len(cmdparts) >= 3:
                                    if cmdparts[1] == "cmd":
                                        print("\n")
                                        if cmdparts[2] == "context":
                                            # Context menu selection
                                            print(f"Received contextual menu input from: "
                                                  f"{ip}:{port} message being {message} ", end="")
                                            command_value = cmdparts[3]
                                            if command_value == '0' or command_value == '1':
                                                # Client requires authentication node
                                                if len(auth_ms_nodes) < 1:
                                                    # No auth microservices available
                                                    # Get bootstrap to spawn one idk
                                                    connection.oBuffer.put(f"bootstrap:cmd:auth:-1")
                                            else:
                                                connection.oBuffer.put(f"bootstrap:cmd:auth:-1")
                                #client:cmd:context:

                            ### AUTH NODE
                            elif message.startswith("auth"):
                                print()
                                cmdparts = message.split(":")
                                if len(cmdparts) >= 3:
                                    if cmdparts[1] == "cmd":
                                        print("Received auth node command")
                                        if cmdparts[2] == "load":
                                            print(f"AUTHENTICATION NODE DETECTED", end="")
                                            print()
                                            name = "auth"
                                            self.handle_functional_nodes(connection, name, ip, port)
                                            connection.oBuffer.put("cmd:spwn:ms")
                                        elif cmdparts[2] == "spwnms":
                                            print("Received micro-service details")
                                            ip = cmdparts[3]
                                            port = cmdparts[4]
                                            name = "auth-ms"
                                            self.handle_functional_nodes(connection, name, ip, port)
                                            auth_ms_nodes.append(Nodes(len(auth_ms_nodes)+1, "auth_ms_"+
                                                                       str(len(auth_ms_nodes)+1), ip, port))

                            ### CONTENT NODE
                            elif message.startswith("content"):
                                cmdparts = message.split(":")
                                if len(cmdparts) >= 3:
                                    if cmdparts[1] == "cmd":
                                        if cmdparts[2] == "spawn":
                                            print()
                                            print(f"Content node connected")
                                            name = "content"
                                            self.load_balancer("content", connection, ip, port)
                                            self.handle_functional_nodes(connection, name, ip, port)
                                        else:
                                            print("1")
                                    else:
                                        print("2")
                                else:
                                    print("3")
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
            print(f"{name} node: {ip}:{port} saved successfully ", end="")
        else:
            print(f"{name} node {ip}:{port} saved unsuccessfully ", end="")
        print()

    def load_balancer(self, node, connection, ip, port):
        if node == "content":
            global content_node
            global content_nodes
            # If no content nodes available, this first connected node will be authentication
            if content_node == 0:
                print(f"Currently no content nodes available - establishing connection to first "
                      f"content node")
                content_node += 1
                content_node_type = ContentNodes(content_node, ip, port, "authentication")
                print("Assigning first content node to authentication node")
                connection.oBuffer.put("cmd:node:auth")
                content_nodes.append(content_node_type)
                content_node_type.display_info()
            # If more then one content_node connected
            elif content_node >= 1:
                count_authentication = 0
                count_filedistribution = 0
                for nodes in content_nodes:
                    if "authentication" in nodes.functionalNodes:
                        count_authentication += 1
                    if "filedistribution" in nodes.functionalNodes:
                        count_filedistribution += 1
                print(count_authentication)
                print(count_filedistribution)

                # 1 or more authentication nodes connected
                if count_authentication >= 1:
                    # If 0 file distribution nodes connected
                    if count_filedistribution == 0:
                        content_node += 1
                        content_node_type = ContentNodes(content_node, ip, port, "filedistribution")
                        print(f"Assigning content node {content_node} to file distribution node")
                        connection.oBuffer.put("cmd:node:fdn")
                        content_nodes.append(content_node_type)
                        content_node_type.display_info()

    def read_json_file(self):
        with open('nodes.json', 'r') as file:
            data = json.load(file)
            connections = data.get('connections', [])

            for connection in connections:
                if connection.get('connection_type') == 'auth':
                    ip = connection.get('ip')
                    port = connection.get('port')
                    return ip, port

        # If no "auth" connection is found, return None values
        return None, None


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
    server = AbstractServer("127.0.0.1", 50001)
    server.process()
