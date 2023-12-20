import subprocess
import threading
import requests
import signal
import os
import time

# Start three instances of the AuthMicroservice on different ports
auth_microservice_processes = subprocess.Popen(["python", "AuthMicroservice.py", "--port", "50005"])

# Wait for the microservice to start (you can use a more robust method for production)
# For demonstration purposes, a short delay is added here
time.sleep(2)

# URL of the AuthMicroservice
auth_microservice_url = 'http://localhost:50004/register'  # Replace with the actual URL

# Start Nginx as a load balancer
#nginx_process = subprocess.Popen(["nginx", "-c", "nginx.conf"])

# User details for registration
user_details = {
    'username': 'example_user112',
    'password': 'example_password111'
}

# Set a timeout for the requests.post call
try:
    response = requests.post(auth_microservice_url, json=user_details, timeout=5)  # Adjust the timeout as needed
except requests.Timeout:
    print("Request timed out. Connection to AuthMicroservice aborted.")
    os.kill(auth_microservice_processes.pid, signal.SIGTERM)  # Terminate the microservice process
except requests.RequestException as e:
    print(f"Request failed. Error: {e}")
    os.kill(auth_microservice_processes.pid, signal.SIGTERM)  # Terminate the microservice process
else:
    # Retrieve the authentication token from the response
    if response.status_code == 200:
        token = response.json()['token']
        print(f"Received authentication token: {token}")
    else:
        print(f"Failed to retrieve authentication token. Status code: {response.status_code}")

# Terminate the microservice process
print(f"Ended")
