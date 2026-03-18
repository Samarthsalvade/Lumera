#!/bin/bash

echo "🚀 Luméra ML Model Setup & Training"
echo "===================================="

# Step 1: Download dataset
echo ""
echo "Step 1: Downloading Kaggle dataset..."
python ml_model/download_dataset.py

# Step 2: Train model
echo ""
echo "Step 2: Training model..."
python ml_model/train_kaggle_model.py

echo ""
echo "✓ Setup complete!"
echo "Model ready at: ml_model/skin_type_model.h5"