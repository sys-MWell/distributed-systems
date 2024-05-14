from collections import deque
from ServerNetworkInterface import ServerNetworkInterface
import time
from datetime import datetime
import threading
import queue
import subprocess
import os
import json

connected_clients = 0
content_node = 0
content_nodes = []      # List to keep track of content nodes
auth_nodes = []         # List to keep track of authentication nodes
auth_ms_nodes = []      # List to keep track of authentication microservice nodes
fd_nodes = []
fd_ms_nodes = []        # List to keep track of file distribution microservice nodes
client_tokens = []      # List of connected client tokens
clients = []            # List of connected clients


class ContentNodes:
    def __init__(self, connection, ip, port, functionalNodeType):
        self.connection = connection
        self.ip = ip
        self.port = port
        self.functionalNodes = functionalNodeType

    def display_info(self):
        """
        Display information about the ContentNodes instance.
        """
        print(f"IP Address: {self.ip}")
        print(f"Port Number: {self.port}")
        print(f"Functional: {self.functionalNodes}")


class Clients:
    def __init__(self, connection, ip, port):
        self.connection = connection
        self.ip = ip
        self.port = port

    def display_info(self):
        """
        Display information about Nodes instance.
        """
        print(f"IP Address: {self.ip}")
        print(f"Port Number: {self.port}")


