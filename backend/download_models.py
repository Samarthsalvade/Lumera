import os
import requests

def _gdrive_url(file_id: str) -> str:
    return f"https://drive.google.com/uc?export=download&id={file_id}"

# Paste your Google Drive file IDs here after uploading
MODELS = {
    'ml_model/best_model_v2.keras':    os.environ.get('MODEL_ID_SKIN', ''),
    'ml_model/concern_model_v3.keras': os.environ.get('MODEL_ID_CONCERN_V3', ''),
    'ml_model/concern_model_v2.keras': os.environ.get('MODEL_ID_CONCERN_V2', ''),
    'ml_model/concern_model.keras':    os.environ.get('MODEL_ID_CONCERN_V1', ''),
}

def download_models():
    base = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(base, 'ml_model'), exist_ok=True)

    for relative_path, file_id in MODELS.items():
        full_path = os.path.join(base, relative_path)
        if os.path.exists(full_path):
            print(f'Already exists: {relative_path}')
            continue
        if not file_id:
            print(f'No ID set for {relative_path} — skipping')
            continue
        print(f'Downloading {relative_path} from Google Drive...')
        try:
            session = requests.Session()
            url = _gdrive_url(file_id)
            response = session.get(url, stream=True, timeout=300)

            # Google Drive shows a virus scan warning for large files
            # We need to confirm the download
            token = None
            for key, value in response.cookies.items():
                if key.startswith('download_warning'):
                    token = value
                    break

            if token:
                response = session.get(
                    url, params={'confirm': token}, stream=True, timeout=300
                )

            with open(full_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=32768):
                    if chunk:
                        f.write(chunk)

            size_mb = os.path.getsize(full_path) / (1024 * 1024)
            print(f'Done: {relative_path} ({size_mb:.1f} MB)')

        except Exception as e:
            print(f'Failed to download {relative_path}: {e}')

if __name__ == '__main__':
    download_models()