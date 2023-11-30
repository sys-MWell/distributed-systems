import subprocess
import requests

# Start the AuthMicroservice using subprocess
p = subprocess.Popen(["python", "AuthMicroservice.py"])

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

# Retrieve the authentication token from the response
if response.status_code == 200:
    token = response.json()['token']
    print(f"Received authentication token: {token}")
else:
    print(f"Failed to retrieve authentication token. Status code: {response.status_code}")
