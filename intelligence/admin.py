"""Configuration d'administration de l'application intelligence."""
from django.contrib import admin
from . import models

# Enregistrement automatique des modèles concrets de l'application.
for nom in dir(models):
    objet=getattr(models,nom)
    try:
        if hasattr(objet,"_meta") and not objet._meta.abstract:
            admin.site.register(objet)
    except admin.sites.AlreadyRegistered:
        pass
