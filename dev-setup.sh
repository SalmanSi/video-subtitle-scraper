#!/bin/bash

# dev-setup.sh - Setup script for local development

echo "🛠️  Setting up Video Subtitle Scraper for local development..."

# Backend setup
echo "📦 Setting up backend..."
cd backend

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "✅ Backend setup complete"

# Return to root directory
cd ..

# Frontend setup
echo "📦 Setting up frontend..."
cd frontend

# Install Node dependencies
echo "Installing Node.js dependencies..."
npm install

echo "✅ Frontend setup complete"

# Return to root directory
cd ..

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📋 Creating .env file from .env.example..."
    cp .env.example .env
fi

echo ""
echo "🎉 Development setup complete!"
echo ""
echo "To start development servers:"
echo ""
echo "Backend (in one terminal):"
echo "  cd backend"
echo "  source .venv/bin/activate"
echo "  uvicorn src.app:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "Frontend (in another terminal):"
echo "  cd frontend"
echo "  npm run dev"
echo ""
echo "Or use Docker:"
echo "  ./start.sh"
