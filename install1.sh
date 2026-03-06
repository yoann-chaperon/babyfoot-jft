#!/bin/bash

echo "⚽ Installation projet Babyfoot JFT"

PROJECT="babyfoot-jft"

echo "📁 Création du projet"

mkdir -p $PROJECT
cd $PROJECT

mkdir -p database
mkdir -p templates
mkdir -p static/css
mkdir -p static/js
mkdir -p static/img

echo "📄 Création des fichiers"

touch app.py
touch requirements.txt

touch database/models.py

touch templates/index.html
touch templates/global.html
touch templates/player.html

touch static/css/style.css
touch static/js/main.js
touch static/js/charts.js

touch static/img/default.png

touch run.sh

echo "🐍 Création environnement Python"

python3 -m venv venv

source venv/bin/activate

pip install flask flask_sqlalchemy flask_socketio eventlet

echo "▶ Script lancement"

cat <<EOF > run.sh
#!/bin/bash
source venv/bin/activate
python3 app.py
EOF

chmod +x run.sh

echo ""
echo "✅ Installation terminée"
echo ""
echo "Structure créée :"
echo ""

tree .

echo ""
echo "🚀 Pour lancer le projet :"
echo ""

echo "cd $PROJECT"
echo "./run.sh"
echo ""
echo "Puis ouvrir :"
echo "http://localhost:5070"