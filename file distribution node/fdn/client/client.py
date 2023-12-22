import requests
import hashlib
from urllib.parse import unquote  # Use unquote to handle URL-encoded filenames

# Replace 'http://localhost:50006/download_media/StarWars3.wav' with the actual URL of your Flask server
media_download_url = 'http://localhost:50006/download_media/StarWars3.wav'

# Send a GET request to download the media file as bytes
response = requests.get(media_download_url)

# Check if the request was successful (status code 200)
if response.status_code == 200:
    # Retrieve the downloaded file data, the Content-MD5 header, and the Content-Disposition header
    file_data = response.content
    md5_checksum_header = response.headers.get('Content-MD5')
    content_disposition_header = response.headers.get('Content-Disposition')

    # Calculate MD5 checksum for the downloaded file
    calculated_md5_checksum = hashlib.md5(file_data).hexdigest()

    # Verify MD5 checksum
    if md5_checksum_header and md5_checksum_header == calculated_md5_checksum:
        # Extract the suggested filename from the Content-Disposition header
        suggested_filename = None
        if content_disposition_header:
            _, params = content_disposition_header.split(';', 1)
            for param in params.split(';'):
                key, value = param.strip().split('=', 1)
                if key.lower() == 'filename':
                    suggested_filename = unquote(value.strip('\"'))

        # Use the suggested filename or a default name if not provided
        download_filename = suggested_filename or 'downloaded_media'

        # Save the downloaded file with the suggested filename
        with open(download_filename, 'wb') as file:
            file.write(file_data)

        print(f'Media file downloaded successfully as {download_filename}.')
    else:
        print('Failed to verify MD5 checksum. File may be corrupted.')
else:
    print(f'Failed to download media file. Status code: {response.status_code}')


# Replace 'http://localhost:50006/list_audio/music' with the actual URL of your Flask server
list_audio_url = 'http://localhost:50006/list_audio'

# Send a GET request to obtain the list of audio files
response = requests.get(list_audio_url)

# Check if the request was successful (status code 200)
if response.status_code == 200:
    # Retrieve the list of audio files from the JSON response
    audio_files = response.json().get('audio_files', [])

    if audio_files:
        print('List of audio files:')
        for file in audio_files:
            print(f'- {file}')
    else:
        print('No audio files available in the specified folder.')
else:
    print(f'Failed to obtain the list of audio files. Status code: {response.status_code}')