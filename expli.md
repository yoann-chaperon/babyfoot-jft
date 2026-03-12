1️⃣ Import des librairies

from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import datetime, os
from werkzeug.utils import secure_filename

Ces modules servent à :

module                  rôle
Flask               serveur web
render_template     afficher les pages HTML
request             récupérer les données des formulaires
redirect            rediriger vers une autre page
SQLAlchemy          gérer la base SQLite
SocketIO            mise à jour temps réel écran 2
datetime            date des matchs
os                  gestion fichiers
secure_filename     sécuriser les uploads d’images

