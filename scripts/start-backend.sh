#!/bin/bash
# Start Django backend server

cd "$(dirname "$0")/.."
source venv/Scripts/activate
python manage.py runserver
