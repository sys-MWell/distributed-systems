import requests

# URL of the AuthMicroservice
auth_microservice_url = 'http://localhost:50007/register'  # Replace with the actual URL

# User details for registration
user_details = {
    'username': 'example_user_2',
    'password': 'example_password_2'
}

# Send a POST request to the AuthMicroservice
response = requests.post(auth_microservice_url, json=user_details)

# Retrieve the authentication token from the response
if response.status_code == 200:
    token = response.json()['token']
    print(f"Received authentication token: {token}")
else:
    print(f"Failed to retrieve authentication token. Status code: {response.status_code}")