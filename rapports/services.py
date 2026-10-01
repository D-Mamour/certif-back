"""Rapports PDF et diffusion multicanale (email + WhatsApp Cloud API optionnelle)."""
from io import BytesIO
import os, requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from intelligence.services.controle_financier import ServiceControleFinancier


def generer_rapport_pdf(projet, periode=None):
    out=BytesIO(); doc=SimpleDocTemplate(out,pagesize=A4,rightMargin=36,leftMargin=36,topMargin=36,bottomMargin=36); st=getSampleStyleSheet(); story=[]
    ind=ServiceControleFinancier().indicateurs_evm(projet)
    titre=f"CHANTIAL - Rapport de chantier{(' - '+periode) if periode else ''}"
    story += [Paragraph(titre,st['Title']),Paragraph(projet.nom,st['Heading2']),Paragraph(f"Localisation : {projet.localisation or 'Non renseignée'}",st['BodyText']),Spacer(1,12)]
    data=[['Indicateur','Valeur'],['Budget initial',f"{ind['budget_initial']:,.0f} FCFA"],['Avenants approuvés',f"{ind['avenants_approuves']:,.0f} FCFA"],['Budget révisé',f"{ind['budget_reference']:,.0f} FCFA"],['Dépenses validées',f"{ind['depenses_validees']:,.0f} FCFA"],['Avancement physique',f"{ind['avancement_physique']:.1f} %"],['Consommation budgétaire',f"{ind['consommation_budgetaire']:.1f} %"],['Écart',f"{ind['ecart_points']:.1f} points"],['CPI',f"{ind['CPI']:.2f}" if ind['CPI'] is not None else 'N/A']]
    t=Table(data,colWidths=[220,220]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('GRID',(0,0),(-1,-1),.4,colors.grey),('PADDING',(0,0),(-1,-1),7)])); story += [t,Spacer(1,16)]
    story.append(Paragraph('Dépenses',st['Heading2']))
    depenses=[]
    for e in projet.etapes.all(): depenses.extend(list(e.depenses.all()))
    if periode: depenses=[d for d in depenses if d.date_depense.strftime('%Y-%m')==periode]
    if depenses:
        rows=[['Date','Libellé','Fournisseur','Montant','Statut']]+[[d.date_depense.strftime('%d/%m/%Y'),d.libelle,d.fournisseur or '-',f"{d.montant:,.0f}",d.statut] for d in depenses]
        td=Table(rows,repeatRows=1,colWidths=[65,120,90,90,70]); td.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('GRID',(0,0),(-1,-1),.3,colors.grey),('FONTSIZE',(0,0),(-1,-1),8)])); story += [td]
    else: story.append(Paragraph('Aucune dépense pour la période.',st['BodyText']))
    story += [Spacer(1,14),Paragraph('Alertes et anomalies ouvertes',st['Heading2'])]
    anomalies=projet.anomalies.filter(statut='OUVERTE').order_by('-date_detection')[:30]
    for a in anomalies: story.append(Paragraph(f"• {a.type_anomalie} — {a.description}",st['BodyText']))
    if not anomalies: story.append(Paragraph('Aucune anomalie ouverte.',st['BodyText']))
    story += [Spacer(1,14),Paragraph('Avenants',st['Heading2'])]
    avs=projet.avenants.order_by('-date_creation')[:30]
    for a in avs: story.append(Paragraph(f"• {a.titre} — {a.montant:,.0f} FCFA — {a.get_statut_display()} — impact délai {a.impact_delai_jours} j",st['BodyText']))
    if not avs: story.append(Paragraph('Aucun avenant.',st['BodyText']))
    story += [Spacer(1,14),Paragraph('Journal de chantier',st['Heading2'])]
    js=projet.journal_chantier.order_by('-date_ajout')[:20]
    for j in js:
        geo=f" ({j.latitude}, {j.longitude})" if j.latitude is not None and j.longitude is not None else ''
        story.append(Paragraph(f"• {j.date_ajout:%d/%m/%Y %H:%M}{geo} — {j.commentaire or 'Preuve terrain'}",st['BodyText']))
    if not js: story.append(Paragraph('Aucune preuve terrain.',st['BodyText']))
    story += [Spacer(1,14),Paragraph('Traçabilité',st['Heading2']),Paragraph('Les validations, décisions et opérations importantes sont consignées dans le journal d’audit horodaté de Chantial.',st['BodyText'])]
    doc.build(story); return out.getvalue()


def archiver_rapport(projet, periode, utilisateur=None):
    from projets.models import RapportChantier
    contenu=generer_rapport_pdf(projet,periode)
    rapport,_=RapportChantier.objects.get_or_create(projet=projet,periode=periode,defaults={'genere_par':utilisateur})
    rapport.genere_par=utilisateur or rapport.genere_par
    rapport.fichier.save(f"rapport-chantial-{projet.id}-{periode}.pdf",ContentFile(contenu),save=False); rapport.save()
    return rapport,contenu


def envoyer_email_rapport(projet, rapport, contenu):
    email=getattr(projet.bailleur,'email','')
    if not email: return False,'Email bailleur absent'
    msg=EmailMessage(subject=f"Chantial — Rapport {rapport.periode} — {projet.nom}",body="Bonjour,\n\nVeuillez trouver en pièce jointe le rapport mensuel Chantial de votre chantier.\n",to=[email])
    msg.attach(f"rapport-{rapport.periode}.pdf",contenu,'application/pdf'); msg.send(fail_silently=False)
    rapport.envoye_email=True; rapport.save(update_fields=['envoye_email']); return True,'Email envoyé'


def envoyer_whatsapp_rapport(projet, rapport):
    """Envoie un message WhatsApp via Meta Cloud API si les identifiants sont configurés.
    Le PDF reste téléchargeable dans Chantial ; l'envoi de document public nécessite une URL publique HTTPS.
    """
    token=os.getenv('WHATSAPP_TOKEN',''); phone_id=os.getenv('WHATSAPP_PHONE_NUMBER_ID',''); numero=getattr(projet.bailleur,'telephone','') or ''
    if not (token and phone_id and numero): return False,'WhatsApp non configuré ou téléphone absent'
    url=f"https://graph.facebook.com/v21.0/{phone_id}/messages"
    payload={'messaging_product':'whatsapp','to':numero.replace('+','').replace(' ',''),'type':'text','text':{'body':f"Chantial : le rapport {rapport.periode} du projet « {projet.nom} » est disponible dans votre espace bailleur."}}
    r=requests.post(url,headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'},json=payload,timeout=20)
    if r.ok:
        rapport.envoye_whatsapp=True; rapport.save(update_fields=['envoye_whatsapp']); return True,'WhatsApp envoyé'
    return False,f'WhatsApp: HTTP {r.status_code}'
