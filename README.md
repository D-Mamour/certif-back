# Chantial — Backend Django modulaire

Cette version organise le backend par **domaines métier** et non par diagrammes de séquence.

## Applications

- `comptes` : utilisateur, rôles, JWT et profil.
- `projets` : projet, étape et avancement.
- `finances` : dépenses, validation et rejet.
- `documents` : justificatifs, documents projet et OCR.
- `intelligence` : analyse, anomalies, recommandations et RAG.
- `interactions` : demandes et alertes.
- `audit` : historique et traçabilité.

## Démarrage

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d
python manage.py makemigrations comptes projets finances documents intelligence interactions audit
python manage.py migrate
python manage.py check
python manage.py createsuperuser
python manage.py test
python manage.py runserver
```

Swagger : `http://127.0.0.1:8000/api/docs/`

## Important concernant l'IA

L'architecture RAG est séparée et prête à recevoir un moteur d'embeddings, une base
vectorielle et un LLM. Cette archive **ne prétend pas fournir un RAG de production
déjà branché** : `ServiceRAG` expose les points d'intégration nécessaires.
Même une fois le LLM connecté, la validation finale d'une dépense reste une décision
du bailleur.

Le service OCR suit la même logique : son interface est prête, mais le moteur OCR réel
(Tesseract, EasyOCR ou fournisseur externe) doit être configuré.

## Préparation locale pour la démonstration OCR (macOS)

Chantial lance automatiquement l'OCR lorsqu'un entrepreneur dépose un justificatif image.

```bash
brew install tesseract tesseract-lang
python -m pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py runserver 8000
```

Les PDF contenant déjà une couche texte sont lus directement avec `pypdf`. Pour une démonstration OCR visuelle, utiliser de préférence une facture JPG/PNG nette. Si Tesseract n'est pas disponible, le justificatif est quand même conservé et l'API indique que l'OCR est indisponible au lieu de perdre le document.

### Diagnostic OCR avant la démonstration

Le backend expose `GET /api/justificatifs/etat-ocr/` pour confirmer que Tesseract est réellement disponible. La réponse attendue contient `"disponible": true` et la version détectée. La relance d'un justificatif utilise `POST /api/justificatifs/{id}/relancer-ocr/`.

Sur Mac Intel :

```bash
brew install tesseract tesseract-lang
export TESSERACT_CMD=/usr/local/bin/tesseract
```

Le service tente aussi automatiquement `which tesseract`, `/usr/local/bin/tesseract` et `/opt/homebrew/bin/tesseract`.
