"""Traçabilité des actions importantes."""
import uuid
from django.conf import settings
from django.db import models

class Historique(models.Model):
    """Conserve une trace d'audit des opérations importantes."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    utilisateur=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="historique_actions")
    projet_id=models.UUIDField(null=True,blank=True)
    action=models.CharField(max_length=120)
    description=models.TextField(blank=True)
    donnees=models.JSONField(default=dict,blank=True)
    date_action=models.DateTimeField(auto_now_add=True)
    hash_precedent=models.CharField(max_length=64,blank=True)
    hash_evenement=models.CharField(max_length=64,blank=True,unique=True,null=True)
    class Meta:
        ordering=["-date_action"]
