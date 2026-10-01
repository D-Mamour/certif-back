"""Pipeline RAG Chantial avec Hugging Face."""
import math
import os
import requests
from intelligence.models import FragmentDocument
from documents.services.extraction import ServiceExtraction
from .embeddings import ServiceEmbeddings

class ServiceRAG:
    """Indexation, recherche sémantique et génération contextualisée."""
    def __init__(self):
        """Configure Hugging Face et les composants RAG."""
        self.embeddings = ServiceEmbeddings()
        self.extraction = ServiceExtraction()
        self.modele = os.getenv("HF_GENERATION_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
        self.token = os.getenv("HF_TOKEN", "").strip()
        self.url = f"https://router.huggingface.co/hf-inference/models/{self.modele}"

    @staticmethod
    def decouper(texte, taille=900, chevauchement=150):
        """Découpe le texte en fragments."""
        texte = (texte or "").strip()
        if not texte:
            return []
        pas = max(1, taille-chevauchement)
        return [texte[i:i+taille] for i in range(0, len(texte), pas)]

    def indexer_document(self, document):
        """Extrait, fragmente, vectorise et enregistre un document."""
        texte = document.texte_extrait or self.extraction.extraire_texte(document)
        if not texte:
            raise ValueError("Aucun texte exploitable n'a été extrait.")
        document.texte_extrait = texte
        document.save(update_fields=["texte_extrait"])
        document.fragments.all().delete()
        fragments = self.decouper(texte)
        vecteurs = self.embeddings.encoder_lot(fragments)
        for ordre, (contenu, vecteur) in enumerate(zip(fragments, vecteurs)):
            FragmentDocument.objects.create(
                document=document, contenu=contenu, ordre=ordre, vecteur=vecteur
            )
        document.est_indexe = True
        document.save(update_fields=["est_indexe"])
        return document

    @staticmethod
    def similarite_cosinus(a, b):
        """Calcule la similarité cosinus entre deux vecteurs."""
        if not a or not b or len(a) != len(b):
            return 0.0
        produit = sum(x*y for x, y in zip(a, b))
        na = math.sqrt(sum(x*x for x in a))
        nb = math.sqrt(sum(y*y for y in b))
        return produit/(na*nb) if na and nb else 0.0

    def rechercher_contexte(self, projet, question, limite=5):
        """Récupère les fragments les plus pertinents du projet."""
        q = self.embeddings.encoder(question)
        fragments = FragmentDocument.objects.filter(
            document__projet=projet, document__est_indexe=True
        ).select_related("document")
        classes = sorted(
            ((self.similarite_cosinus(q, f.vecteur), f) for f in fragments),
            key=lambda x: x[0], reverse=True
        )
        return [{"score":round(s,4),"document":f.document.nom,"contenu":f.contenu}
                for s,f in classes[:limite]]

    def generer(self, prompt):
        """Appelle le modèle génératif via Hugging Face Inference."""
        if not self.token:
            raise RuntimeError("HF_TOKEN absent dans le fichier .env.")
        r = requests.post(
            self.url,
            headers={"Authorization": f"Bearer {self.token}"},
            json={"inputs":prompt,"parameters":{"max_new_tokens":400,"return_full_text":False}},
            timeout=120
        )
        r.raise_for_status()
        data=r.json()
        if isinstance(data,list) and data:
            return data[0].get("generated_text","").strip()
        if isinstance(data,dict):
            return data.get("generated_text","").strip()
        return ""

    def analyser(self, projet, question):
        """Exécute le RAG et retourne la réponse avec ses sources."""
        contexte=self.rechercher_contexte(projet,question)
        passages="\n\n".join(
            f"[Source : {x['document']}] {x['contenu']}" for x in contexte
        )
        prompt=f"""Tu es le module d'aide à la décision de Chantial.
Réponds uniquement à partir du contexte fourni.
N'accuse jamais un acteur de fraude. Décris les écarts et recommande une vérification.

CONTEXTE :
{passages}

QUESTION :
{question}

ANALYSE :"""
        try:
            texte=self.generer(prompt); disponible=True
        except (requests.RequestException,RuntimeError) as erreur:
            texte=f"Analyse générative indisponible : {erreur}"; disponible=False
        return {"question":question,"reponse":texte,
                "llm_disponible":disponible,"sources":contexte}

    def assister(self, projet, question, utilisateur):
        """Répond à une question en combinant données métier et documents RAG.

        Les données sont limitées au projet déjà autorisé par la vue API. Les
        anomalies et recommandations sont réservées au bailleur et à
        l'administrateur afin de respecter la séparation fonctionnelle de Chantial.
        """
        from comptes.models import Utilisateur
        from finances.models import Depense
        from intelligence.models import Anomalie, Recommandation

        depenses = Depense.objects.filter(etape__projet=projet)
        total_depenses = sum((d.montant for d in depenses), 0)
        budget = projet.budget_previsionnel
        reste = budget - total_depenses
        avancement = projet.avancement_global

        lignes = [
            f"Projet : {projet.nom}",
            f"Statut : {projet.statut}",
            f"Budget prévisionnel : {budget} FCFA",
            f"Dépenses déclarées : {total_depenses} FCFA",
            f"Budget restant : {reste} FCFA",
            f"Avancement global : {avancement}%",
            f"Nombre de dépenses : {depenses.count()}",
        ]

        # Les informations d'aide à la décision sont destinées au bailleur.
        if utilisateur.role in (Utilisateur.Role.BAILLEUR, Utilisateur.Role.ADMINISTRATEUR):
            anomalies = Anomalie.objects.filter(projet=projet, statut="OUVERTE")[:5]
            recommandations = Recommandation.objects.filter(projet=projet).order_by("-date_creation")[:5]
            lignes.append(f"Anomalies ouvertes : {Anomalie.objects.filter(projet=projet, statut='OUVERTE').count()}")
            for anomalie in anomalies:
                lignes.append(f"Anomalie ({anomalie.niveau}) : {anomalie.description}")
            for recommandation in recommandations:
                lignes.append(f"Recommandation : {recommandation.titre} — {recommandation.description}")

        contexte_documents = self.rechercher_contexte(projet, question)
        passages = "\n\n".join(
            f"[Document : {source['document']}] {source['contenu']}"
            for source in contexte_documents
        )
        contexte_metier = "\n".join(lignes)

        prompt = f"""Tu es Assistant Chantial, assistant d'un logiciel de suivi BTP.
Réponds en français, de façon concise, professionnelle et compréhensible.
Utilise uniquement les DONNÉES DU PROJET et les DOCUMENTS fournis ci-dessous.
N'invente aucune valeur. Si l'information demandée n'est pas disponible, dis-le clairement.
N'accuse jamais un acteur de fraude. Parle d'écart, de vérification ou d'action recommandée.
Tu aides l'utilisateur à comprendre le chantier ; tu ne prends jamais une décision à sa place.

DONNÉES DU PROJET :
{contexte_metier}

DOCUMENTS :
{passages or 'Aucun document indexé pertinent.'}

QUESTION :
{question}

RÉPONSE :"""
        try:
            reponse = self.generer(prompt)
            disponible = True
        except (requests.RequestException, RuntimeError) as erreur:
            # Le chatbot reste utile même lorsque le fournisseur LLM est indisponible.
            reponse = (
                "Le service génératif est momentanément indisponible. "
                f"Voici les données disponibles : projet {projet.nom}, "
                f"avancement {avancement} %, dépenses {total_depenses} FCFA, "
                f"budget restant {reste} FCFA."
            )
            disponible = False

        return {
            "reponse": reponse,
            "llm_disponible": disponible,
            "projet": str(projet.id),
            "projet_nom": projet.nom,
            "sources": [
                {"document": s["document"], "score": s["score"]}
                for s in contexte_documents
            ],
        }
