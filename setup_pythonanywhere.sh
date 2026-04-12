#!/bin/bash
# ─────────────────────────────────────────────────────────────
# JoyVet Care — PythonAnywhere Setup Script
# Run this ONCE in the PythonAnywhere Bash console:
#   bash setup_pythonanywhere.sh
# ─────────────────────────────────────────────────────────────
set -e

PA_USERNAME=$(whoami)
echo "Setting up JoyVet Care for user: $PA_USERNAME"

# 1. Clone / update the repo
if [ -d ~/joyvet ]; then
  echo "Updating existing repo..."
  cd ~/joyvet && git pull origin main
else
  echo "Cloning repo..."
  git clone https://github.com/gilangmauwp/joyvet.git ~/joyvet
  cd ~/joyvet
fi

# 2. Create virtualenv (Python 3.12)
if [ ! -d ~/.venvs/joyvet ]; then
  echo "Creating virtualenv..."
  python3.12 -m venv ~/.venvs/joyvet
fi

source ~/.venvs/joyvet/bin/activate

# 3. Install dependencies
echo "Installing Python packages (takes ~2 min)..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# 4. Set environment
export DJANGO_SETTINGS_MODULE=joyvet.settings.pythonanywhere
export PA_USERNAME=$PA_USERNAME
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(50))")

# Save env to a file so the web app can read it
cat > ~/.joyvet_env << EOF
export DJANGO_SETTINGS_MODULE=joyvet.settings.pythonanywhere
export PA_USERNAME=$PA_USERNAME
export SECRET_KEY=$SECRET_KEY
EOF
chmod 600 ~/.joyvet_env
echo "source ~/.joyvet_env" >> ~/.bashrc

# 5. Database setup
echo "Running migrations..."
python manage.py migrate --noinput

# 6. Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# 7. Create demo data
echo "Loading demo data..."
python manage.py seed_demo_data

echo ""
echo "══════════════════════════════════════════════"
echo "  Setup complete!"
echo ""
echo "  Now go to the PythonAnywhere Web tab and:"
echo "  1. Click 'Add a new web app'"
echo "  2. Choose 'Manual configuration' → Python 3.12"
echo "  3. Virtualenv path: /home/$PA_USERNAME/.venvs/joyvet"
echo "  4. WSGI file: paste content from ~/joyvet/pythonanywhere_wsgi.py"
echo "  5. In WSGI file, set PA_USERNAME = '$PA_USERNAME'"
echo "  6. Click Reload"
echo ""
echo "  Your clinic URL: https://$PA_USERNAME.pythonanywhere.com"
echo "  Login: admin / joyvet2024"
echo "══════════════════════════════════════════════"
