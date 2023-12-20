import sys
import os
from flask import Flask, request, jsonify
import uuid

app = Flask(__name__)

# Get the absolute path of the script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Endpoint for user registration
@app.route('/register', methods=['POST'])
def register():
    # Get user details from the request
    user_details = request.get_json()
    print()
    print("Client connected, information received")

    # Generate an authentication token
    auth_token = str(uuid.uuid4())

    # Save user details to a text file
    try:
        # Check if the file exists, create it if it doesn't
        user_data_file = os.path.join(script_dir, 'userData.txt')
        if not os.path.exists(user_data_file):
            with open(user_data_file, 'w'):  # 'w' mode will create the file if it doesn't exist
                pass
        with open(user_data_file, 'a') as file:
            file.write(f"Username: {user_details['username']}, Password: {user_details['password']}, Token: {auth_token}\n")

        print("Authentication successful, token generated")
        # Return the authentication token
        return jsonify({'token': auth_token})
    except Exception as ex:
        print(f"Exception: {ex}")


if __name__ == '__main__':
    # Default Microservice IP and PORT
    ip = 'localhost'
    port = 50007

    # Check if IP and PORT parameters are provided via command-line arguments
    if len(sys.argv) > 2:
        ip = sys.argv[1]
        port = int(sys.argv[2])

    app.run(host=ip, port=port, debug=True)
