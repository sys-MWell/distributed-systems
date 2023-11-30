import subprocess
import threading
import requests
import signal
import os

# Start the AuthMicroservice using subprocess
auth_microservice_process = subprocess.Popen(["python", "AuthMicroservice.py"])

# Wait for the microservice to start (you can use a more robust method for production)
# For demonstration purposes, a short delay is added here
import time
time.sleep(2)

# URL of the AuthMicroservice
auth_microservice_url = 'http://localhost:50004/register'  # Replace with the actual URL

# User details for registration
user_details = {
    'username': 'example_user',
    'password': 'example_password'
}

# Send a POST request to the AuthMicroservice
response = requests.post(auth_microservice_url, json=user_details)

def stop_auth_microservice():
    os.kill(auth_microservice_process.pid, signal.SIGTERM)

# Retrieve the authentication token from the response
if response.status_code == 200:
    token = response.json()['token']
    print(f"Received authentication token: {token}")
    stop_auth_microservice()
else:
    print(f"Failed to retrieve authentication token. Status code: {response.status_code}")
    stop_auth_microservice()

