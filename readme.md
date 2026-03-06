## Automatiser tous les lundis soir

Utiliser cron.

Ouvre la crontab :

crontab -e

Ajouter :

0 21 * * 1 /home/YOANN/babyfoot-jft/backup.sh

Explication :

0 21 * * 1
│ │  │ │ │
│ │  │ │ └── lundi
│ │  │ └──── tous les mois
│ │  └────── tous les jours
│ └───────── 21h
└─────────── minute 0

Donc :

👉 tous les lundis à 21h