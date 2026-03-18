import kagglehub
import os
import shutil
from pathlib import Path

def download_and_prepare_dataset():
    """
    Download Kaggle dataset and prepare it for training
    """
    print("=" * 60)
    print("📥 DOWNLOADING KAGGLE DATASET")
    print("=" * 60)
    
    # Download dataset
    print("\n1. Downloading from Kaggle...")
    path = kagglehub.dataset_download("shakyadissanayake/oily-dry-and-normal-skin-types-dataset")
    print(f"✓ Dataset downloaded to: {path}")
    
    # Create training_data directory structure
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    training_data_dir = os.path.join(base_dir, 'training_data')
    
    print(f"\n2. Preparing training directory: {training_data_dir}")
    
    # Create all skin type folders
    skin_types = ['normal', 'oily', 'dry', 'combination', 'sensitive']
    for skin_type in skin_types:
        os.makedirs(os.path.join(training_data_dir, skin_type), exist_ok=True)
    
    # Map downloaded folders to our structure
    print("\n3. Organizing images...")
    
    # The Kaggle dataset has: Oily/, Dry/, Normal/
    # We need to map them to our structure
    kaggle_to_our_mapping = {
        'Oily': 'oily',
        'oily': 'oily',
        'Dry': 'dry',
        'dry': 'dry',
        'Normal': 'normal',
        'normal': 'normal'
    }
    
    # Find and copy images
    downloaded_path = Path(path)
    image_count = {'normal': 0, 'oily': 0, 'dry': 0}
    
    # Search for image folders in downloaded path
    for item in downloaded_path.rglob('*'):
        if item.is_dir():
            folder_name = item.name
            if folder_name in kaggle_to_our_mapping:
                target_folder = kaggle_to_our_mapping[folder_name]
                target_path = os.path.join(training_data_dir, target_folder)
                
                print(f"\n   Processing {folder_name}/ → {target_folder}/")
                
                # Copy all images from this folder
                for img_file in item.glob('*'):
                    if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                        try:
                            target_file = os.path.join(target_path, img_file.name)
                            shutil.copy2(img_file, target_file)
                            image_count[target_folder] += 1
                        except Exception as e:
                            print(f"   ⚠ Error copying {img_file.name}: {e}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("✓ DATASET PREPARATION COMPLETE")
    print("=" * 60)
    print(f"\nImages organized:")
    print(f"  • Normal: {image_count['normal']} images")
    print(f"  • Oily: {image_count['oily']} images")
    print(f"  • Dry: {image_count['dry']} images")
    print(f"  • Combination: 0 images (will need augmentation)")
    print(f"  • Sensitive: 0 images (will need augmentation)")
    
    total = sum(image_count.values())
    print(f"\n  Total: {total} images")
    
    # Handle missing categories
    if image_count['normal'] > 0 and image_count['oily'] == 0:
        print("\n⚠ Note: Dataset has limited categories.")
        print("   We'll create synthetic data for missing categories.")
    
    return training_data_dir, image_count


def create_synthetic_data(training_data_dir, image_count):
    """
    Create synthetic data for Combination and Sensitive types
    using augmentation from existing images
    """
    print("\n" + "=" * 60)
    print("🎨 CREATING SYNTHETIC DATA FOR MISSING CATEGORIES")
    print("=" * 60)
    
    from tensorflow.keras.preprocessing.image import ImageDataGenerator, load_img, img_to_array
    import numpy as np
    from PIL import Image
    
    # Create augmentation generator
    datagen = ImageDataGenerator(
        rotation_range=15,
        width_shift_range=0.15,
        height_shift_range=0.15,
        brightness_range=[0.8, 1.2],
        horizontal_flip=True,
        zoom_range=0.15,
        fill_mode='nearest'
    )
    
    # Create combination images (mix of oily T-zone + dry cheeks)
    print("\n1. Creating Combination skin type images...")
    combination_dir = os.path.join(training_data_dir, 'combination')
    
    if image_count['oily'] > 0 and image_count['normal'] > 0:
        # Mix oily and normal images
        oily_dir = os.path.join(training_data_dir, 'oily')
        normal_dir = os.path.join(training_data_dir, 'normal')
        
        oily_images = list(Path(oily_dir).glob('*.jpg'))[:20]
        normal_images = list(Path(normal_dir).glob('*.jpg'))[:20]
        
        for idx, (oily_img_path, normal_img_path) in enumerate(zip(oily_images, normal_images)):
            try:
                # Create blended image
                img1 = Image.open(oily_img_path).convert('RGB').resize((224, 224))
                img2 = Image.open(normal_img_path).convert('RGB').resize((224, 224))
                
                # Blend
                blended = Image.blend(img1, img2, alpha=0.5)
                
                output_path = os.path.join(combination_dir, f'combination_{idx}.jpg')
                blended.save(output_path)
                
                # Create augmented versions
                img_array = img_to_array(blended)
                img_array = np.expand_dims(img_array, axis=0)
                
                aug_iter = datagen.flow(img_array, batch_size=1)
                for aug_idx in range(3):
                    aug_img = next(aug_iter)[0].astype('uint8')
                    aug_output = os.path.join(combination_dir, f'combination_{idx}_aug{aug_idx}.jpg')
                    Image.fromarray(aug_img).save(aug_output)
                
            except Exception as e:
                print(f"   ⚠ Error creating combination image {idx}: {e}")
        
        combination_count = len(list(Path(combination_dir).glob('*.jpg')))
        print(f"   ✓ Created {combination_count} combination images")
    
    # Create sensitive images (add redness overlay)
    print("\n2. Creating Sensitive skin type images...")
    sensitive_dir = os.path.join(training_data_dir, 'sensitive')
    
    if image_count['normal'] > 0:
        normal_dir = os.path.join(training_data_dir, 'normal')
        normal_images = list(Path(normal_dir).glob('*.jpg'))[:20]
        
        for idx, normal_img_path in enumerate(normal_images):
            try:
                # Load image
                img = Image.open(normal_img_path).convert('RGB').resize((224, 224))
                img_array = np.array(img)
                
                # Add redness (increase red channel)
                img_array[:, :, 0] = np.clip(img_array[:, :, 0] * 1.15, 0, 255)
                
                sensitive_img = Image.fromarray(img_array.astype('uint8'))
                
                output_path = os.path.join(sensitive_dir, f'sensitive_{idx}.jpg')
                sensitive_img.save(output_path)
                
                # Create augmented versions
                img_array_exp = np.expand_dims(img_array, axis=0)
                aug_iter = datagen.flow(img_array_exp, batch_size=1)
                
                for aug_idx in range(3):
                    aug_img = next(aug_iter)[0].astype('uint8')
                    aug_output = os.path.join(sensitive_dir, f'sensitive_{idx}_aug{aug_idx}.jpg')
                    Image.fromarray(aug_img).save(aug_output)
                
            except Exception as e:
                print(f"   ⚠ Error creating sensitive image {idx}: {e}")
        
        sensitive_count = len(list(Path(sensitive_dir).glob('*.jpg')))
        print(f"   ✓ Created {sensitive_count} sensitive images")
    
    print("\n✓ Synthetic data creation complete")


if __name__ == '__main__':
    # Download and prepare dataset
    training_dir, counts = download_and_prepare_dataset()
    
    # Create synthetic data for missing categories
    if counts['normal'] > 0:
        create_synthetic_data(training_dir, counts)
    
    print("\n" + "=" * 60)
    print("🎓 READY TO TRAIN!")
    print("=" * 60)
    print(f"\nRun: python ml_model/train_model.py")