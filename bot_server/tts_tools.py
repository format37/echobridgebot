import requests
import os

def generate_speech(text, language, reference_file='asmr_0.wav', api_url="http://localhost:5000"):    
    # Request payload
    payload = {
        'text': text,
        'language': language,
        'reference_file': reference_file
    }
    
    try:
        # Send POST request
        response = requests.post(f"{api_url}/tts", json=payload)
        
        # Check if request was successful
        if response.status_code == 200:
            # Save the audio file
            output_filename = 'output.wav'
            with open(output_filename, 'wb') as f:
                f.write(response.content)
            print(f"Audio saved as {output_filename}")
        else:
            print(f"Error: {response.json().get('error', 'Unknown error')}")
            
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {str(e)}")

def upload_reference_file(file_path, api_url="http://localhost:5000", filename="reference.wav"):
    """
    Upload a reference audio file to the TTS server
    
    Args:
        file_path (str): Path to the audio file
        api_url (str): Base URL of the API server
    
    Returns:
        dict: Server response
    """
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Prepare the file and filename for upload
    files = {
        'file': open(file_path, 'rb')
    }
    
    data = {
        'filename': filename
    }
    
    try:
        response = requests.post(
            f"{api_url}/upload_reference",
            files=files,
            data=data
        )
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"Error uploading file: {str(e)}")
        raise
    finally:
        files['file'].close()

if __name__ == "__main__":
    url = 'https://d676-5-178-149-227.ngrok-free.app'
    # Example Russian text
    text = "Так, кажется кому-то пора помыть посуду"
    language = 'ru'
    reference_file = 'kompot.wav'
    # Generate speech
    generate_speech(url, text, language, reference_file)
