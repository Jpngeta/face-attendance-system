#!/bin/bash
# Setup script for Face Attendance System

echo "=========================================="
echo "Face Attendance System - Setup"
echo "=========================================="
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "WARNING: This script is designed for Raspberry Pi"
    echo "Continue anyway? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        exit 1
    fi
fi

# Check Python version
echo "[1/7] Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Create virtual environment
echo ""
echo "[2/7] Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo ""
echo "[3/7] Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "[4/7] Installing Python dependencies..."
echo "This may take several minutes..."
pip install -r requirements.txt

# Create .env file
echo ""
echo "[5/7] Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env file from template"
    echo "Please edit .env to customize your configuration"
else
    echo ".env file already exists"
fi

# Create necessary directories
echo ""
echo "[6/7] Creating directories..."
mkdir -p uploads
mkdir -p static/css
mkdir -p static/js
mkdir -p templates
mkdir -p insightface_dataset
echo "Directories created"

# Initialize database
echo ""
echo "[7/7] Initializing database..."
python migrate_to_database.py

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review and edit .env file if needed"
echo "2. Register students using: python insightface_capture.py"
echo "3. Train the model: python insightface_training.py"
echo "4. Run migration again: python migrate_to_database.py"
echo "5. Start the web app: python app.py"
echo "6. Access dashboard at: http://localhost:5000"
echo ""
echo "For Google Sheets integration:"
echo "1. Place credentials.json in project root"
echo "2. Set GOOGLE_SHEETS_ENABLED=true in .env"
echo "3. Add GOOGLE_SHEET_ID to .env"
echo ""
echo "=========================================="
