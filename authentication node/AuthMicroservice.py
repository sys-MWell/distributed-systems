import sys
import os
import uuid

from flask import Flask, request, jsonify

app = Flask(__name__)

# Get the absolute path of the script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Endpoint for user registration
@app.route('/register', methods=['POST'])
def register():
    try:
        # Get user details from the request
        user_details = request.get_json()
        print()
        print("Client connected, information received")

        # Check if user wants login or register
        # Login
        if user_details['option'] == '1':
            print("Login functionality")
            username = user_details['username']
            password = user_details['password']
            token = None

            # Check not empty username and password
            if not username or not password:
                print("Error: username or password is incorrect format")
                return jsonify({'error': 'Username or password cannot be empty'}), 400  # 400 indicates bad request

            user_data_file = os.path.join(script_dir, 'userData.txt')
            user_found = False  # Flag to check if the user is found

            # Check user details in userData.txt file
            with open(user_data_file, 'r') as file:
                for line in file:
                    # Parse the line to extract username, password, and token
                    if 'Username: ' + username in line and ' Password: ' + password in line:
                        token = line.split(', ')[-1].replace(' Token: ', '').strip()
                        user_found = True
                        break  # Stop searching once a matching line is found

            if user_found:
                return jsonify({'token': token})
            else:
                # Username or password not found
                print("Error: Username or password not found")
                return jsonify({'error': 'Username or password not found'}), 401  # 401 indicates unauthorized

        # Register
        elif user_details['option'] == '2':
            print("Register functionality")
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
        else:
            print("Error occurred")
            pass
    except Exception as ex:
        print(f"Exception: {ex}")


if __name__ == '__main__':
    # Default Microservice IP and PORT
    ip = "localhost"
    port = 50007

    # Check if IP and PORT parameters are provided via command-line arguments
    try:
        if len(sys.argv) > 2:
            ip = sys.argv[1]
            port = int(sys.argv[2])
    except Exception as ex:
        print(f"Exception: {ex}")

    app.run(host=ip, port=port, debug=True)
