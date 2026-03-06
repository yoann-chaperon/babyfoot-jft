#!/bin/bash

echo "⚽ Installation Babyfoot JFT sur Ubuntu..."

# Mettre à jour et installer Python3 + pip
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install --upgrade pip
pip install flask flask_sqlalchemy flask_socketio eventlet werkzeug

# Créer dossier img si non existant
mkdir -p static/img

# Créer fichier de base SQLite vide si inexistant
touch babyfoot.db

# Créer run.sh
cat <<EOF > run.sh
#!/bin/bash
source venv/bin/activate
python3 app.py
EOF
chmod +x run.sh

echo ""
echo "✅ Installation terminée !"
echo "Pour lancer le projet : ./run.sh"