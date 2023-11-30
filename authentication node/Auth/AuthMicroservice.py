from flask import Flask, request, jsonify
import uuid

app = Flask(__name__)

# Endpoint for user registration
@app.route('/register', methods=['POST'])
def register():
    # Get user details from the request
    user_details = request.get_json()

    # Generate an authentication token (you can use a more secure method for production)
    auth_token = str(uuid.uuid4())

    # Save user details to a text file (you should use a database for production)
    with open('userData.txt', 'a') as file:
        file.write(f"Username: {user_details['username']}, Password: {user_details['password']}, Token: {auth_token}\n")

    # Return the authentication token
    return jsonify({'token': auth_token})

if __name__ == '__main__':
    app.run(host="localhost", port=50004, debug=True)