class Nodes:
    def __init__(self, nodeNumber, nodeType, connection, ip, port, hostip, hostport):
        self.nodeNumber = nodeNumber
        self.nodeType = nodeType
        self.connection = connection
        self.ip = ip
        self.port = port
        self.hostIp = hostip
        self.hostPort = hostport
        self.connectedMS = []
        self.connectedClients = []

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
        self.clientConnection = None
        # Load balancer requirements
        self.load_balancer_tasks = deque()
        self.load_balancer_lock = threading.Lock()
        self.max_concurrent_tasks = 4
        self.current_tasks = 0
        self.client_limit = 2

        # Create a threading.Event - Used to signal terminate microservice
        self.terminate_countdown_flag_auth = False
        self.terminate_countdown_flag_fdn = False

        # Thread for stats - Ensure running in background separately, doesn't interfere with other processes
        thread = threading.Thread(target=self.check_variable_periodically)
        thread.start()

    # Add new client connection - new thread for every client
    def add(self, connection, ip, port):
        self.connections.append(connection)
        handler_thread = threading.Thread(target=self.process, args=(ip, port, connection,))
        handler_thread.start()

    # Function to run in a separate thread
    def check_variable_periodically(self):
        while True:
            global clients
            global content_nodes

            # Check arrays have nodes available
            if all(not array for array in
                   [content_nodes, auth_nodes, auth_ms_nodes, fd_nodes, fd_ms_nodes, client_tokens, clients]):
                print(f"No connected nodes detected...")
                pass
            else:
                print()
                print(f"Stats: \n"
                      f"Connected clients: {len(clients)}\n"
                      f"Connected Content nodes: {len(content_nodes)}")
                # Content node stats
                for index, content in enumerate(content_nodes):
                    print(f"Content node: {index + 1}\n"
                          f"    {content.ip}:{content.port}\n"
                          f"    sub: {content.functionalNodes}")
                # Authentication node stats
                for index, auth in enumerate(auth_nodes):
                    print(f"Authentication node: {index + 1} - {auth.ip}:{auth.port}")
                # File distribution stats
                for index, fdn in enumerate(fd_nodes):
                    print(f"File distribution node: {index + 1} - {fdn.ip}:{fdn.port}")
                # Authentication microservice stats
                for index, auth_ms in enumerate(auth_ms_nodes):
                    print(f"Authentication microservice: {index + 1}\n"
                          f"    Node: {auth_ms.ip}:{auth_ms.port}\n"
                          f"    Host node: {auth_ms.hostIp}:{auth_ms.hostPort}\n"
                          f"    Connected clients: {len(auth_ms.connectedClients)}")
                    for auth in auth_nodes:
                        # Ensure it targets correct authentication node with corresponding microservice
                        if f"{auth.ip}:{auth.port}" == f"{auth_ms.hostIp}:{auth_ms.hostPort}":
                            auth_connection = auth.connection
                            auth_connection.oBuffer.put(f"cmd:stats:"
                                                        f"{auth_ms.ip}:{auth_ms.port}:{len(auth_ms.connectedClients)}")
                    # Check node client count, if 0 clients run terminate countdown cycle
                    if len(auth_ms_nodes) > 1:
                        # Check if it's the last element - last microservice
                        if index == len(auth_ms_nodes) - 1:
                            if len(auth_ms.connectedClients) == 0:
                                # Check terminate countdown isn't already happening
                                if self.terminate_countdown_flag_auth:
                                    pass
                                else:
                                    print(f"Terminate countdown initialising for auth ms: {auth_ms.ip}:{auth_ms.port}")
                                    for auth in auth_nodes:
                                        # Ensure it targets correct authentication node with corresponding microservice
                                        if f"{auth.ip}:{auth.port}" == f"{auth_ms.hostIp}:{auth_ms.hostPort}":
                                            # Parent node connection target
                                            auth_parent = auth.connection
                                            # Start countdown terminate thread
                                            if not self.terminate_countdown_flag_auth:
                                                # Terminate thread
                                                self.terminate_countdown_thread = threading.Thread(
                                                    target=self.run_terminate_countdown, daemon=True,
                                                    args=('auth', auth_ms, auth_parent,))
                                                # Start terminate thread countdown
                                                self.terminate_countdown_thread.start()
                # File distribution microservice stats
                for index, fdn_ms in enumerate(fd_ms_nodes):
                    print(f"File distribution microservice: {index + 1}\n"
                          f"    Node: {fdn_ms.ip}:{fdn_ms.port}\n"
                          f"    Host node: {fdn_ms.hostIp}:{fdn_ms.hostPort}\n"
                          f"    Connected clients: {len(fdn_ms.connectedClients)}")
                    for fdn in fd_nodes:
                        # Ensure it targets correct file distribution node with corresponding microservice
                        if f"{fdn.ip}:{fdn.port}" == f"{fdn_ms.hostIp}:{fdn_ms.hostPort}":
                            fdn_connection = fdn.connection
                            fdn_connection.oBuffer.put(f"cmd:stats:"
                                                       f"{fdn_ms.ip}:{fdn_ms.port}:{len(fdn_ms.connectedClients)}")
                    # Check node client count, if 0 clients run terminate countdown cycle
                    if len(fd_ms_nodes) > 1:
                        # Check if it's the last element - last microservice
                        if index == len(fd_ms_nodes) - 1:
                            if len(fdn_ms.connectedClients) == 0:
                                if self.terminate_countdown_flag_fdn:
                                    pass
                                else:
                                    print(f"Terminate countdown initialising for fdn ms: {fdn_ms.ip}:{fdn_ms.port}")
                                    for fdn in fd_nodes:
                                        # Ensure it targets correct file distribution node with corresponding microservice
                                        if f"{fdn.ip}:{fdn.port}" == f"{fdn_ms.hostIp}:{fdn_ms.hostPort}":
                                            # Parent node connection target
                                            fdn_parent = fdn.connection
                                            # Start countdown terminate thread
                                            if not self.terminate_countdown_flag_fdn:
                                                # Terminate thread
                                                self.terminate_countdown_thread = threading.Thread(
                                                    target=self.run_terminate_countdown, daemon=True,
                                                    args=('fdn', fdn_ms, fdn_parent,))
                                                # Start terminate thread countdown
                                                self.terminate_countdown_thread.start()
                pass
            time.sleep(15)

    def run_terminate_countdown(self, node_type, node_ms, node_parent):
        if node_type == 'auth':
            self.terminate_countdown_flag_auth = True
        elif node_type == 'fdn':
            self.terminate_countdown_flag_fdn = True
        # Double check no clients have suddenly connected
        if len(node_ms.connectedClients) == 0:
            print(f"Terminate countdown start: {node_ms.ip}:{node_ms.port}")
            print()
            # Count, wait allocated time
            time.sleep(60)
            # Final check if no clients have suddenly connected during countdown
            if len(node_ms.connectedClients) == 0:
                # Begin microservice terminate - time to contact functional node
                print("Terminate countdown reached, requesting microservice termination")
                node_parent.oBuffer.put(f"cmd:terminate:{node_ms.ip}:{node_ms.port}")
                if node_type == 'auth':
                    self.terminate_countdown_flag_auth = False
                elif node_type == 'fdn':
                    self.terminate_countdown_flag_fdn = False
            else:
                # Countdown aborted clients connected
                print(f"Terminate countdown aborted: {node_ms.ip}:{node_ms.port}")
                if node_type == 'auth':
                    self.terminate_countdown_flag_auth = False
                elif node_type == 'fdn':
                    self.terminate_countdown_flag_fdn = False
        else:
            # Countdown aborted clients connected
            print(f"Terminate countdown aborted: {node_ms.ip}:{node_ms.port}")
            if node_type == 'auth':
                self.terminate_countdown_flag_auth = False
            elif node_type == 'fdn':
                self.terminate_countdown_flag_fdn = False

    def update_heartbeat(self, connection, ip, port):
        duration = connection.time_since_last_message()
        self.ip = ip
        self.port = port
        # You should perform your disconnect / ping as appropriate here.
        if duration > 5:
            connection.update_time()
            connection.add_timeout()
            try:
                # Ensure connection can still be established
                ip, port = connection.sock.getpeername()
            except OSError as e:
                # When connection no longer established
                if e.errno == 10038:  # WinError 10038: An operation was attempted on something that is not a socket
                    # Handle the error gracefully, disconnect
                    print()
                    print(f"Connection closed {ip}:{port} disconnected...", end="")
                    self.find_connection(connection, ip, port) # Remove nodes from arrays
                    self.connections.remove(connection)
                    print()
                    exit()

    def find_connection(self, connection, ip, port):
        # Find connections to disconnect, delete nodes from saved lists
        global clients
        global connected_clients
        global content_node
        global content_nodes
        global auth_nodes
        global fd_nodes

        # Find client that has disconnected
        for client in clients:
            if (
                    client.connection == connection
                    and client.ip == ip
                    and client.port == port
            ):
                print()
                print(f"Client disconnected: {ip}:{port}, details deleted...")

                # Check with microservice client was connected to and remove it
                for auth_node in auth_ms_nodes:
                    # Check the connectedClients array for the condition
                    for client_connection in auth_node.connectedClients:
                        if client_connection == connection:
                            print(
                                f"Client removed from Authentication Microservice connection")
                            auth_node.connectedClients.remove(client_connection)
                for fd_node in fd_ms_nodes:
                    # Check the connectedClients array for the condition
                    for client_connection in fd_node.connectedClients:
                        if client_connection == connection:
                            print(
                                f"Client removed from File Distribution Microservice connection")
                            fd_node.connectedClients.remove(client_connection)

                connected_clients -= 1
                clients.remove(client)

        # Find content node that disconnected
        for content in content_nodes:
            if (
                    content.connection == connection
                    and content.ip == ip
                    and content.port == port
            ):
                print()
                print(f"Content node disconnected: {ip}:{port}, details deleted...")
                content_nodes.remove(content)
                content_node -= 1

        # Find authentication node that disconnected
        for auth in auth_nodes:
            if (
                    auth.connection == connection
            ):
                print()
                print(f"Authentication node disconnected: {ip}:{port}, details deleted...")
                auth_nodes.remove(auth)

        # Find file distribution node that disconnected
        for fdn in fd_nodes:
            if (
                    fdn.connection == connection
            ):
                print()
                print(f"File distribution node disconnected: {ip}:{port}, details deleted...")
                fd_nodes.remove(fdn)

    def process(self, ip, port, connection=None):
        self.connected_client = None
        while self.running:
            global connected_clients
            if connection:
                #                Heartbeat update
                # ------------------------------------------------
                self.update_heartbeat(connection, ip, port)
                # Commands from nodes
                try:
                    global content_nodes
                    global clients
                    if not connection.iBuffer.empty():
                        message = connection.iBuffer.get()
                        global client_tokens
                        if message:
                            # Global variables
                            # Client token array
                            global client_tokens
                            global clients
                            # File distribution microservice node list
                            global fd_ms_nodes
                            ip, port = connection.sock.getpeername()
                            if message.startswith("ping"):
                                connection.oBuffer.put("pong")
                            elif message.startswith("quit"):
                                # Handle the disconnect gracefully
                                print(f"Connection closed {self.ip}:{self.port} disconnected...", end="")
                                # Disconnect - find in arrays
                                self.find_connection(connection, ip, port)
                                self.connections.remove(connection)
                                print()
                                exit()
                            ### CLIENT NODE INCOMING COMMANDS
                            elif message.startswith("client"):
                                # Split commands
                                cmdparts = message.split(":")
                                if len(cmdparts) >= 3:
                                    if cmdparts[1] == "cmd":
                                        # print("\n")
                                        if cmdparts[2] == "context":
                                            # Context menu selection
                                            print(f"Received contextual menu input from: "
                                                  f"{ip}:{port} message being {message} \n", end="")
                                            command_value = cmdparts[3]
                                            if command_value == '1' or command_value == '2':
                                                # Append to client count
                                                connected_clients += 1
                                                # Client requires authentication node
                                                if len(auth_ms_nodes) < 1:
                                                    # No auth microservices available
                                                    # Get bootstrap to spawn one
                                                    connection.oBuffer.put(f"bootstrap:cmd:auth:-1")
                                                elif len(auth_ms_nodes) >= 1:
                                                    # Auth microservice available
                                                    # Store connected client connection
                                                    self.connected_client = connection
                                                    self.load_balancer("authentication", connection
                                                                       , ip, port, connection)
                                            else:
                                                connection.oBuffer.put(f"bootstrap:cmd:auth:-1")
                                        elif cmdparts[2] == "fdn":
                                            # Client requests FDN details
                                            token_found = False
                                            print()
                                            print(f"Received FDN request from client: "
                                                  f"{ip}:{port} message being {message} ", end="")
                                            # Compare token with that stored in authentication node
                                            # First check if bootstrap already stores authentication token
                                            search_token = cmdparts[3]
                                            for index, token in enumerate(client_tokens):
                                                if token == search_token:
                                                    print()
                                                    print(f"{search_token} found at index {index}.")
                                                    token_found = True
                                                    break
                                            # If token is stored locally (user connected before during session)
                                            if token_found:
                                                print()
                                                print("Token found locally")
                                                self.load_balancer("filedistribution",
                                                                   self.clientConnection
                                                                   , ip, port, self.connected_client)
                                            else:
                                                # Check with authentication node
                                                print()
                                                print("Token not found locally")
                                                self.clientConnection = connection
                                                self.load_balancer("authTokenCfirm", connection
                                                                   , ip, port, f"{search_token}:{cmdparts[4]}"
                                                                               f":{cmdparts[5]}")
                                        elif cmdparts[2] == "spwn":
                                            print(f"New connected client: {ip}:{port}")
                                            client = Clients(connection, ip, port)
                                            clients.append(client)
                                        else:
                                            print("Invalid command")

                            ### AUTH NODE INCOMING COMMANDS
                            elif message.startswith("auth"):
                                print()
                                cmdparts = message.split(":")
                                if len(cmdparts) >= 3:
                                    if cmdparts[1] == "cmd":
                                        print("Received auth node command")
                                        if cmdparts[2] == "load":
                                            # New authentication node connected
                                            print(f"New authentication node connection establishing...", end="")
                                            print()
                                            name = "auth"
                                            # Save to JSON
                                            self.handle_functional_nodes(connection, name, ip, port)
                                            # REPLY TO AUTH NODE
                                            connection.oBuffer.put(f"cmd:spwn:connection:{ip}:{port}")
                                            global auth_nodes
                                            # Bootstrap save auth node to array
                                            auth_nodes.append(Nodes(len(auth_nodes) + 1, "auth_" +
                                                                    str(len(auth_ms_nodes) + 1), connection, ip, port,
                                                                    None, None))
                                            connection.oBuffer.put("cmd:spwn:ms")
                                        elif cmdparts[2] == "spwnms":
                                            # Received auth incoming command detailing microservice has been spawned
                                            print("Received micro-service details")
                                            ip = cmdparts[3]
                                            port = cmdparts[4]
                                            print(f"Received auth microservice host: {cmdparts[5]}:{cmdparts[6]}")
                                            name = "auth-ms"
                                            self.handle_functional_nodes(connection, name, ip, port)
                                            # Save auth microservice to array
                                            auth_ms_nodes.append(Nodes(len(auth_ms_nodes) + 1, "auth_ms_" +
                                                                       str(len(auth_ms_nodes) + 1),
                                                                       None, ip, port,
                                                                       cmdparts[5], cmdparts[6]))
                                        elif cmdparts[2] == "token":
                                            print(message)
                                            # Token status from authentication node
                                            status = cmdparts[3]
                                            token = cmdparts[4]
                                            if status == "0":
                                                # Success, token confirmed
                                                print(f"Token validated: {cmdparts[4]}")
                                                client_tokens.append(token)
                                                # Now need to send FDN details to client
                                                # Client requires file distribution microservice node
                                                if len(fd_ms_nodes) < 1:
                                                    # No file distribution microservices available
                                                    self.clientConnection.oBuffer.put(f"bootstrap:cmd:fdn:-1")
                                                    # If one content node exists, spawn fdn from that content node
                                                    if len(content_nodes) == 1:
                                                        node = content_nodes[0]
                                                        self.load_balancer("content", node.connection,
                                                                           ip, port, None)

                                                elif len(fd_ms_nodes) >= 1:
                                                    # File distribution microservice available
                                                    self.load_balancer("filedistribution",
                                                                       self.clientConnection
                                                                       , ip, port, self.connected_client)
                                            else:
                                                # Failure, token not confirmed
                                                print("Invalid token")
                                                connection.oBuffer.put(f"bootstrap:cmd:token:-1")
                                        elif cmdparts[2] == "terminated":
                                            # Received from auth node that microservice has been terminated
                                            print(f"Auth Microservice: {cmdparts[3]}:{cmdparts[4]} "
                                                  f"successfully terminated...")
                                            for auth_node in auth_ms_nodes:
                                                # Ensure it targets correct authentication node with
                                                # corresponding microservice
                                                if f"{auth_node.ip}:{auth_node.port}" == f"{cmdparts[3]}:{cmdparts[4]}":
                                                    print(f"Auth Microservice: {auth_node.ip}:{auth_node.port} "
                                                          f"details successfully deleted...")
                                                    # Remove node from array
                                                    auth_ms_nodes.remove(auth_node)
                            ### FDN NODE INCOMING NODES
                            elif message.startswith("fdn"):
                                print()
                                cmdparts = message.split(":")
                                global fd_nodes
                                if len(cmdparts) >= 3:
                                    if cmdparts[1] == "cmd":
                                        print("Received fdn node command")
                                        if cmdparts[2] == "load":
                                            print(f"New file distribution node connection establishing...", end="")
                                            print()
                                            name = "fdn"
                                            connection.oBuffer.put(f"cmd:spwn:connection:{ip}:{port}")
                                            self.handle_functional_nodes(connection, name, ip, port)
                                            # Bootstrap save fdn node
                                            fd_nodes.append(Nodes(len(fd_nodes) + 1, "fdn_" +
                                                                    str(len(fd_ms_nodes) + 1), connection, ip, port,
                                                                  None, None))
                                            connection.oBuffer.put("cmd:spwn:ms")
                                        elif cmdparts[2] == "spwnms":
                                            print("Received micro-service details for fdn")
                                            ip = cmdparts[3]
                                            port = cmdparts[4]
                                            print(f"Received fdn microservice host: {cmdparts[5]}:{cmdparts[6]}")
                                            name = "fdn-ms"
                                            # Add node to json
                                            self.handle_functional_nodes(connection, name, ip, port)
                                            # Append node to array
                                            fd_ms_nodes.append(Nodes(len(fd_ms_nodes) + 1, "fdn_ms_" +
                                                                       str(len(fd_ms_nodes) + 1),
                                                                       connection, ip, port,
                                                                       cmdparts[5], cmdparts[6]))
                                        elif cmdparts[2] == "terminated":
                                            # Received from fdn node that microservice has been terminated
                                            print(f"FDN Microservice: {cmdparts[3]}:{cmdparts[4]} "
                                                  f"successfully terminated...")
                                            for fdn_node in fd_ms_nodes:
                                                # Ensure it targets correct file distribution node with
                                                # corresponding microservice
                                                if f"{fdn_node.ip}:{fdn_node.port}" == f"{cmdparts[3]}:{cmdparts[4]}":
                                                    print(f"FDN Microservice: {fdn_node.ip}:{fdn_node.port} "
                                                          f"details successfully deleted...")
                                                    # Remove node from array
                                                    fd_ms_nodes.remove(fdn_node)

                            ### CONTENT NODE INCOMING COMMANDS
                            elif message.startswith("content"):
                                cmdparts = message.split(":")
                                if len(cmdparts) >= 3:
                                    if cmdparts[1] == "cmd":
                                        # If content node has spawned
                                        if cmdparts[2] == "spawn":
                                            print()
                                            print(f"Content node connected")
                                            name = "content"
                                            # Load balance for content
                                            self.load_balancer("content", connection, ip, port, None)
                                        # Error handling
                                        else:
                                            print("An error has occurred with content node spawn command")
                                    else:
                                        print("An error has occurred with content node command")
                                else:
                                    print("An error has occurred with content node command splitting")
                            else:
                                connection.oBuffer.put(f"Echoing: {message}")
                except ConnectionResetError:
                    # Handle client node disconnect gracefully
                    self.connections.remove(connection)
                    break
        # Quit network functionality if running false
        self.network.quit()

    def handle_functional_nodes(self, connection, name, ip, port):
        # Handle new nodes connecting, saves to JSON - A feature that I have not really utilised
        condition = connection.add_node_to_json(name, ip, port)
        if condition:
            print(f"{name} node: {ip}:{port} saved successfully ", end="")
        else:
            print(f"{name} node {ip}:{port} saved unsuccessfully ", end="")
        print()

    def load_balancer(self, command, connection, ip, port, extra):
        # Append the parameters to the circular list - circular load balancing - roundrobin
        self.load_balancer_tasks.append((command, connection, ip, port, extra))

        # Call load_balancer_exe with the parameters from the circular list
        self.load_balancer_exe()

    def load_balancer_exe(self):
        with self.load_balancer_lock:
            # Check if the maximum number of concurrent tasks is reached
            if self.current_tasks >= self.max_concurrent_tasks:
                return
            # Continue with load balancing
            if self.load_balancer_tasks:
                command, connection, ip, port, extra = self.load_balancer_tasks.popleft()

                # Execute the task in a separate thread
                threading.Thread(target=self.execute_task, args=(command, connection, ip, port, extra)).start()
                self.current_tasks += 1

    def execute_task(self, command, connection, ip, port, extra):
        global content_node
        global content_nodes
        global connected_clients
        global auth_nodes
        # Start node local count
        count_authentication = 0
        count_filedistribution = 0
        # Increment auth and fd node counts
        for nodes in content_nodes:
            if "authentication" in nodes.functionalNodes:
                count_authentication += 1
            if "filedistribution" in nodes.functionalNodes:
                count_filedistribution += 1
        print(f"Nodes available: auth:{count_authentication} and fdn:{count_filedistribution}")
        print(f"Current content nodes available: {len(content_nodes)}")
        if command == "content":
            # If no content nodes available, this first connected node will be authentication
            if content_node == 0:
                print(f"Currently no content nodes available - establishing connection to first "
                      f"content node")
                # Append content node count
                content_node += 1
                # Content node class object, append to array
                content_node_type = ContentNodes(connection, ip, port, "authentication")
                print("Assigning first content node to authentication node")
                # Tell content node to spawn authentication node
                connection.oBuffer.put("cmd:node:auth")
                content_nodes.append(content_node_type)
                content_node_type.display_info()
            # If more then one content_node connected -> fdn
            elif content_node >= 1:
                # Print node counts
                # 1 or more authentication nodes connected
                if count_authentication >= 1 and count_filedistribution < 1:
                    # If 0 file distribution nodes connected
                    if count_filedistribution == 0:
                        # Increment content node count
                        content_node += 1
                        # Assign file distribution node to array
                        content_node_type = ContentNodes(connection, ip, port, "filedistribution")
                        print(f"Assigning content node {content_node} to file distribution node")
                        # Contact content to spawn FDN
                        connection.oBuffer.put("cmd:node:fdn")
                        content_nodes.append(content_node_type)
                        content_node_type.display_info()
                # If FDN node exists but AUTH does not
                elif count_authentication < 1 <= count_filedistribution:
                    content_node += 1
                    content_node_type = ContentNodes(connection, ip, port, "authentication")
                    print(f"Assigning content node {content_node} to authentication node")
                    connection.oBuffer.put("cmd:node:auth")
                    content_nodes.append(content_node_type)
                    content_node_type.display_info()
                # If more than one of each AUTH and FDN exists
                # If another content node exists assign to which ever is the lowest count
                # Below goings circular assigning functional nodes, auth,fdn,auth,fdn,... etc etc
                elif count_authentication >= 1 and count_filedistribution >= 1:
                    print(f"Additional content node detected")
                    content_node += 1
                    if count_authentication == count_filedistribution:
                        print(f"Assigning content node {content_node} to authentication node")
                        content_node_type = ContentNodes(connection, ip, port, "authentication")
                        connection.oBuffer.put("cmd:node:auth")
                        content_nodes.append(content_node_type)
                        content_node_type.display_info()
                    elif count_authentication > count_filedistribution:
                        print(f"Assigning content node {content_node} to file distribution node")
                        content_node_type = ContentNodes(connection, ip, port, "filedistribution")
                        connection.oBuffer.put("cmd:node:fdn")
                        content_nodes.append(content_node_type)
                        content_node_type.display_info()
            # Append node to array
            self.handle_functional_nodes(connection, 'content', ip, port)

        ### Confirm client token with auth node
        elif command == 'authTokenCfirm':
            print("Token auth confirm")
            # Send command to authentication node to check client token
            if len(auth_nodes) > 0:
                print("Check token with authentication node...")
                # Token parts
                tokenParts = extra.split(":")
                token = tokenParts[0]
                auth_ms_ip = tokenParts[1]
                auth_ms_port = tokenParts[2]
                # Find array class object that matches tokenParts
                # Find microservice host details, this will be used to confirm node details
                for auth_ms in auth_ms_nodes:
                    if f"{auth_ms_ip}:{auth_ms_port}" == f"{auth_ms.ip}:{auth_ms.port}":
                        print(f"Authentication microservice host: {auth_ms.hostIp} {auth_ms.hostPort}")
                        for auth in auth_nodes:
                            if f"{auth.ip}:{auth.port}" == f"{auth_ms.hostIp}:{auth_ms.hostPort}":
                                print(f"Authentication connection found")
                                auth_connection = auth.connection
                                auth_connection.oBuffer.put(f"cmd:check:token:{token}")
            else:
                connection.oBuffer.put(f"bootstrap:cmd:auth:-1")

        ### Send authentication microservice to client
        elif command == "authentication":
            client = extra
            already_connected = False
            # Send command to client with authentication microservice ip and port
            # Check if the client is already connected to any node
            for auth_ms in auth_ms_nodes:
                if client in auth_ms.connectedClients:
                    # As client is already connected to a authentication node, bootstrap doesn't need to assign it one
                    print(f"Client is already connected to Node {auth_ms.ip}:{auth_ms.port}")
                    name = "auth-ms"
                    auth_ms_connection = (f"{auth_ms.nodeNumber}:{name}:"
                                          f"{auth_ms.ip}:{auth_ms.port}")
                    connection.oBuffer.put(f"bootstrap:cmd:auth:0:{auth_ms_connection}")
                    already_connected = True
                    break

            # Check if all nodes have more than the limit clients connected
            all_auth_ms_nodes_full = all(len(auth_ms.connectedClients) >= self.client_limit for auth_ms in auth_ms_nodes)

            if not all_auth_ms_nodes_full:
                # Find nodes with the least connected clients
                eligible_auth_ms_nodes = sorted(auth_ms_nodes, key=lambda x: len(x.connectedClients))

                if not already_connected:
                    # Go through all eligible authentication microservice nodes
                    for auth_ms in eligible_auth_ms_nodes:
                        if len(auth_ms.connectedClients) <= self.client_limit and client not in auth_ms.connectedClients:
                            auth_ms.connectedClients.append(client)
                            print(f"Client assigned to Node {auth_ms.ip}:{auth_ms.port}")
                            # Microservice type
                            name = "auth-ms"
                            auth_ms_connection = (f"{auth_ms.nodeNumber}:{name}:"
                                                  f"{auth_ms.ip}:{auth_ms.port}")
                            connection.oBuffer.put(f"bootstrap:cmd:auth:0:{auth_ms_connection}")
                            break
            else:
                print(f"All auth microservices nodes have more than {self.client_limit} clients connected.")
                connection.oBuffer.put(f"bootstrap:cmd:auth:-1")
                # Spawn additional authentication microservice dynamically
                # Count the number of auth_ms nodes for each auth node
                matching_auth_counts = {}

                # For each node
                for auth in auth_nodes:
                    matching_auth_counts[auth] = 0  # Initialise the count for each auth node
                    # For each microservice
                    for auth_ms in auth_ms_nodes:
                        if f"{auth.ip}:{auth.port}" == f"{auth_ms.hostIp}:{auth_ms.hostPort}":
                            matching_auth_counts[auth] += 1

                # Find the auth node with the fewest matching auth_ms nodes
                min_matching_count_auth = min(matching_auth_counts, key=matching_auth_counts.get)

                # Display the authentication node details with the least amount of auth microservices
                print(
                    f"The auth node with the fewest matching auth_ms nodes is {min_matching_count_auth.ip}:"
                    f"{min_matching_count_auth.port} with {matching_auth_counts[min_matching_count_auth]} "
                    f"matching auth_ms nodes.")
                # Tell authentication node available with lowest microservice count to spawn new auth microservice
                auth_node_connection = min_matching_count_auth.connection
                auth_node_connection.oBuffer.put("cmd:spwn:ms")

        ### Send filedistribution microservice to client
        elif command == "filedistribution":
            client = extra
            already_connected = False
            # Check if the client is already connected to any node
            for fdn_ms in fd_ms_nodes:
                if client in fdn_ms.connectedClients:
                    print(f"Client is already connected to Node {fdn_ms.ip}:{fdn_ms.port}")
                    name = "fd-ms"
                    fdn_ms_connection = (f"{fdn_ms.nodeNumber}:{name}:"
                                          f"{fdn_ms.ip}:{fdn_ms.port}")
                    connection.oBuffer.put(f"bootstrap:cmd:fdn:0:{fdn_ms_connection}")
                    already_connected = True
                    break

            # Check if all nodes have more than the limit clients connected
            all_fdn_ms_nodes_full = all(len(fdn_ms.connectedClients) >= self.client_limit for fdn_ms in fd_ms_nodes)

            if not all_fdn_ms_nodes_full:
                # Find nodes with the least connected clients
                eligible_fdn_ms_nodes = sorted(fd_ms_nodes, key=lambda x: len(x.connectedClients))

                if not already_connected:
                    # Go through all eligible file distribution microservice nodes
                    for fdn_ms in eligible_fdn_ms_nodes:
                        if len(fdn_ms.connectedClients) <= self.client_limit and client not in fdn_ms.connectedClients:
                            fdn_ms.connectedClients.append(client)
                            print(f"Client assigned to Node {fdn_ms.ip}:{fdn_ms.port}")
                            # Microservice type
                            name = "fd-ms"
                            fdn_ms_connection = (f"{fdn_ms.nodeNumber}:{name}:"
                                                  f"{fdn_ms.ip}:{fdn_ms.port}")
                            self.connected_client.oBuffer.put(f"bootstrap:cmd:fdn:0:{fdn_ms_connection}")
                            break
            else:
                print(f"All fdn microservices nodes have more than {self.client_limit} clients connected.")
                connection.oBuffer.put(f"bootstrap:cmd:fdn:-1")
                # Spawn additional file distribution microservice dynamically
                # Count the number of fdn_ms nodes for each fdn node
                matching_fdn_counts = {}

                # For each node
                for fdn in fd_nodes:
                    matching_fdn_counts[fdn] = 0  # Initialise the count for each fdn node
                    # For each microservice
                    for fdn_ms in fd_ms_nodes:
                        if f"{fdn.ip}:{fdn.port}" == f"{fdn_ms.hostIp}:{fdn_ms.hostPort}":
                            matching_fdn_counts[fdn] += 1

                # Find the fdn node with the fewest matching fdn_ms nodes
                min_matching_count_fdn = min(matching_fdn_counts, key=matching_fdn_counts.get)

                # Display the file distribution node details with the least amount of fdn microservices
                print(
                    f"The fdn node with the fewest matching fdn_ms nodes is {min_matching_count_fdn.ip}:"
                    f"{min_matching_count_fdn.port} with {matching_fdn_counts[min_matching_count_fdn]} "
                    f"matching fdn_ms nodes.")
                # Tell file distribution node available with lowest microservice count to spawn new fdn microservice
                fdn_node_connection = min_matching_count_fdn.connection
                fdn_node_connection.oBuffer.put("cmd:spwn:ms")

        print("Bootstrap Task Ended")

        # Introduce a delay between tasks
        time.sleep(1)
        # Unlock load balancer to accept new loads
        with self.load_balancer_lock:
            self.current_tasks -= 1
        # Continue with the next task
        self.load_balancer_exe()
        return

    def read_json_file(self):
        # Intent was to use this as a feature earlier in development, but never utilised it as using arrays
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
        print(f"Bootstrap node loaded, host: {self.host}, port: {self.port}")
        print("Waiting for connecting nodes...")

    def client_handler(self, clientConnection):
        self.functionalityHandler.add(clientConnection, self.host, self.port)

    def process(self):
        # Create new nodes JSON file when bootstrap initialised
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
    #server = AbstractServer("10.30.8.54", 50001)
    server.process()
