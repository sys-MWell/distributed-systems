# All of the processing code has now been pulled into this file - the network code remains in the other file Abstract...
import time
from ClientNetworkInterface import ClientNetworkInterface
import threading

auth_nodes = []
fdn_nodes = []

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


class abstractClient:
    def __init__(self, host="127.0.0.1", port=50001):
        self.host = host
        self.port = port
        self.networkHandler = ClientNetworkInterface()
        self.connection = None
        self.uiThread = threading.Thread(target=self.ui)
        self.running = True

    # Simple UI thread
    def ui(self):
        # Handle incoming messages from the server
        while self.running:
            if self.connection:
                message = self.connection.iBuffer.get()
                if message:
                    if message == 'auth':
                        # Hardcoded bootstrap prime node - ip, port - CHANGE IP TO BOOSTRAP IP
                        print("Waiting for authentication...")
                    elif message.startswith('bootstrap'):
                        cmdparts = message.split(":")
                        if len(cmdparts) >= 3:
                            if cmdparts[1] == "cmd":
                                print("Command received from bootstrap")
                                if cmdparts[2] == "auth":
                                    nodeStatus = cmdparts[3]
                                    if nodeStatus == '0':
                                        # Connect to microservice
                                        print(f"Received command: {message}")
                                        nodeNumber = int(cmdparts[4])
                                        nodeName = cmdparts[5]
                                        nodeIP = cmdparts[6]
                                        nodePort = cmdparts[7]
                                        auth_nodes.append(Nodes(nodeNumber, nodeName, nodeIP, nodePort))
                                    else:
                                        print("Authentication node unavailable")
                                        print("Please try again...")
                                        time.sleep(5)
                                        print()
                                        self.contextual_menu()

                            # Context menu selection
                            #connection.oBuffer.put(f"bootstrap:cmd:auth:-1")


                    elif message.startswith('authNodeConn'):
                        contextOptionCommand = "conOptComAuthReq"
                        print("Receiving authentication node information...")
                        if self.connection:
                            time.sleep(10)
                            self.connection.oBuffer.put(contextOptionCommand)


    def process(self):
        # Start the UI thread and start the network components
        self.uiThread.start()
        self.connection = self.networkHandler.start_client(self.host, self.port)
        self.contextual_menu()

        while self.running:
            pass
            if self.connection:
                pass
            else:
                self.running = False

        # stop the network components and the UI thread
        self.networkHandler.quit()
        self.uiThread.join()

    def node_connection(self, type, ip, port):
        print("Connection to auth here")
        # authNode = abstractAuthClient('127.0.0.9', 50005)
        # authNode.process()

    def contextual_menu(self):
        contextOption = input("Please select an option:\n"
                                "1 - Login\n"
                                "2 - Signup\n"
                                "3 - Exit\n"
                                "Option: ")
        if contextOption == "1":
            print("Selected Login")
        elif contextOption == "2":
            print("Selected Signup")
        elif contextOption == "3":
            print("Selected Exit")
        else:
            print("Invalid option selected\n")
            time.sleep(1)
            self.contextual_menu()
        contextOptionCommand = "client:cmd:context:"+contextOption
        if self.connection:
            self.connection.oBuffer.put(contextOptionCommand)


if __name__ == "__main__":
    # Hardcoded bootstrap prime node - ip, port - CHANGE IP TO BOOSTRAP IP
    client = abstractClient("127.0.0.1", 50001)
    client.process()