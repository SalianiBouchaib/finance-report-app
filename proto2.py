import streamlit as st
import pandas as pd
from PIL import Image
import json
import os
from pathlib import Path
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Configuration de la page
st.set_page_config(
    page_title="Rapport ",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Fichier de sauvegarde
SAVE_FILE = "glove_voice_data.json"

# Charger les données existantes
def load_data():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    return {}

# Sauvegarder les données
def save_data(data):
    with open(SAVE_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Charger les anciennes entrées
saved_data = load_data()

# Fonction pour créer des inputs avec persistance
def create_input(label, default_value="", key=None, text_area=False, height=None):
    # Récupérer la valeur sauvegardée si elle existe
    saved_value = saved_data.get(key, default_value)
    
    if text_area:
        if height:
            user_input = st.text_area(label, value=saved_value, key=key, height=height)
        else:
            user_input = st.text_area(label, value=saved_value, key=key)
    else:
        user_input = st.text_input(label, value=saved_value, key=key)
    
    # Sauvegarder automatiquement quand il y a un changement
    if user_input != saved_data.get(key):
        saved_data[key] = user_input
        save_data(saved_data)
    
    return user_input

# Fonction pour les tables éditables avec persistance
def create_editable_table(data, key):
    # Récupérer les données sauvegardées
    saved_table = saved_data.get(key, data)
    df = pd.DataFrame(saved_table)
    
    # Créer l'éditeur de données
    edited_df = st.data_editor(df, key=key, num_rows="dynamic")
    
    # Sauvegarder si des modifications sont détectées
    if not edited_df.equals(df):
        saved_data[key] = edited_df.to_dict('records')
        save_data(saved_data)
    
    return edited_df

def create_expandable_table(title, data, key):
    with st.expander(title):
        return create_editable_table(data, key)

# Fonction pour créer le tableau de comparaison des concurrents avec inputs
def create_competitor_comparison_table(key):
    # Définir les critères et concurrents
    criteres = [
        "Traduction en temps réel", 
        "Application mobile", 
        "Portail web", 
        "Support multilingue", 
        "Formation en langue des signes", 
        "Personnalisation pour secteurs", 
        "Partenariats avec ONG/écoles", 
        "Tarification différenciée"
    ]
    
    concurrents = ["Glove Voice", "SignAll", "MotionSavvy", "Kinemic", "DuoSign", "Google Live Transcribe", "Ava"]
    
    # Valeurs par défaut du tableau
    default_values = {
        "Critères/Concurrents": criteres,
        "Glove Voice": ["+", "+", "+", "+", "+", "+", "+", "+"],
        "SignAll": ["+", "-", "-", "-", "-", "-", "T", "T"],
        "MotionSavvy": ["+", "-", "-", "-", "-", "-", "T", "T"],
        "Kinemic": ["-", "-", "-", "-", "-", "-", "-", "-"],
        "DuoSign": ["-", "-", "-", "-", "-", "-", "T", "-"],
        "Google Live Transcribe": ["-", "+", "-", "+", "-", "-", "-", "+"],
        "Ava": ["-", "+", "-", "+", "-", "-", "-", "+"]
    }
    
    # Récupérer les données sauvegardées ou utiliser les valeurs par défaut
    saved_table = saved_data.get(key, default_values)
    
    # Créer le dataframe
    df = pd.DataFrame(saved_table)
    df = df.set_index("Critères/Concurrents")
    
    # Permettre l'édition des valeurs du tableau
    st.write("### Tableau Comparatif Détaillé des Concurrents")
    st.write("Modifiez les valeurs en cliquant dessus (+ : présent, - : absent, T : partiellement présent)")
    
    edited_df = st.data_editor(
        df, 
        key=key,
        height=400,
        use_container_width=True
    )
    
    # Sauvegarder les modifications
    if not edited_df.equals(df):
        # Ajouter la colonne d'index comme une colonne normale pour la sauvegarde
        edited_df_save = edited_df.reset_index()
        saved_data[key] = edited_df_save.to_dict('list')
        save_data(saved_data)
    
    # Afficher la légende
    st.write("**Légende :**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("• + : Service présent")
    with col2:
        st.write("• - : Service absent")
    with col3:
        st.write("• T : Service partiellement présent")
    
    return edited_df

# Fonction pour créer le Business Model Canvas avec inputs
def create_business_model_canvas(key_prefix):
    st.write("## 7. Business Model Canvas (BMC) de Glove Voice")
    
    # Définir les couleurs pour chaque section du BMC (comme dans l'image)
    bmc_colors = {
        "partenaires": "#ffadb9",    # Rose
        "activites": "#b388ff",      # Violet
        "proposition": "#81c784",     # Vert
        "relations": "#ffb74d",      # Orange
        "segments": "#4fc3f7",       # Bleu
        "ressources": "#b388ff",     # Violet (même que activités)
        "canaux": "#ffb74d",         # Orange (même que relations)
        "couts": "#ffd54f",          # Jaune
        "revenus": "#b388ff"         # Violet (même que activités/ressources)
    }
    
    # Créer le canvas avec 3 rangées
    st.write("#### Cliquez dans chaque case pour modifier le contenu")
    
    # Première rangée: Partenaires Clés, Activités Clés, Proposition de Valeur, Relations avec les Clients, Segments de Clientèle
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"<div style='background-color:{bmc_colors['partenaires']};padding:10px;border-radius:5px;height:250px;'>", unsafe_allow_html=True)
        st.write("**Partenaires Clés**")
        partenaires = create_input("", 
                                 "- ONG et Associations : Pour une meilleure diffusion et impact social\n- Établissements Éducatifs : Partenariats pour intégrer Glove Voice dans leur cursus\n- Développeurs : Soutien technique et mises à jour du produit",
                                 f"{key_prefix}_partenaires",
                                 text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"<div style='background-color:{bmc_colors['activites']};padding:10px;border-radius:5px;height:250px;'>", unsafe_allow_html=True)
        st.write("**Activités Clés**")
        activites = create_input("", 
                                "- Développement Produit : Amélioration continue de Glove Voice\n- Marketing et Promotion : Campagnes pour sensibiliser et attirer des clients\n- Support et Formation : Assistance technique et formation pour les utilisateurs",
                                f"{key_prefix}_activites",
                                text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"<div style='background-color:{bmc_colors['proposition']};padding:10px;border-radius:5px;height:250px;'>", unsafe_allow_html=True)
        st.write("**Proposition de Valeur**")
        proposition = create_input("", 
                                  "- Traduction en temps réel de la langue des signes : Facilite la communication entre personnes sourdes et entendantes\n- Accessibilité Multilingue : Adaptation aux divers besoins culturels\n- Formation à la langue des signes : Sensibilisation et éducation pour promouvoir l'inclusion\n- Personnalisation : Solutions adaptées aux besoins spécifiques de chaque secteur",
                                  f"{key_prefix}_proposition",
                                  text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"<div style='background-color:{bmc_colors['relations']};padding:10px;border-radius:5px;height:250px;'>", unsafe_allow_html=True)
        st.write("**Relations avec les Clients**")
        relations = create_input("", 
                               "- Support Client : Assistance technique et service après-vente\n- Formation et Sensibilisation : Sessions de formation pour les utilisateurs\n- Feedback Utilisateur : Récolte des retours pour améliorer le produit",
                               f"{key_prefix}_relations",
                               text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"<div style='background-color:{bmc_colors['segments']};padding:10px;border-radius:5px;height:250px;'>", unsafe_allow_html=True)
        st.write("**Segments de Clientèle**")
        segments = create_input("", 
                              "- ONG et Associations : Œuvrant pour l'inclusion des personnes sourdes et muettes\n- Établissements Éducatifs : Écoles et universités cherchant à sensibiliser à la langue des signes\n- Entreprises : Sociétés désirant améliorer leur inclusion sociale\n- Particuliers : Utilisateurs souhaitant apprendre et communiquer en langue des signes",
                              f"{key_prefix}_segments",
                              text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Deuxième rangée: vide, Ressources Clés, vide, Canaux, vide
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.write("")
    
    with col2:
        st.markdown(f"<div style='background-color:{bmc_colors['ressources']};padding:10px;border-radius:5px;height:230px;'>", unsafe_allow_html=True)
        st.write("**Ressources Clés**")
        ressources = create_input("", 
                                "- Technologie IA : Développement de l'algorithme de traduction\n- Équipe technique : Développeurs et experts en langue des signes\n- Partenariats Stratégiques : Collaborations avec ONG et institutions éducatives",
                                f"{key_prefix}_ressources",
                                text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        st.write("")
    
    with col4:
        st.markdown(f"<div style='background-color:{bmc_colors['canaux']};padding:10px;border-radius:5px;height:230px;'>", unsafe_allow_html=True)
        st.write("**Canaux**")
        canaux = create_input("", 
                            "- Application Mobile : Disponible sur iOS et Android\n- Portail Web : Accès en ligne pour les utilisateurs\n- Partenariats : Collaboration avec écoles, ONG et entreprises\n- Démonstrations et Ateliers : Présentations dans des établissements éducatifs pour promouvoir Glove Voice",
                            f"{key_prefix}_canaux",
                            text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col5:
        st.write("")
    
    # Troisième rangée: Structure de Coûts, vide, vide, vide, Sources de Revenus
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        st.markdown(f"<div style='background-color:{bmc_colors['couts']};padding:10px;border-radius:5px;height:150px;'>", unsafe_allow_html=True)
        st.write("**Structure de Coûts**")
        couts = create_input("", 
                           "- Développement Technologique : Coûts liés à la création et à la maintenance de l'application et du portail\n- Marketing et Communication : Dépenses pour la promotion et les événements\n- Support Client : Coûts associés à l'assistance technique et à la formation",
                           f"{key_prefix}_couts",
                           text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.write("")
    
    with col3:
        st.markdown(f"<div style='background-color:{bmc_colors['revenus']};padding:10px;border-radius:5px;height:150px;'>", unsafe_allow_html=True)
        st.write("**Sources de Revenus**")
        revenus = create_input("", 
                             "- Vente de Licences : Tarification adaptée pour écoles, entreprises et ONG\n- Abonnements : Offres mensuelles ou annuelles pour l'utilisation du service\n- Options Premium : Modèle gratuit pour utilisateurs éducatifs ou petites entreprises, avec extensions payantes",
                             f"{key_prefix}_revenus",
                             text_area=True)
        st.markdown("</div>", unsafe_allow_html=True)

# Fonction pour générer le PDF
def generate_pdf():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'title',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    heading1_style = ParagraphStyle(
        'Heading1',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=10
    )
    heading2_style = ParagraphStyle(
        'Heading2',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=8
    )
    normal_style = styles['Normal']
    
    # Titre principal
    story.append(Paragraph(saved_data.get('projet_titre', "Glove Voice - Rapport Complet"), title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Présentation du projet
    story.append(Paragraph("PRÉSENTATION DU PROJET", heading1_style))
    
    # Description du projet
    story.append(Paragraph("1. Description du Projet", heading2_style))
    story.append(Paragraph(f"<b>Problématique :</b> {saved_data.get('pres_prob', '')}", normal_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Processez les retours à la ligne pour les champs texte
    solution_lines = saved_data.get('pres_solution', '').split('\n')
    story.append(Paragraph("<b>Solution proposée :</b>", normal_style))
    for line in solution_lines:
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Fiche d'identité
    story.append(Paragraph("2. Fiche d'Identité", heading2_style))
    identity_data = [
        ["Information", "Détail"],
        ["Raison sociale", saved_data.get('ident_rs', '')],
        ["Slogan", saved_data.get('ident_slogan', '')],
        ["Objet social", saved_data.get('ident_objet_social', '')],
        ["Domaines d'activité", saved_data.get('ident_domaines', '')],
        ["Siège social", saved_data.get('ident_siege', '')],
        ["Forme juridique", saved_data.get('ident_forme', '')],
        ["Nombre d'associés", saved_data.get('ident_associes', '')],
        ["Valeurs", saved_data.get('ident_valeurs', '')]
    ]
    
    identity_table = Table(identity_data, colWidths=[doc.width/3.0, doc.width*2/3.0])
    identity_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(identity_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Objectifs et Vision
    story.append(Paragraph("3. Objectifs et Vision", heading2_style))
    story.append(Paragraph("<b>Objectifs Principaux :</b>", normal_style))
    for line in saved_data.get('pres_objectifs', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("<b>Objectifs de Développement Durable :</b>", normal_style))
    for line in saved_data.get('pres_odd', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(f"<b>Mission :</b> {saved_data.get('pres_mission', '')}", normal_style))
    story.append(Paragraph(f"<b>Vision :</b> {saved_data.get('pres_vision', '')}", normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Réalisations
    story.append(Paragraph("4. Réalisations Accomplies", heading2_style))
    for line in saved_data.get('pres_realisations', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Analyse de Marché
    story.append(Paragraph("ANALYSE DE MARCHÉ", heading1_style))
    
    # Tendances
    story.append(Paragraph("1. Tendances du Marché", heading2_style))
    for line in saved_data.get('marche_tendances', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Cibles Principales
    story.append(Paragraph("2. Cibles Principales", heading2_style))
    if 'marche_cibles_table' in saved_data:
        cibles_data = [["Segment", "Bénéfices"]]
        segments = saved_data['marche_cibles_table'].get('Segment', [])
        benefices = saved_data['marche_cibles_table'].get('Bénéfices', [])
        
        for i in range(min(len(segments), len(benefices))):
            cibles_data.append([segments[i], benefices[i]])
        
        cibles_table = Table(cibles_data, colWidths=[doc.width/2.0, doc.width/2.0])
        cibles_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(cibles_table)
    story.append(Spacer(1, 0.2*inch))
    
    # SWOT
    story.append(Paragraph("3. Analyse SWOT", heading2_style))
    if 'marche_swot_table' in saved_data:
        swot_data = [["Catégorie", "Points"]]
        categories = saved_data['marche_swot_table'].get('Catégorie', [])
        points = saved_data['marche_swot_table'].get('Points', [])
        
        for i in range(min(len(categories), len(points))):
            swot_data.append([categories[i], points[i]])
        
        swot_table = Table(swot_data, colWidths=[doc.width/3.0, doc.width*2/3.0])
        swot_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(swot_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Marketing Mix
    story.append(Paragraph("4. Marketing Mix (4P)", heading2_style))
    if 'marche_marketing_table' in saved_data:
        marketing_data = [["Élément", "Stratégie"]]
        elements = saved_data['marche_marketing_table'].get('Élément', [])
        strategies = saved_data['marche_marketing_table'].get('Stratégie', [])
        
        for i in range(min(len(elements), len(strategies))):
            marketing_data.append([elements[i], strategies[i]])
        
        marketing_table = Table(marketing_data, colWidths=[doc.width/3.0, doc.width*2/3.0])
        marketing_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(marketing_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Analyse Concurrentielle
    story.append(Paragraph("5. Analyse Concurrentielle", heading2_style))
    story.append(Paragraph("Tableau Comparatif des Concurrents", styles['Heading3']))
    if 'marche_concurrents_table' in saved_data:
        concurrents_data = [["Type", "Nom", "Localisation", "Description"]]
        types = saved_data['marche_concurrents_table'].get('Type', [])
        noms = saved_data['marche_concurrents_table'].get('Nom', [])
        locs = saved_data['marche_concurrents_table'].get('Localisation', [])
        descs = saved_data['marche_concurrents_table'].get('Description', [])
        
        for i in range(min(len(types), len(noms), len(locs), len(descs))):
            concurrents_data.append([types[i], noms[i], locs[i], descs[i]])
        
        concurrents_table = Table(concurrents_data, colWidths=[doc.width/6.0, doc.width/6.0, doc.width/6.0, doc.width/2.0])
        concurrents_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (3, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (3, 0), colors.black),
            ('ALIGN', (0, 0), (3, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(concurrents_table)
    
    # Tableau Comparatif Détaillé des Concurrents (nouveau)
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Tableau Comparatif Détaillé des Concurrents", styles['Heading3']))
    
    if 'competitors_comparison_table' in saved_data:
        criteres = saved_data['competitors_comparison_table'].get('Critères/Concurrents', [])
        
        # Préparer les données pour le tableau PDF
        competitors_data = [["Critères/Concurrents", "Glove Voice", "SignAll", "MotionSavvy", "Kinemic", "DuoSign", "Google Live Transcribe", "Ava"]]
        
        for i, critere in enumerate(criteres):
            row = [critere]
            for comp in ["Glove Voice", "SignAll", "MotionSavvy", "Kinemic", "DuoSign", "Google Live Transcribe", "Ava"]:
                values = saved_data['competitors_comparison_table'].get(comp, [])
                if i < len(values):
                    row.append(values[i])
                else:
                    row.append("")
            competitors_data.append(row)
        
        comp_table = Table(competitors_data, colWidths=[doc.width/4.0] + [doc.width/12.0]*7)
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (7, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (7, 0), colors.black),
            ('ALIGN', (0, 0), (7, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(comp_table)
        
        # Ajouter la légende
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph("<b>Légende :</b>", normal_style))
        story.append(Paragraph("• + : Service présent", normal_style))
        story.append(Paragraph("• - : Service absent", normal_style))
        story.append(Paragraph("• T : Service partiellement présent", normal_style))
    
    story.append(Spacer(1, 0.2*inch))
    
    # Business Model Canvas
    story.append(Paragraph("7. Business Model Canvas (BMC) de Glove Voice", heading2_style))
    
    # Construire les données pour les sections du BMC
    bmc_data = [
        {
            "titre": "Partenaires Clés",
            "contenu": saved_data.get('bmc_partenaires', '')
        },
        {
            "titre": "Activités Clés",
            "contenu": saved_data.get('bmc_activites', '')
        },
        {
            "titre": "Proposition de Valeur",
            "contenu": saved_data.get('bmc_proposition', '')
        },
        {
            "titre": "Relations avec les Clients",
            "contenu": saved_data.get('bmc_relations', '')
        },
        {
            "titre": "Segments de Clientèle",
            "contenu": saved_data.get('bmc_segments', '')
        },
        {
            "titre": "Ressources Clés",
            "contenu": saved_data.get('bmc_ressources', '')
        },
        {
            "titre": "Canaux",
            "contenu": saved_data.get('bmc_canaux', '')
        },
        {
            "titre": "Structure de Coûts",
            "contenu": saved_data.get('bmc_couts', '')
        },
        {
            "titre": "Sources de Revenus",
            "contenu": saved_data.get('bmc_revenus', '')
        }
    ]
    
    # Pour chaque section du BMC
    for section in bmc_data:
        story.append(Paragraph(f"<b>{section['titre']}</b>", styles['Heading3']))
        
        # Traiter le contenu ligne par ligne
        for line in section['contenu'].split('\n'):
            if line.strip():
                story.append(Paragraph(line, normal_style))
        
        story.append(Spacer(1, 0.1*inch))
    
    story.append(Spacer(1, 0.2*inch))
    
    # Stratégie Commerciale
    story.append(Paragraph("STRATÉGIE COMMERCIALE", heading1_style))
    
    # Cibles Commerciales
    story.append(Paragraph("1. Cibles Commerciales", heading2_style))
    story.append(Paragraph("Particuliers", styles['Heading3']))
    for line in saved_data.get('part', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    
    # Projections
    if 'projections_table' in saved_data:
        story.append(Spacer(1, 0.1*inch))
        projections_data = [["Année", "Visiteurs", "Ventes"]]
        annees = saved_data['projections_table'].get('Année', [])
        visiteurs = saved_data['projections_table'].get('Visiteurs', [])
        ventes = saved_data['projections_table'].get('Ventes', [])
        
        for i in range(min(len(annees), len(visiteurs), len(ventes))):
            projections_data.append([str(annees[i]), visiteurs[i], ventes[i]])
        
        projections_table = Table(projections_data, colWidths=[doc.width/3.0, doc.width/3.0, doc.width/3.0])
        projections_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (2, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (2, 0), colors.black),
            ('ALIGN', (0, 0), (2, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(projections_table)
    
    # Associations, Écoles, Entreprises
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Associations", styles['Heading3']))
    for line in saved_data.get('assoc', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Établissements Scolaires", styles['Heading3']))
    for line in saved_data.get('ecoles', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Entreprises", styles['Heading3']))
    for line in saved_data.get('entrep', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Plan Financier
    story.append(Paragraph("PLAN FINANCIER", heading1_style))
    
    # Besoins de Financement
    story.append(Paragraph("1. Besoins de Financement", heading2_style))
    if 'financement_table' in saved_data:
        financement_data = [["Poste", "Montant (DH)"]]
        postes = saved_data['financement_table'].get('Poste', [])
        montants = saved_data['financement_table'].get('Montant (DH)', [])
        
        for i in range(min(len(postes), len(montants))):
            financement_data.append([postes[i], montants[i]])
        
        financement_table = Table(financement_data, colWidths=[doc.width/2.0, doc.width/2.0])
        financement_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(financement_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Sources de Financement
    story.append(Paragraph("2. Sources de Financement", heading2_style))
    if 'sources_table' in saved_data:
        sources_data = [["Source", "Montant (DH)"]]
        sources = saved_data['sources_table'].get('Source', [])
        montants_s = saved_data['sources_table'].get('Montant (DH)', [])
        
        for i in range(min(len(sources), len(montants_s))):
            sources_data.append([sources[i], montants_s[i]])
        
        sources_table = Table(sources_data, colWidths=[doc.width/2.0, doc.width/2.0])
        sources_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(sources_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Compte de Résultat
    story.append(Paragraph("3. Compte de Résultat", heading2_style))
    if 'resultats_table' in saved_data:
        resultats_data = [["Année", "CA (DH)", "Résultat"]]
        annees_r = saved_data['resultats_table'].get('Année', [])
        ca = saved_data['resultats_table'].get('CA (DH)', [])
        resultats = saved_data['resultats_table'].get('Résultat', [])
        
        for i in range(min(len(annees_r), len(ca), len(resultats))):
            resultats_data.append([str(annees_r[i]), ca[i], resultats[i]])
        
        resultats_table = Table(resultats_data, colWidths=[doc.width/3.0, doc.width/3.0, doc.width/3.0])
        resultats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (2, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (2, 0), colors.black),
            ('ALIGN', (0, 0), (2, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(resultats_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Indicateurs Clés
    story.append(Paragraph("4. Indicateurs Clés", heading2_style))
    if 'indicateurs_table' in saved_data:
        indicateurs_data = [["Indicateur", "Valeur"]]
        indicateurs = saved_data['indicateurs_table'].get('Indicateur', [])
        valeurs = saved_data['indicateurs_table'].get('Valeur', [])
        
        for i in range(min(len(indicateurs), len(valeurs))):
            indicateurs_data.append([indicateurs[i], valeurs[i]])
        
        indicateurs_table = Table(indicateurs_data, colWidths=[doc.width/2.0, doc.width/2.0])
        indicateurs_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(indicateurs_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Détails Techniques
    story.append(Paragraph("DÉTAILS TECHNIQUES", heading1_style))
    
    # Étude technique
    story.append(Paragraph("1. Étude technique du projet Glove Voice", heading2_style))
    
    # Prototype Gant Intelligent
    story.append(Paragraph("1.1 Prototype Gant Intelligent Glove Voice", heading2_style))
    
    # Partie Électronique
    story.append(Paragraph("Partie Électronique", styles['Heading3']))
    for line in saved_data.get('tech_electronique', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Partie Matériaux
    story.append(Paragraph("Partie Étude des Matériaux", styles['Heading3']))
    for line in saved_data.get('tech_materiaux', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Application Mobile
    story.append(Paragraph("1.2 Application Mobile Glove Voice", heading2_style))
    for line in saved_data.get('tech_application', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Algorithmes et Traitement des Données
    story.append(Paragraph("1.3 Algorithmes et Traitement des Données", heading2_style))
    for line in saved_data.get('tech_algorithmes', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Interface Utilisateur
    story.append(Paragraph("1.4 Interface Utilisateur et Expérience", heading2_style))
    for line in saved_data.get('tech_interface', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Tests et Validation
    story.append(Paragraph("1.5 Tests et Validation", heading2_style))
    for line in saved_data.get('tech_tests', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Sections originales
    story.append(Paragraph("2. Prototype", heading2_style))
    for line in saved_data.get('comp', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("3. Application Mobile", heading2_style))
    for line in saved_data.get('app', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("4. Processus de Production", heading2_style))
    for line in saved_data.get('prod', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Pied de page
    story.append(Paragraph("© 2024 Glove Voice - Tous droits réservés", 
                          ParagraphStyle(
                            'Footer',
                            parent=styles['Normal'],
                            alignment=TA_CENTER,
                            fontSize=8
                          )))
    
    # Assembler le document
    doc.build(story)
    buffer.seek(0)
    return buffer

# Navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Aller à :",
    ("Présentation du Projet", "Analyse de Marché", "Stratégie Commerciale", "Plan Financier", "Détails Techniques")
)

# Bouton de génération PDF dans la barre latérale
if st.sidebar.button("📄 Générer un PDF du rapport"):
    pdf = generate_pdf()
    st.sidebar.download_button(
        label="⬇️ Télécharger le PDF",
        data=pdf,
        file_name="Glove_Voice_Rapport.pdf",
        mime="application/pdf"
    )

# Page 1: Présentation du Projet
if page == "Présentation du Projet":
    # Ajout d'un input pour changer le titre du projet
    projet_titre = create_input("Titre du Projet", "🧤 Glove Voice - Présentation du Projet", "projet_titre")
    
    st.title(projet_titre)
    
    st.header("1. Description du Projet")
    probleme = create_input("Problématique", 
                          "La difficulté des personnes sourdes et muettes à communiquer avec celles qui ne maîtrisent pas la langue des signes", 
                          "pres_prob")
    solution = create_input("Solution proposée", 
                          "- Gant intelligent équipé de capteurs de mouvement\n- Application mobile connectée\n- Synthèse vocale des gestes traduits\n- Technologie d'IA", 
                          "pres_solution", text_area=True)
    
    st.header("2. Fiche d'Identité")
    identite_data = {
        "Information": ["Raison sociale", "Slogan", "Objet social", "Domaines d'activité", 
                       "Siège social", "Forme juridique", "Nombre d'associés", "Valeurs"],
        "Détail": [
            create_input("Raison sociale", "Glove Voice", "ident_rs"),
            create_input("Slogan", "Your Voice is HEARD", "ident_slogan"),
            create_input("Objet social", "Dispositif de communication intelligent", "ident_objet_social"),
            create_input("Domaines d'activité", "Technologie assistive, Informatique mobile", "ident_domaines"),
            create_input("Siège social", "Rabat", "ident_siege"),
            create_input("Forme juridique", "SARL", "ident_forme"),
            create_input("Nombre d'associés", "9 membres", "ident_associes"),
            create_input("Valeurs", "Innovation, Inclusion, Accessibilité", "ident_valeurs")
        ]
    }
    st.table(pd.DataFrame(identite_data))
    
    st.header("3. Objectifs et Vision")
    objectifs = create_input("Objectifs Principaux", 
                           "- Améliorer l'inclusion sociale\n- Faciliter l'accès à l'emploi\n- Accroître l'autonomie", 
                           "pres_objectifs", text_area=True)
    odd = create_input("Objectifs de Développement Durable", 
                      "- ODD 4 : Éducation\n- ODD 8 : Travail décent\n- ODD 10 : Réduction des inégalités", 
                      "pres_odd", text_area=True)
    mission = create_input("Mission", "Révolutionner la communication pour les sourds/muets", "pres_mission")
    vision = create_input("Vision", "Monde sans barrières de communication", "pres_vision")
    
    st.header("4. Réalisations Accomplies")
    realisations = create_input("Réalisations", 
                              "- Présentation au ministre\n- Partenariat Fondation Lalla Asmae\n- Collaboration ESITH\n- Brevetage en cours", 
                              "pres_realisations", text_area=True)

# Page 2: Analyse de Marché
elif page == "Analyse de Marché":
    # Ajout d'un input pour changer le titre de la page
    marche_titre = create_input("Titre de la Page", "📊 Analyse de Marché", "marche_titre")
    st.title(marche_titre)
    
    st.header("1. Tendances du Marché")
    tendances = create_input("Tendances", 
                           "- Marché technologies d'assistance en croissance\n- Sensibilisation accrue à l'inclusion\n- Avancées en IA", 
                           "marche_tendances", text_area=True)
    
    st.header("2. Cibles Principales")
    cibles_data = {
        "Segment": [
            create_input("Segment 1", "Écoles/Universités", "marche_seg1"),
            create_input("Segment 2", "Entreprises", "marche_seg2"),
            create_input("Segment 3", "Associations", "marche_seg3")
        ],
        "Bénéfices": [
            create_input("Bénéfice 1", "Communication inclusive", "marche_ben1"),
            create_input("Bénéfice 2", "Amélioration communication", "marche_ben2"),
            create_input("Bénéfice 3", "Formation, sensibilisation", "marche_ben3")
        ]
    }
    create_editable_table(cibles_data, "marche_cibles_table")
    
    st.header("3. Analyse SWOT")
    swot_data = {
        "Catégorie": ["Forces", "Faiblesses", "Opportunités", "Menaces"],
        "Points": [
            create_input("Forces", "Interface intuitive, impact social", "marche_force"),
            create_input("Faiblesses", "Manque de notoriété, coûts", "marche_faib"),
            create_input("Opportunités", "Programmes gouvernementaux", "marche_opp"),
            create_input("Menaces", "Évolution technologique rapide", "marche_menace")
    ]
    }
    create_editable_table(swot_data, "marche_swot_table")
    
    st.header("4. Marketing Mix (4P)")
    marketing_data = {
        "Élément": ["Produit", "Prix", "Distribution", "Promotion"],
        "Stratégie": [
            create_input("Stratégie Produit", "Gant + app mobile, multilingue", "marche_prod"),
            create_input("Stratégie Prix", "Tarification différenciée", "marche_prix"),
            create_input("Stratégie Distribution", "Plateformes en ligne", "marche_dist"),
            create_input("Stratégie Promotion", "Campagnes sensibilisation", "marche_promo")
        ]
    }
    create_editable_table(marketing_data, "marche_marketing_table")
    
    st.header("5. Analyse Concurrentielle")
    st.subheader("Tableau Comparatif des Concurrents")
    concurrents_data = {
        "Type": [create_input("Type 1", "Concurrent direct", "marche_type1")],
        "Nom": [create_input("Nom 1", "", "marche_nom1")],
        "Localisation": [create_input("Localisation 1", "", "marche_loc1")],
        "Description": [create_input("Description 1", "", "marche_desc1", text_area=True)]
    }
    create_editable_table(concurrents_data, "marche_concurrents_table")
    
    # Ajout du nouveau tableau comparatif détaillé des concurrents avec inputs
    st.markdown("---")
    create_competitor_comparison_table("competitors_comparison_table")
    st.markdown("---")
    
    st.subheader("Comparaison des Fonctionnalités Clés")
    comparison_data = {
        "Critères": ["Traduction temps réel", "App mobile", "Multilingue"],
        "Glove Voice": ["+", "+", "+"],
        "Concurrent 1": ["+", "-", "-"],
        "Concurrent 2": ["-", "+", "+"]
    }
    create_editable_table(comparison_data, "marche_comparison_table")
    
    st.subheader("Analyse Comparative")
    analyse_comp = create_input("Analyse", 
                               "Glove Voice se distingue par son approche intégrée...", 
                               "marche_analyse", text_area=True)
    
    st.subheader("Matrice de Comparaison")
    matrice_data = {
        "Critère": ["Support", "Langues", "Prix"],
        "Glove Voice": ["Gant", "Arabe, Français", "Variable"],
        "Concurrent 1": ["Caméras", "ASL", "Élevé"]
    }
    create_editable_table(matrice_data, "marche_matrice_table")
    
    # Ajout du Business Model Canvas avec inputs
    st.markdown("---")
    create_business_model_canvas("bmc")
    st.markdown("---")
    
    st.header("6. Modèle d'Affaires")
    create_expandable_table("Partenaires Clés", 
                          {"Type": ["ONG"], "Rôle": ["Diffusion"]}, 
                          "modele_partenaires")
    create_expandable_table("Activités Clés", 
                          {"Activité": ["Développement"], "Description": ["Amélioration"]}, 
                          "modele_activites")
    create_expandable_table("Proposition de Valeur", 
                          {"Élément": ["Traduction"], "Description": ["Communication"]}, 
                          "modele_proposition")
    create_expandable_table("Relations Clients", 
                          {"Type": ["Support"], "Description": ["Assistance"]}, 
                          "modele_relations")
    create_expandable_table("Segments Clients", 
                          {"Segment": ["Écoles"], "Description": ["Sensibilisation"]}, 
                          "modele_segments")
    create_expandable_table("Ressources Clés", 
                          {"Type": ["IA"], "Description": ["Algorithmes"]}, 
                          "modele_ressources")
    create_expandable_table("Structure de Coûts", 
                          {"Poste": ["Développement"], "Description": ["Application"]}, 
                          "modele_couts")
    create_expandable_table("Canaux", 
                          {"Canal": ["App mobile"], "Description": ["iOS/Android"]}, 
                          "modele_canaux")
    create_expandable_table("Sources de Revenus", 
                          {"Source": ["Licences"], "Description": ["Tarification"]}, 
                          "modele_revenus")

# Page 3: Stratégie Commerciale
elif page == "Stratégie Commerciale":
    # Ajout d'un input pour changer le titre de la page
    strategie_titre = create_input("Titre de la Page", "📈 Stratégie Commerciale", "strategie_titre")
    st.title(strategie_titre)
    
    st.header("1. Cibles Commerciales")
    st.subheader("Particuliers")
    particuliers = create_input("Stratégie", 
                              "Segmentation : Parents, jeunes adultes...", 
                              "part", text_area=True)
    
    annees = st.slider("Nombre d'années", 1, 5, 3, key="annees_slider")
    projections = {
        "Année": list(range(1, annees+1)),
        "Visiteurs": [create_input(f"Visiteurs {i}", "500", f"vis{i}") for i in range(1, annees+1)],
        "Ventes": [create_input(f"Ventes {i}", "50", f"ventes{i}") for i in range(1, annees+1)]
    }
    create_editable_table(projections, "projections_table")
    
    st.subheader("Associations")
    associations = create_input("Plan associations", 
                              "20 associations ciblées...", 
                              "assoc", text_area=True)
    
    st.subheader("Établissements Scolaires")
    ecoles = create_input("Plan écoles", 
                         "Année 3 : écoles pilotes...", 
                         "ecoles", text_area=True)
    
    st.subheader("Entreprises")
    entreprises = create_input("Plan entreprises", 
                             "Secteurs cibles : Automobile...", 
                             "entrep", text_area=True)

# Page 4: Plan Financier
elif page == "Plan Financier":
    # Ajout d'un input pour changer le titre de la page
    financier_titre = create_input("Titre de la Page", "💰 Plan Financier", "financier_titre")
    st.title(financier_titre)
    
    st.header("1. Besoins de Financement")
    financement_data = {
        "Poste": ["Immobilisations", "Frais"],
        "Montant (DH)": ["167,694", "8,000"]
    }
    create_editable_table(financement_data, "financement_table")
    
    st.header("2. Sources de Financement")
    sources_data = {
        "Source": ["Subvention", "Emprunt"],
        "Montant (DH)": ["100,000", "518,574"]
    }
    create_editable_table(sources_data, "sources_table")
    
    st.header("3. Compte de Résultat")
    resultats_data = {
        "Année": [1, 2, 3],
        "CA (DH)": ["1,161,509", "2,066,406", "3,820,488"],
        "Résultat": ["-870,227", "-672,604", "+278,172"]
    }
    create_editable_table(resultats_data, "resultats_table")
    
    st.header("4. Indicateurs Clés")
    indicateurs_data = {
        "Indicateur": ["Seuil rentabilité", "CAF"],
        "Valeur": ["11,190,550 DH", "7,270,333 DH"]
    }
    create_editable_table(indicateurs_data, "indicateurs_table")

# Page 5: Détails Techniques
elif page == "Détails Techniques":
    # Ajout d'un input pour changer le titre de la page
    technique_titre = create_input("Titre de la Page", "⚙️ Détails Techniques", "technique_titre")
    st.title(technique_titre)
    
    # Nouvelle section pour l'étude technique
    st.header("1. Étude technique du projet Glove Voice")
    
    # Section prototype
    st.subheader("1.1 Prototype Gant Intelligent Glove Voice")
    
    # Partie électronique
    st.markdown("##### Partie Électronique")
    partie_electronique = create_input("", 
                                     "La conception du gant intelligent repose sur plusieurs composants électroniques essentiels. Tout d'abord, les capteurs jouent un rôle crucial : les capteurs de flexion mesurent la courbure des doigts (un capteur par doigt), tels que le Spectra Symbol Flex Sensor et les Flexpoint Bend Sensors. Les accéléromètres, comme le ADXL335 et le MPU-6050, mesurent les accélérations linéaires des mouvements de la main, tandis que les gyroscopes, également présents dans le MPU-6050, mesurent la rotation angulaire. En option, des magnétomètres tels que le HMC5883L peuvent être intégrés pour mesurer l'orientation par rapport au champ magnétique terrestre. Le cœur du gant est constitué d'un microcontrôleur, tel que l'Arduino Nano ou l'ESP32, qui collecte et traite les données des capteurs. Pour la communication, des modules Bluetooth (comme le HC-05) et Wi-Fi (ESP8266) sont utilisés, garantissant une connexion sans fil avec l'application mobile. Le circuit imprimé (PCB) est conçu sur mesure pour supporter les composants et faciliter l'assemblage. En ce qui concerne l'alimentation, une batterie rechargeable, par exemple une Li-Po 3.7V, alimente les capteurs et le microcontrôleur, avec un système de gestion de l'énergie incluant un régulateur de tension et un module de charge.",
                                     "tech_electronique", text_area=True, height=300)
    
    # Partie étude des matériaux
    st.markdown("##### Partie Étude des Matériaux")
    partie_materiaux = create_input("", 
                                  "Le choix des matériaux pour le gant est également déterminant pour son efficacité et son confort. Un tissu conducteur est utilisé dans les zones nécessitant la transmission de signaux électriques, tel que le nylon mélangé à de l'argent. Pour la couche de base, le Spandex ou le Lycra est privilégié, offrant une extensibilité pour un ajustement serré et confortable en contact avec la peau. Une fine couche de tissu non tissé est ajoutée entre cette couche et la couche extérieure pour améliorer le confort et éviter les irritations cutanées. Pour la protection de la batterie, située au niveau du coude, des matériaux robustes comme le Kevlar ou le Cordura sont intégrés, assurant une protection durable. Enfin, des câbles souples et des connecteurs, tels que les fils Dupont et les câbles flexibles plats (FFC/FPC), relient les capteurs et autres composants au microcontrôleur, garantissant une flexibilité et une fiabilité optimales dans l'assemblage du gant.",
                                  "tech_materiaux", text_area=True, height=250)
    
    # Section application mobile
    st.subheader("1.2 Application Mobile Glove Voice")
    partie_application = create_input("", 
                                   "L'application mobile Glove Voice permet une connexion rapide au gant intelligent via Bluetooth ou Wi-Fi (ESP32), assurant ainsi un transfert instantané des données. Les capteurs intégrés au gant transmettent les mouvements des mains et des doigts à l'application qui, grâce à des algorithmes d'intelligence artificielle avancés, les convertit en temps réel en texte et en paroles. L'interface utilisateur est conçue pour être intuitive, permettant une configuration rapide et un accès facile aux différentes fonctionnalités. L'application offre plusieurs modes de traduction : temps réel pour les conversations immédiates, mode d'enregistrement pour sauvegarder des phrases fréquemment utilisées, et mode d'apprentissage pour enseigner la langue des signes aux utilisateurs non-initiés. La personnalisation est au cœur de l'application, avec des paramètres ajustables pour la sensibilité de détection des gestes, le volume et la vitesse de la parole synthétisée, ainsi que le choix entre différentes voix et langues. Pour les environnements éducatifs et professionnels, des fonctionnalités spécifiques sont disponibles, comme la création de vocabulaires personnalisés et l'intégration avec d'autres systèmes de communication.",
                                   "tech_application", text_area=True, height=250)
    
    # Section algorithmes et traitement des données
    st.subheader("1.3 Algorithmes et Traitement des Données")
    partie_algorithmes = create_input("", 
                                    "Le système Glove Voice repose sur des algorithmes sophistiqués de traitement des données pour traduire avec précision les gestes en langage parlé. Les données brutes des capteurs sont d'abord prétraitées pour éliminer le bruit et normaliser les signaux. Ensuite, des algorithmes de reconnaissance de motifs basés sur l'apprentissage automatique (comme les réseaux de neurones profonds ou SVM) identifient les gestes spécifiques. Des modèles pré-entraînés, constamment améliorés par apprentissage continu, permettent une reconnaissance précise des signes standardisés et personnalisés. Le système intègre également des algorithmes de prédiction contextuelle pour améliorer la fluidité de la traduction, en suggérant des mots ou expressions probables basés sur le contexte de la conversation. Pour garantir des performances optimales même avec une connexion internet limitée, une partie du traitement est effectuée directement sur l'appareil, tandis que des modèles plus complexes peuvent être exécutés dans le cloud lorsque disponible.",
                                    "tech_algorithmes", text_area=True, height=200)
    
    # Section interface utilisateur et expérience
    st.subheader("1.4 Interface Utilisateur et Expérience")
    partie_interface = create_input("", 
                                  "L'interface utilisateur de Glove Voice a été développée selon les principes du design centré sur l'utilisateur, avec une attention particulière aux besoins des personnes sourdes et malentendantes. L'application se caractérise par une navigation intuitive avec des icônes claires et des instructions visuelles. Des retours haptiques et visuels sont intégrés pour confirmer les actions et les traductions. Le tableau de bord principal affiche en temps réel le texte traduit, avec options de sauvegarde, partage et modification. L'application inclut également un mode nuit, des options de personnalisation des couleurs et de la taille du texte, et une section d'aide contextuelle. Des tutoriels interactifs guident les nouveaux utilisateurs, tandis que l'historique des conversations et un dictionnaire de signes personnalisable enrichissent l'expérience. Des tests utilisateurs réguliers avec des personnes sourdes et malentendantes contribuent à l'amélioration continue de l'interface.",
                                  "tech_interface", text_area=True, height=200)
    
    # Section tests et validation
    st.subheader("1.5 Tests et Validation")
    partie_tests = create_input("", 
                              "Le processus de validation du système Glove Voice suit une méthodologie rigoureuse pour garantir fiabilité et précision. Des tests unitaires vérifient chaque composant (capteurs, algorithmes, interface) individuellement. Des tests d'intégration évaluent le fonctionnement combiné des composants. Des tests fonctionnels avec des utilisateurs réels dans diverses conditions (luminosité, bruit ambiant) mesurent la précision de reconnaissance. Des tests de performance évaluent la réactivité, la consommation d'énergie et la stabilité du système. Des sessions de feedback avec des interprètes en langue des signes et des représentants de la communauté sourde permettent d'ajuster le système. Des évaluations comparatives avec d'autres solutions existantes confirment les avantages distinctifs de Glove Voice. Le processus de validation est continu, avec des mises à jour régulières basées sur les retours utilisateurs et les avancées technologiques.",
                              "tech_tests", text_area=True, height=200)
    
    # Garde les sections prototype et application originales
    st.header("2. Prototype du Gant")
    composants = create_input("Composants", 
                            "- Capteurs flexion\n- Microcontrôleur\n- Bluetooth", 
                            "comp", text_area=True)
    
    st.header("3. Application Mobile")
    app_mobile = create_input("App mobile", 
                            "- Reconnaissance gestuelle\n- Multilingue", 
                            "app", text_area=True)
    
    st.header("4. Processus de Production")
    production = create_input("Production", 
                            "Prototypage avec ESITH...", 
                            "prod", text_area=True)

# Pied de page
st.markdown("---")


# Bouton pour effacer toutes les données (optionnel)
if st.sidebar.button("Réinitialiser toutes les données"):
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)
    st.rerun()
