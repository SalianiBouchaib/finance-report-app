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
def create_input(label, default_value="", key=None, text_area=False):
    # Récupérer la valeur sauvegardée si elle existe
    saved_value = saved_data.get(key, default_value)
    
    if text_area:
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
    story.append(Paragraph("Glove Voice - Rapport Complet", title_style))
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
    
    # Prototype du Gant
    story.append(Paragraph("1. Prototype", heading2_style))
    for line in saved_data.get('comp', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Application Mobile
    story.append(Paragraph("2. Application Mobile", heading2_style))
    for line in saved_data.get('app', '').split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Processus de Production
    story.append(Paragraph("3. Processus de Production", heading2_style))
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
    st.title("🧤 Glove Voice - Présentation du Projet")
    
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
    st.title("📊 Analyse de Marché")
    
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
    st.title("📈 Stratégie Commerciale")
    
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
    st.title("💰 Plan Financier")
    
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
    st.title("⚙️ Détails Techniques")
    
    st.header("1. Prototype du Gant")
    composants = create_input("Composants", 
                            "- Capteurs flexion\n- Microcontrôleur\n- Bluetooth", 
                            "comp", text_area=True)
    
    st.header("2. Application Mobile")
    app_mobile = create_input("App mobile", 
                            "- Reconnaissance gestuelle\n- Multilingue", 
                            "app", text_area=True)
    
    st.header("3. Processus de Production")
    production = create_input("Production", 
                            "Prototypage avec ESITH...", 
                            "prod", text_area=True)

# Pied de page
st.markdown("---")
st.caption("© 2024 Glove Voice - Tous droits réservés")

# Bouton pour effacer toutes les données (optionnel)
if st.sidebar.button("Réinitialiser toutes les données"):
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)
    st.rerun()