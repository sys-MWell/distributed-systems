import os
import hashlib
from flask import Flask, send_file, make_response, jsonify

app = Flask(__name__)

# Define the folder containing audio files
audio_folder = './audio'

@app.route('/download_media/<filename>', methods=['GET'])
def download_media(filename):
    # Replace 'path/to/your/media/files/' with the actual path to your media files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_location = f"./audio/{filename}"
    media_file = os.path.join(script_dir, file_location)

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

    return response

@app.route('/list_audio', methods=['GET'])
def list_audio():
    # Get the list of audio files in the specified folder
    audio_files = [file for file in os.listdir(audio_folder) if file.endswith(('.mp3', '.wav', '.ogg'))]

    # Return the list as JSON
    return jsonify({'audio_files': audio_files})

if __name__ == '__main__':
    app.run(host='localhost', port=50006, debug=True)
