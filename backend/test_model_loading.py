import os
import sys

print("=" * 60)
print("🔍 CHECKING MODEL STATUS")
print("=" * 60)

# Check current directory
print(f"\nCurrent directory: {os.getcwd()}")

# Check if ml_model folder exists
ml_model_dir = 'ml_model'
if os.path.exists(ml_model_dir):
    print(f"✓ ml_model/ folder exists")
    files = os.listdir(ml_model_dir)
    print(f"\nFiles in ml_model/:")
    for f in files:
        file_path = os.path.join(ml_model_dir, f)
        size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
        print(f"  - {f} ({size:,} bytes)")
else:
    print(f"❌ ml_model/ folder NOT found")

# Check if training_data exists
training_dir = 'training_data'
if os.path.exists(training_dir):
    print(f"\n✓ training_data/ folder exists")
    for skin_type in ['normal', 'oily', 'dry', 'combination', 'sensitive']:
        folder_path = os.path.join(training_dir, skin_type)
        if os.path.exists(folder_path):
            count = len([f for f in os.listdir(folder_path) if f.endswith(('.jpg', '.png', '.jpeg'))])
            print(f"  - {skin_type}: {count} images")
else:
    print(f"❌ training_data/ folder NOT found")

# Try to load the model
print("\n" + "=" * 60)
print("🧪 TESTING MODEL LOADING")
print("=" * 60)

try:
    from services.ml_service import get_analyzer
    analyzer = get_analyzer()
    
    if analyzer.model is not None:
        print("✅ MODEL LOADED SUCCESSFULLY!")
        print(f"   Model type: {type(analyzer.model)}")
    else:
        print("⚠️  Model not loaded - using fallback analysis")
except Exception as e:
    print(f"❌ Error loading model: {e}")

print("\n" + "=" * 60)