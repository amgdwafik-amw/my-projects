#!/usr/bin/env bash
# exit on error
set -o errexit

echo "--- Debugging File Structure ---"
ls -la
if [ -d "oms_backend" ]; then
    echo "oms_backend exists"
    ls -la oms_backend
else
    echo "ERROR: oms_backend directory MISSING!"
fi
echo "--------------------------------"

pip install -r requirements.txt

# Fix for module not found
export PYTHONPATH=$PYTHONPATH:.

python manage.py collectstatic --no-input
python manage.py migrate
