# All of the processing code has now been pulled into this file - the network code remains in the other file Abstract...
import time
from ClientNetworkInterface import ClientNetworkInterface
import threading
import requests

nodes = []
auth_token = ''

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

        # Context status
        self.context_status = 0

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
                                if cmdparts[2] == "auth":
                                    if len(nodes) < 1:
                                        nodeStatus = cmdparts[3]
                                        if nodeStatus == '0':
                                            # Connect to microservice
                                            print(f"Received command: {message}")
                                            nodeNumber = int(cmdparts[4])
                                            nodeName = cmdparts[5]
                                            nodeIP = cmdparts[6]
                                            nodePort = cmdparts[7]
                                            nodes.append(Nodes(nodeNumber, nodeName, nodeIP, nodePort))
                                            self.node_connection()
                                        else:
                                            print("Authentication node unavailable")
                                            print("Please try again...")
                                            time.sleep(5)
                                            print()
                                            self.contextual_menu()
                                    else:
                                        # Node already exists
                                        self.node_connection()

                                elif cmdparts[2] == "fdn":
                                    print("fdn")

                                elif cmdparts[2] == "token":
                                    if cmdparts[3] == "-1":
                                        print("Token unavailable/invalid, connection failure")
                                        print("Please try again...")
                                        time.sleep(5)
                                        self.contextual_menu()

                                else:
                                    print("error2")
                            # Context menu selection
                            #connection.oBuffer.put(f"bootstrap:cmd:auth:-1")

                    elif message.startswith('authNodeConn'):
                        contextOptionCommand = "conOptComAuthReq"
                        print("Receiving authentication node information...")
                        if self.connection:
                            time.sleep(10)
                            self.connection.oBuffer.put(contextOptionCommand)

    def node_connection(self):
        # If login
        if self.context_status == 1:
            # Login
            self.authentication('1')
        # If signup
        elif self.context_status == 2:
            # Signup
            self.authentication('2')
        else:
            # Error
            print("An internal error has occurred")
            time.sleep(5)
            self.contextual_menu()

    def process(self):
        # Start the UI thread and start the network components
        self.uiThread.start()
        self.connection = self.networkHandler.start_client(self.host, self.port)
        self.contextual_menu()

        # Continue running client process, always ready to accept and send messages
        while self.running:
            pass
            if self.connection:
                pass
            else:
                self.running = False

        # stop the network components and the UI thread
        self.networkHandler.quit()
        self.uiThread.join()

    def contextual_menu(self):
        time.sleep(4)
        contextOption = input("Please select an option:\n"
                                "1 - Login\n"
                                "2 - Signup\n"
                                "3 - Exit\n"
                                "Option: ")
        if contextOption == "1":
            print("Selected Login")
            self.context_status = 1
        elif contextOption == "2":
            print("Selected Signup")
            self.context_status = 2
        elif contextOption == "3":
            print("Selected Exit")
        else:
            print("Invalid option selected\n")
            time.sleep(1)
            self.contextual_menu()
        contextOptionCommand = "client:cmd:context:"+contextOption
        if self.connection:
            self.connection.oBuffer.put(contextOptionCommand)

    def main_menu(self):
        time.sleep(4)
        # Main menu for audio tool functionality
        menuOptions = input("Please select an option:\n"
                              "1 - Retrieve list of available nodes\n"
                              "2 - List local audio files\n"
                              "3 - List remote audio files\n"
                              "4 - Download audio files\n"
                              "5 - Play audio file\n"
                              "6 - Exit\n"
                              "Option: ")
        if menuOptions == "1":
            print("Retrieve list of available nodes\n")
        elif menuOptions == "2":
            print("List local audio files\n")
        elif menuOptions == "3":
            print("List remote audio files\n")
        elif menuOptions == "4":
            print("Download audio files\n")
        elif menuOptions == "5":
            print("Play audio files\n")
        elif menuOptions == "6":
            print("Exit\n")
        else:
            print("Invalid input selected\n")
            print()
            time.sleep(4)
            self.main_menu()

        # NEED TO CONNECT TO FDN
        # If user select option 3 or 4 -> Requires bootstrap
        # if menuOptions in ["3", "4"]:
        #     menuOptionCmd = f"client:cmd:menu:{menuOptions}:{auth_token}"
        # if self.connection:
        #     self.connection.oBuffer.put(menuOptionCmd)
        #     time.sleep(3)
            # HAVE A WAIT UNTIL HERE FOR REPLY?

            #self.main_menu()

    def authentication(self, option):
        global nodes
        if len(nodes) > 0:
            # Check if auth node is saved in array
            auth_ms_node = next((node for node in nodes if node.nodeType == "auth-ms"), None)
            if auth_ms_node is not None:
                ip = auth_ms_node.ip
                port = auth_ms_node.port
                host = f"{ip}:{port}"
                try:
                    # Connect to authentication microservice - signup/register account
                    authMicroserviceURL = f'http://{host}/register'  # Replace with the actual URL
                    print()

                    # Setting option based of context menu input
                    if option == '1':
                        print("Login")
                    elif option == '2':
                        print("Register")

                    username = input("Username: ")
                    password = input("Password: ")

                    user_details = {
                        'option': option,
                        'username': username,
                        'password': password
                    }

                    # Set a timeout for the requests.post call
                    try:
                        response = requests.post(authMicroserviceURL, json=user_details,
                                                 timeout=5)  # Adjust the timeout as needed
                    except requests.Timeout:
                        # Error timeout
                        print("Request timed out. Connection to AuthMicroservice aborted.")
                        time.sleep(5)
                        print()
                        self.contextual_menu()
                    except requests.RequestException as ex:
                        # Error exception
                        print(f"Request failed. Error: {ex}")
                        time.sleep(5)
                        print()
                        self.contextual_menu()
                    else:
                        # Retrieve the authentication token from the response
                        if response.status_code == 200:
                            # Success - retrieved authentication token
                            global auth_token
                            token = response.json()['token']
                            auth_token = token.replace('Token: ', '')
                            print(f"Received authentication token: {auth_token}")
                            print()
                            # Get FDN details as login/signup successful
                            fdnRqstCmd = f"client:cmd:fdn:{auth_token}"
                            if self.connection:
                                self.connection.oBuffer.put(fdnRqstCmd)
                                time.sleep(3)
                            #self.main_menu()
                        else:
                            # Error code
                            print(f"Failed to retrieve authentication token. Status code: {response.status_code}")
                            time.sleep(5)
                            print()
                            self.contextual_menu()

                except Exception as ex:
                    # Error login/signup, failed details
                    print("Login failed, invalid details entered. Please try again.")
                    time.sleep(5)
                    print()
                    self.contextual_menu()
            else:
                print(f"An error has occurred")
                time.sleep(5)
                print()
                self.contextual_menu()

if __name__ == "__main__":
    # Hardcoded bootstrap prime node - ip, port - CHANGE IP TO BOOSTRAP IP
    client = abstractClient("127.0.0.1", 50001)
    client.process()