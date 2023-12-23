# All of the processing code has now been pulled into this file - the network code remains in the other file Abstract...
import hashlib
import os
import sys
import pygame
import time
from ClientNetworkInterface import ClientNetworkInterface
import threading
import requests
from urllib.parse import unquote  # Use unquote to handle URL-encoded filenames
from tqdm import tqdm  # Import tqdm for the progress bar

nodes = []
auth_token = ''
downloaded_audio = []

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
        self.uiThread = threading.Thread(target=self.ui, daemon=True)
        self.exit_flag = threading.Event()
        self.running = True

        # Context status
        self.context_status = 0

    # Simple UI thread
    def ui(self):
        # Handle incoming messages from the server
        while not self.exit_flag.is_set():
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
                                        print(f"Received token confirmation from bootstrap")
                                        if len(nodes) >= 1:
                                            nodeStatus = cmdparts[3]
                                            if nodeStatus == '0':
                                                # Connect to microservice
                                                print(f"Received command: {message}")
                                                nodeNumber = int(cmdparts[4])
                                                nodeName = cmdparts[5]
                                                nodeIP = cmdparts[6]
                                                nodePort = cmdparts[7]
                                                nodes.append(Nodes(nodeNumber, nodeName, nodeIP, nodePort))
                                                self.main_menu()
                                            else:
                                                print("File distribution node unavailable")
                                                print("Please try again...")
                                                time.sleep(5)
                                                print()
                                                self.contextual_menu()
                                        else:
                                            # Error handling
                                            self.contextual_menu()

                                    elif cmdparts[2] == "token":
                                        if cmdparts[3] == "-1":
                                            print("Token unavailable/invalid, connection failure")
                                            print("Please try again...")
                                            time.sleep(5)
                                            self.contextual_menu()

                                    else:
                                        print("error2")

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
        # Exit returns back here

        # Continue running client process, always ready to accept and send messages
        while self.running:
            pass
            if self.connection:
                pass
            else:
                self.running = False

        # stop the network components and the UI thread
        self.connection.oBuffer.put("quit")
        self.networkHandler.quit()
        self.exit_flag.set()
        sys.exit(0)

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
            self.exit()
            return
        else:
            print("Invalid option selected\n")
            self.contextual_menu()
        contextOptionCommand = "client:cmd:context:"+contextOption
        if self.connection:
            self.connection.oBuffer.put(contextOptionCommand)

    def main_menu(self):
        global nodes
        print()
        time.sleep(2)
        # Main menu for audio tool functionality
        menuOptions = input("Please select an option:\n"
                              "1 - Retrieve list of available nodes\n"
                              "2 - List local audio files\n"
                              "3 - List remote audio files\n"
                              "4 - Download audio files\n"
                              "5 - Play audio file\n"
                              "6 - Exit\n"
                              "Option: ")
        print()
        if menuOptions == "1":
            self.print_nodes_details(nodes)
        elif menuOptions == "2":
            self.list_local_files()
        elif menuOptions == "3":
            self.list_fdn_files()
        elif menuOptions == "4":
            self.download_fdn_file()
        elif menuOptions == "5":
            self.play_local_file()
        elif menuOptions == "6":
            self.exit()
        else:
            print("Invalid input selected\n")
            print()
            time.sleep(4)
            self.main_menu()

    # Menu option 1: Display all available nodes information
    def print_nodes_details(self, nodes_array):
        print("Retrieve list of available nodes:")
        for node in nodes_array:
            print(
                f"['Node number:' {node.nodeNumber}, 'Node type:' {node.nodeType},"
                f" 'Node IP:' {node.ip}, 'Node port:' {node.port}]")
        input("Press enter to continue...")
        self.main_menu()

    # Menu option 2:
    def list_local_files(self):
        # Local file directory, file audio
        audio_folder_path = os.path.join(os.path.dirname(__file__), "audio")

        # List all files in the "audio" folder
        audio_files = [f for f in os.listdir(audio_folder_path) if os.path.isfile(os.path.join(audio_folder_path, f))]

        if not audio_files:
            print("No audio files found in the 'audio' folder.")
            return

        print("Available audio files:")
        for i, audio_file in enumerate(audio_files):
            print(f"{i + 1}. {audio_file}")
        input("Press enter to continue...")
        self.main_menu()

    # Menu option 3:
    def list_fdn_files(self):
        global nodes
        if len(nodes) > 0:
            # Check if file distribution microservice node is saved in array
            fd_ms_node = next((node for node in nodes if node.nodeType == "fd-ms"), None)
            if fd_ms_node is not None:
                ip = fd_ms_node.ip
                port = fd_ms_node.port
                host = f"{ip}:{port}"
                try:
                    print("Connecting to file distribution microservice")
                    # Flask server connection
                    list_audio_url = f'http://{host}/list_audio'

                    # Send a GET request to obtain the list of audio files
                    response = requests.get(list_audio_url)

                    # Check if the request was successful (status code 200)
                    if response.status_code == 200:
                        # Retrieve the list of audio files from the JSON response
                        audio_files = response.json().get('audio_files', [])

                        if audio_files:
                            print('List of audio files:')
                            for file in audio_files:
                                print(f'- {file}')
                            input("Press enter to continue...")
                        else:
                            print('No audio files available in the specified folder.')
                    else:
                        print(f'Failed to obtain the list of audio files. Status code: {response.status_code}')
                    self.main_menu()
                except Exception as e:
                    print(f"Exception occurred: {e}")
                    self.main_menu()
        else:
            print("Node unavailable")

    # Menu option 4:
    def download_fdn_file(self):
        print("Download audio file:")
        global nodes
        if len(nodes) > 0:
            # Check if file distribution microservice node is saved in array
            fd_ms_node = next((node for node in nodes if node.nodeType == "fd-ms"), None)
            if fd_ms_node is not None:
                ip = fd_ms_node.ip
                port = fd_ms_node.port
                host = f"{ip}:{port}"
                try:
                    file = input(f"Enter filename to download: ")
                    filename = file
                    media_download_url = f'http://{host}/download_media/{file}'

                    # Send a GET request to download the media file as bytes with progress bar
                    with requests.get(media_download_url, stream=True) as response:
                        # Check if the request was successful (status code 200)
                        if response.status_code == 200:
                            # Get total file size from the Content-Length header
                            total_size = int(response.headers.get('Content-Length', 0))

                            # Get the Content-MD5 header for MD5 checksum verification
                            md5_checksum_header = response.headers.get('Content-MD5')

                            # Initialize tqdm with the total size
                            with tqdm(total=total_size, unit='B', unit_scale=True, desc='Downloading') as pbar:
                                # Create a path to the "audio" folder within the current directory
                                audio_folder_path = os.path.join(os.path.dirname(__file__), "audio")

                                # Ensure the "audio" folder exists, create it if not
                                if not os.path.exists(audio_folder_path):
                                    os.makedirs(audio_folder_path)

                                # Construct the full path including the "audio" folder
                                download_filename = os.path.join(audio_folder_path, file)

                                # Open a file to write the downloaded content
                                with open(download_filename, 'wb') as file:
                                    for chunk in response.iter_content(chunk_size=1024):
                                        file.write(chunk)  # Write the chunk directly to the file
                                        pbar.update(len(chunk))  # Update progress bar

                            # Calculate MD5 checksum for the downloaded file
                            calculated_md5_checksum = hashlib.md5(open(download_filename, 'rb').read()).hexdigest()

                            # Verify MD5 checksum
                            if md5_checksum_header and md5_checksum_header == calculated_md5_checksum:
                                print(f'Media file downloaded successfully as {filename}.')
                                time.sleep(1)
                                # Create a path to the "audio" folder within the current directory
                                audio_folder_path = os.path.join(os.path.dirname(__file__), "audio")
                                print(f'Playing media file: {filename}.')
                                file_path = os.path.join(audio_folder_path, filename)
                                self.play_audio_file(file_path)
                                while True:
                                    user_input = input("Enter 'p' to pause, 'r' to resume, or 'q' to quit: ").lower()
                                    if user_input == 'p':
                                        pygame.mixer.music.pause()
                                        print("Paused.")
                                    elif user_input == 'r':
                                        pygame.mixer.music.unpause()
                                        print("Resumed.")
                                    elif user_input == 'q':
                                        pygame.mixer.music.stop()
                                        print("Quitting.")
                                        break
                                    else:
                                        print("Invalid input. Please enter 'p', 'r', or 'q'.")
                                input("Press enter to continue...")
                            else:
                                print('Failed to verify MD5 checksum. File may be corrupted.')
                        else:
                            print(f'Failed to download media file. Status code: {response.status_code}')
                    self.main_menu()
                except Exception as e:
                    print(f"Exception occurred: {e}")
                    self.main_menu()
            else:
                print("Node unavailable")
        else:
            print("Node unavailable")

    def play_local_file(self):
        print("Playing local file...")
        audio_folder_path = os.path.join(os.path.dirname(__file__), "audio")

        # List all files in the "audio" folder
        audio_files = [f for f in os.listdir(audio_folder_path) if os.path.isfile(os.path.join(audio_folder_path, f))]

        if not audio_files:
            print("No audio files found in the 'audio' folder.")
            return

        print("Available audio files:")
        for i, audio_file in enumerate(audio_files):
            print(f"{i + 1}. {audio_file}")

        try:
            file_index = int(input("Enter the number of the file you want to play: ")) - 1
            selected_file = audio_files[file_index]
            file_path = os.path.join(audio_folder_path, selected_file)
            print(f"Playing {selected_file}...")
            self.play_audio_file(file_path)

            while True:
                user_input = input("Enter 'p' to pause, 'r' to resume, or 'q' to quit: ").lower()
                if user_input == 'p':
                    pygame.mixer.music.pause()
                    print("Paused.")
                elif user_input == 'r':
                    pygame.mixer.music.unpause()
                    print("Resumed.")
                elif user_input == 'q':
                    pygame.mixer.music.stop()
                    print("Quitting.")
                    break
                else:
                    print("Invalid input. Please enter 'p', 'r', or 'q'.")
            input("Press enter to continue...")
            self.main_menu()

        except (ValueError, IndexError):
            print("Invalid input. Please enter a valid file number.")
            input("Press enter to continue...")
            self.main_menu()

    def play_audio_file(self, file_path):
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()

    def authentication(self, option):
        global nodes
        if len(nodes) > 0:
            # Check if auth microservice node is saved in array
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

    # Client application close
    def exit(self):
        print("Exit selected")
        self.running = False
        return

if __name__ == "__main__":
    # Hardcoded bootstrap prime node - ip, port - CHANGE IP TO BOOSTRAP IP
    client = abstractClient("127.0.0.1", 50001)
    client.process()