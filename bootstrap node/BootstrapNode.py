from ServerNetworkInterface import ServerNetworkInterface
import time
from datetime import datetime
import threading
import queue
import subprocess
import os
import json

MAX_AUTH_NODES = 4  # Maximum number of authentication nodes
connected_clients = 0
content_node = 0
content_nodes = []  # List to keep track of content nodes
auth_nodes = []  # List to keep track of authentication nodes
auth_ms_nodes = []  # List to keep track of authentication microservice nodes
filedist_ms_nodes = []  # List to keep track of file distribution microservice nodes
client_tokens = []


class ContentNodes:
    def __init__(self, contentNumber, connection, ip, port, functionalNodeType):
        self.contentNumber = contentNumber
        self.connection = connection
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
    def __init__(self, nodeNumber, nodeType, connection, ip, port):
        self.nodeNumber = nodeNumber
        self.nodeType = nodeType
        self.connection = connection
        self.ip = ip
        self.port = port

    def display_info(self):
        """
        Display information about Nodes instance.
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
        # What user main menu inputted
        self.client_main_menu_input = ''

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
                        global client_tokens
                        if message:
                            ip, port = connection.sock.getpeername()
                            if message.startswith("ping"):
                                connection.oBuffer.put("pong")

                            ### CLIENT NODE
                            elif message.startswith("client"):
                                cmdparts = message.split(":")
                                if len(cmdparts) >= 3:
                                    if cmdparts[1] == "cmd":
                                        # print("\n")
                                        if cmdparts[2] == "context":
                                            # Context menu selection
                                            print(f"Received contextual menu input from: "
                                                  f"{ip}:{port} message being {message} ", end="")
                                            command_value = cmdparts[3]
                                            if command_value == '1' or command_value == '2':
                                                # Client requires authentication node
                                                if len(auth_ms_nodes) < 1:
                                                    # No auth microservices available
                                                    # Get bootstrap to spawn one idk
                                                    connection.oBuffer.put(f"bootstrap:cmd:auth:-1")
                                                elif len(auth_ms_nodes) >= 1:
                                                    # Auth microservice available
                                                    self.load_balancer("authentication", connection
                                                                       , ip, port, None)
                                            else:
                                                connection.oBuffer.put(f"bootstrap:cmd:auth:-1")
                                        elif cmdparts[2] == "fdn":
                                            # Client requests FDN details
                                            token_found = False
                                            print()
                                            print(f"Received FDN request from: "
                                                  f"{ip}:{port} message being {message} ", end="")
                                            # compare token with that stored in authentication node
                                            # First check if bootstrap already stores authentication token
                                            search_token = cmdparts[3]
                                            for index, token in enumerate(client_tokens):
                                                if token == search_token:
                                                    print(f"{search_token} found at index {index}.")
                                                    token_found = True
                                                    break
                                            if token_found:
                                                print()
                                                print("Token found locally")
                                            else:
                                                # Check with authentication node
                                                print()
                                                print("Token not found locally")
                                                self.load_balancer("authTokenCfirm", connection
                                                                   , ip, port, search_token)
                                        else:
                                            print("Invalid command")

                            ### AUTH NODE
                            elif message.startswith("auth"):
                                print()
                                cmdparts = message.split(":")
                                if len(cmdparts) >= 3:
                                    if cmdparts[1] == "cmd":
                                        print("Received auth node command")
                                        if cmdparts[2] == "load":
                                            print(f"New authentication node connection establishing...", end="")
                                            print()
                                            name = "auth"
                                            self.handle_functional_nodes(connection, name, ip, port)
                                            global auth_nodes
                                            # Bootstrap save auth node
                                            auth_nodes.append(Nodes(len(auth_nodes) + 1, "auth_" +
                                                                    str(len(auth_ms_nodes) + 1), connection, ip, port))
                                            connection.oBuffer.put("cmd:spwn:ms")
                                        elif cmdparts[2] == "spwnms":
                                            print("Received micro-service details")
                                            ip = cmdparts[3]
                                            port = cmdparts[4]
                                            name = "auth-ms"
                                            self.handle_functional_nodes(connection, name, ip, port)
                                            auth_ms_nodes.append(Nodes(len(auth_ms_nodes) + 1, "auth_ms_" +
                                                                       str(len(auth_ms_nodes) + 1),
                                                                       None, ip, port))
                                        elif cmdparts[2] == "token":
                                            print(message)
                                            status = cmdparts[3]
                                            token = cmdparts[4]
                                            if status == "0":
                                                # Success, token confirmed
                                                print("Valid token")
                                                client_tokens.append(token)
                                                # Now need to send FDN details to client
                                            else:
                                                # Failure, token not confirmed
                                                print("Invalid token")
                                                connection.oBuffer.put(f"bootstrap:cmd:token:-1")

                            ### CONTENT NODE
                            elif message.startswith("content"):
                                cmdparts = message.split(":")
                                if len(cmdparts) >= 3:
                                    if cmdparts[1] == "cmd":
                                        if cmdparts[2] == "spawn":
                                            print()
                                            print(f"Content node connected")
                                            name = "content"
                                            self.load_balancer("content", connection, ip, port, None)
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

    def load_balancer(self, command, connection, ip, port, extra):
        global content_node
        global content_nodes
        if command == "content":
            # If no content nodes available, this first connected node will be authentication
            if content_node == 0:
                print(f"Currently no content nodes available - establishing connection to first "
                      f"content node")
                content_node += 1
                content_node_type = ContentNodes(content_node, connection, ip, port, "authentication")
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
                        content_node_type = ContentNodes(content_node, connection, port, "filedistribution")
                        print(f"Assigning content node {content_node} to file distribution node")
                        connection.oBuffer.put("cmd:node:fdn")
                        content_nodes.append(content_node_type)
                        content_node_type.display_info()

        elif command == 'authTokenCfirm':
            global auth_nodes
            # Send command to authentication node to check client token
            if 0 < len(auth_nodes) <= 1:
                auth_node = auth_nodes[0]
                auth_connection = auth_node.connection
                token = extra
                auth_connection.oBuffer.put(f"cmd:check:token:{token}")

        elif command == "authentication":
            # Send command to client with authentication microservice ip and port
            print("auth")
            if content_node < 5:
                print("less than 5 connected clients")
                microservice = auth_ms_nodes[0]
                name = "auth-ms"
                ms_connection = f"0:{name}:{microservice.ip}:{microservice.port}"
                connection.oBuffer.put(f"bootstrap:cmd:auth:0:{ms_connection}")

            if connected_clients >= 5:
                print("more than 5 connected clients")


        elif command == "filedistribution":
            print("fdn")

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
        global connected_clients
        connected_clients += 1
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
