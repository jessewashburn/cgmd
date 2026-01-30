#!/bin/bash

# Classical Guitar Music Database - Quick Setup Script
# This script helps complete the Phase 3 setup

echo "==================================="
echo "CGMD Backend Setup"
echo "==================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: python -m venv venv"
    exit 1
fi

echo "✅ Virtual environment found"
echo ""

# Activate virtual environment (instructions)
echo "📋 Step 1: Activate virtual environment"
echo "   Windows: venv\\Scripts\\activate"
echo "   Mac/Linux: source venv/bin/activate"
echo ""
read -p "Press Enter after activating the virtual environment..."

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your MySQL credentials"
    echo ""
    read -p "Press Enter after editing .env..."
fi

echo "✅ .env file found"
echo ""

# Database setup instructions
echo "📋 Step 2: Create MySQL database"
echo "   Run these commands in MySQL:"
echo "   mysql -u root -p"
echo "   CREATE DATABASE cgmd CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"echo "   Or use the schema file:"
echo "   mysql -u root -p cgmd < data/database_schema.sql"echo "   EXIT;"
echo ""
read -p "Press Enter after creating the database..."

# Run migrations
echo "📋 Step 3: Running migrations..."
python manage.py migrate

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migration failed. Please check your database configuration in .env"
    exit 1
fi

echo ""

# Create superuser
echo "📋 Step 4: Create superuser account"
python manage.py createsuperuser

echo ""
echo "==================================="
echo "✅ Setup Complete!"
echo "==================================="
echo ""
echo "To start the development server:"
echo "  python manage.py runserver"
echo ""
echo "Then visit:"
echo "  API: http://localhost:8000/"
echo "  Admin: http://localhost:8000/admin/"
echo ""
echo "Next steps:"
echo "  - Import Sheerpluck data (Phase 3.3)"
echo "  - Create REST API endpoints (Phase 3.4)"
echo "  - Set up API documentation (Phase 3.4)"
echo ""
