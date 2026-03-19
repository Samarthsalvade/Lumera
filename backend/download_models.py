import os
import requests

def download_models():
    base = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(base, 'ml_model'), exist_ok=True)

    models = {
        'ml_model/best_model_v2.keras':    os.environ.get('MODEL_ID_SKIN', ''),
        'ml_model/concern_model_v3.keras': os.environ.get('MODEL_ID_CONCERN_V3', ''),
        'ml_model/concern_model_v2.keras': os.environ.get('MODEL_ID_CONCERN_V2', ''),
        'ml_model/concern_model.keras':    os.environ.get('MODEL_ID_CONCERN_V1', ''),
    }

    # ── NEW: if all 4 models are already on disk and valid, skip everything ──
    all_present = all(
        os.path.exists(os.path.join(base, p)) and
        os.path.getsize(os.path.join(base, p)) > 1024 * 100
        for p in models
    )
    if all_present:
        print('✓ All models already present on disk — skipping Google Drive download')
        return
    # ────────────────────────────────────────────────────────────────────────

    for relative_path, file_id in models.items():
        full_path = os.path.join(base, relative_path)

        # Delete corrupt 0-byte files from previous failed downloads
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            if size < 1024 * 100:  # less than 100KB means it's corrupt
                print(f'Removing corrupt file: {relative_path} ({size} bytes)')
                os.remove(full_path)
            else:
                print(f'Already exists: {relative_path} ({size/(1024*1024):.1f} MB)')
                continue

        if not file_id:
            print(f'No ID set for {relative_path} — skipping')
            continue

        print(f'Downloading {relative_path} from Google Drive...')
        try:
            session = requests.Session()
            url = f'https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t&authuser=0'
            response = session.get(url, stream=True, timeout=600)
            response.raise_for_status()
            with open(full_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=32768):
                    if chunk:
                        f.write(chunk)
            size_mb = os.path.getsize(full_path) / (1024 * 1024)
            if size_mb < 0.1:
                print(f'WARNING: {relative_path} downloaded but only {size_mb:.2f} MB — may be corrupt')
            else:
                print(f'Done: {relative_path} ({size_mb:.1f} MB)')
        except Exception as e:
            print(f'Failed to download {relative_path}: {e}')

if __name__ == '__main__':
    download_models()