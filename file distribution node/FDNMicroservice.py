import os
import hashlib
import sys
from flask import Flask, send_file, make_response, jsonify

app = Flask(__name__)

@app.route('/download_media/<filename>', methods=['GET'])
def download_media(filename):
    # Replace 'path/to/your/media/files/' with the actual path to your media files
    print()
    print(f"Client connected, requested download of: {filename}")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_location = f"./audio/{filename}"
    media_file = os.path.join(script_dir, file_location)

    '''
    MAYBE HERE ADD VALIDATION FOR TOKEN 
    LIKE LINK COULD BE /download_media/<filename>/<token> something like this
    SOME WAY TO CONTACT AUTH NODE TO CONFIRM VALIDATION
    '''

    # Check if the file exists
    if not os.path.exists(media_file):
        return "File not found", 404

    # Calculate MD5 checksum while streaming the file
    md5 = hashlib.md5()
    with open(media_file, 'rb') as file:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: file.read(4096), b""):
            md5.update(byte_block)

    # Create a Flask response for streaming the file
    response = make_response(send_file(
        media_file,
        mimetype='application/octet-stream',
        as_attachment=True,
        download_name=filename
    ))

    # Add MD5 checksum to the response headers
    response.headers['Content-MD5'] = md5.hexdigest()
    print(f"File transmission to user...")
    return response

@app.route('/list_audio', methods=['GET'])
def list_audio():
    print()
    print(f"Client connected, requested audio list")
    # Get the list of audio files in the specified folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_location = f"./audio"
    media_file = os.path.join(script_dir, file_location)
    audio_files = [file for file in os.listdir(media_file) if file.endswith(('.mp3', '.wav', '.ogg'))]

    # Return the list as JSON
    return jsonify({'audio_files': audio_files})

if __name__ == '__main__':
    # Default Microservice IP and PORT
    ip = 'localhost'
    port = 50007

    # Check if IP and PORT parameters are provided via command-line arguments
    if len(sys.argv) > 2:
        ip = sys.argv[1]
        port = int(sys.argv[2])

    app.run(host=ip, port=port, debug=True)
