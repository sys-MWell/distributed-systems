# All of the processing code has now been pulled into this file - the network code remains in the other file Abstract...
import time

from ClientNetworkInterface import ClientNetworkInterface
import threading

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
                        print("need to connect to auth")
                        # Hardcoded bootstrap prime node - ip, port - CHANGE IP TO BOOSTRAP IP
                        print("Waiting for authentication...")
                        #client = abstractClient("127.0.0.1", 50005)
                        #client.process()
                    elif message.startswith('authNodeConn'):
                        contextOptionCommand = "conOptComAuthReq"
                        print("Receiving authentication node information...")
                        if self.connection:
                            time.sleep(10)
                            self.connection.oBuffer.put(contextOptionCommand)
                    elif message.startswith('authNodeConfirm'):
                        print(message)

    def process(self):
        # Start the UI thread and start the network components
        self.uiThread.start()
        self.connection = self.networkHandler.start_client(self.host, self.port)
        self.contextual_menu()

        while self.running:
            message = input("")
            if self.connection:
                self.connection.oBuffer.put(message)
            else:
                self.running = False

            if message == "Quit":
                self.running = False

        # stop the network components and the UI thread
        self.networkHandler.quit()
        self.uiThread.join()

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
        contextOptionCommand = "conOptCom+"+contextOption
        if self.connection:
            self.connection.oBuffer.put(contextOptionCommand)

if __name__ == "__main__":
    # Hardcoded bootstrap prime node - ip, port - CHANGE IP TO BOOSTRAP IP
    client = abstractClient("127.0.0.1", 50005)
    client.process()