import socket
import threading
import subprocess

MAX_AUTH_NODES = 4  # Maximum number of authentication nodes
auth_nodes = []  # List to keep track of authentication node processes


def handle_client(client_socket, addr):
    request = client_socket.recv(1024)

    # Assuming the request is a command to start an authentication node
    if request == b'START_AUTH_NODE':
        print(f"Received command to start authentication node from {addr}")
        start_authentication_node()

    client_socket.close()


def start_authentication_node():
    # Check if we've reached the maximum number of authentication nodes
    if len(auth_nodes) < MAX_AUTH_NODES:
        # Use subprocess to start another Python file containing the server
        auth_process = subprocess.Popen(['python', 'authentication_node.py'])
        auth_nodes.append(auth_process)
        print(f"Started a new authentication node. Total nodes: {len(auth_nodes)}")
    else:
        print("Maximum number of authentication nodes reached.")


def main():
    bind_ip = '0.0.0.0'
    bind_port = 9999

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((bind_ip, bind_port))
    server.listen(5)

    print(f"Load balancer listening on {bind_ip}:{bind_port}")

    while True:
        client, addr = server.accept()
        client_handler = threading.Thread(target=handle_client, args=(client, addr))
        client_handler.start()


if __name__ == '__main__':
    main()
