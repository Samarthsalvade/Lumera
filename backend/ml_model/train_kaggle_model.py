import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
import numpy as np
import json
import os
import matplotlib.pyplot as plt
from datetime import datetime

def train_with_kaggle_dataset():
    """
    Optimized training for the Kaggle skin type dataset
    """
    print("=" * 60)
    print("🎓 TRAINING SKIN TYPE CLASSIFIER")
    print("   Dataset: Oily, Dry, Normal (+ Synthetic)")
    print("=" * 60)
    
    # Configuration
    IMG_HEIGHT = 224
    IMG_WIDTH = 224
    BATCH_SIZE = 16  # Smaller batch for limited data
    EPOCHS = 50      # More epochs for smaller dataset
    DATA_DIR = 'training_data'
    MODEL_DIR = 'ml_model'
    
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Data augmentation (aggressive for small dataset)
    train_datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=25,
        width_shift_range=0.25,
        height_shift_range=0.25,
        shear_range=0.2,
        zoom_range=0.25,
        horizontal_flip=True,
        brightness_range=[0.7, 1.3],
        fill_mode='nearest',
        validation_split=0.2
    )
    
    val_datagen = ImageDataGenerator(
        rescale=1./255,
        validation_split=0.2
    )
    
    # Create generators
    print("\n📁 Loading dataset...")
    train_generator = train_datagen.flow_from_directory(
        DATA_DIR,
        target_size=(IMG_HEIGHT, IMG_WIDTH),
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='training',
        shuffle=True
    )
    
    val_generator = val_datagen.flow_from_directory(
        DATA_DIR,
        target_size=(IMG_HEIGHT, IMG_WIDTH),
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='validation',
        shuffle=False
    )
    
    print(f"✓ Training samples: {train_generator.samples}")
    print(f"✓ Validation samples: {val_generator.samples}")
    print(f"✓ Classes: {list(train_generator.class_indices.keys())}")
    
    # Save class indices
    with open(os.path.join(MODEL_DIR, 'class_indices.json'), 'w') as f:
        json.dump(train_generator.class_indices, f)
    
    # Build model
    print("\n🏗️ Building model...")
    base_model = MobileNetV2(
        input_shape=(IMG_HEIGHT, IMG_WIDTH, 3),
        include_top=False,
        weights='imagenet'
    )
    base_model.trainable = False
    
    model = keras.Sequential([
        base_model,
        layers.GlobalAveragePooling2D(),
        layers.BatchNormalization(),
        layers.Dropout(0.4),
        layers.Dense(256, activation='relu', kernel_regularizer=keras.regularizers.l2(0.001)),
        layers.BatchNormalization(),
        layers.Dropout(0.4),
        layers.Dense(128, activation='relu', kernel_regularizer=keras.regularizers.l2(0.001)),
        layers.Dropout(0.3),
        layers.Dense(5, activation='softmax')
    ])
    
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    print("✓ Model built")
    model.build(input_shape=(None, 224, 224, 3))

    model.summary()
    
    # Callbacks
    checkpoint = ModelCheckpoint(
        os.path.join(MODEL_DIR, 'best_model.keras'),
        monitor='val_accuracy',
        save_best_only=True,
        mode='max',
        verbose=1,

    )
    
    early_stop = EarlyStopping(
        monitor='val_accuracy',
        patience=15,
        restore_best_weights=True,
        verbose=1
    )
    
    reduce_lr = ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=7,
        min_lr=1e-7,
        verbose=1
    )
    
    # Train
    print(f"\n🚀 Training for {EPOCHS} epochs...")
    history = model.fit(
        train_generator,
        epochs=EPOCHS,
        validation_data=val_generator,
        callbacks=[checkpoint, early_stop, reduce_lr],
        verbose=1
    )
    
    # Fine-tune
    print("\n🔧 Fine-tuning...")
    base_model.trainable = True
    
    # Freeze first 100 layers
    for layer in base_model.layers[:100]:
        layer.trainable = False
    
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.0001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    history_fine = model.fit(
        train_generator,
        epochs=20,
        validation_data=val_generator,
        callbacks=[checkpoint, early_stop, reduce_lr],
        verbose=1
    )
    
    # Evaluate
    print("\n📊 Final evaluation...")
    results = model.evaluate(val_generator)
    print(f"✓ Validation Loss: {results[0]:.4f}")
    print(f"✓ Validation Accuracy: {results[1]:.4f}")
    
    # Save
    model.save(os.path.join(MODEL_DIR, 'skin_type_model.h5'))
    print(f"✓ Model saved to {MODEL_DIR}/skin_type_model.h5")
    
    # Plot
    plt.figure(figsize=(12, 4))
    
    plt.subplot(1, 2, 1)
    plt.plot(history.history['accuracy'] + history_fine.history['accuracy'])
    plt.plot(history.history['val_accuracy'] + history_fine.history['val_accuracy'])
    plt.title('Model Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend(['Train', 'Val'])
    plt.grid(True)
    
    plt.subplot(1, 2, 2)
    plt.plot(history.history['loss'] + history_fine.history['loss'])
    plt.plot(history.history['val_loss'] + history_fine.history['val_loss'])
    plt.title('Model Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend(['Train', 'Val'])
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig(os.path.join(MODEL_DIR, 'training_history.png'))
    print(f"✓ Training plot saved")
    
    print("\n" + "=" * 60)
    print("✓ TRAINING COMPLETE!")
    print("=" * 60)
    
    return model


if __name__ == '__main__':
    trained_model = train_with_kaggle_dataset()