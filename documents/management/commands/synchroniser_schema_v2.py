"""Répare sans perte les colonnes V2 manquantes dans une base Chantial existante.

Cette commande existe pour les installations ayant appliqué une ancienne migration
initiale avant l'ajout de champs V2. Elle n'efface aucune donnée et n'altère pas
les colonnes déjà présentes.
"""
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Ajoute les tables/colonnes Chantial manquantes sans supprimer les données existantes."

    def handle(self, *args, **options):
        applications = {"comptes", "projets", "finances", "documents", "intelligence", "interactions", "audit"}
        modeles = [m for m in apps.get_models() if m._meta.app_label in applications and m._meta.managed and not m._meta.proxy]

        with connection.cursor() as cursor:
            tables = set(connection.introspection.table_names(cursor))

        # D'abord les tables totalement absentes, dans l'ordre fourni par Django.
        with connection.schema_editor() as schema:
            for modele in modeles:
                table = modele._meta.db_table
                if table not in tables:
                    self.stdout.write(f"Création de la table manquante : {table}")
                    schema.create_model(modele)
                    tables.add(table)

        # Puis les colonnes absentes des tables déjà existantes.
        with connection.schema_editor() as schema:
            for modele in modeles:
                table = modele._meta.db_table
                with connection.cursor() as cursor:
                    description = connection.introspection.get_table_description(cursor, table)
                colonnes = {c.name for c in description}
                for champ in modele._meta.local_fields:
                    if champ.column not in colonnes:
                        self.stdout.write(f"Ajout de la colonne : {table}.{champ.column}")
                        schema.add_field(modele, champ)
                        colonnes.add(champ.column)

        self.stdout.write(self.style.SUCCESS("Schéma V2 synchronisé sans suppression de données."))
