import streamlit as st

# This MUST be the first Streamlit command
st.set_page_config(
    page_title="Simulateur d'Étude Financière", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Now import the rest of the libraries
import pandas as pd
import numpy as np

# Handle optional dependencies with try/except
try:
    import numpy_financial as npf
    NPF_AVAILABLE = True
except ImportError:
    NPF_AVAILABLE = False
    
    
    # Define fallback functions if needed
    def simple_irr(values):
        """Simple IRR fallback when numpy_financial is not available"""
        return 0.0  # Return a default value
    
    # Create a namespace to mimic npf
    class NPF_Fallback:
        @staticmethod
        def irr(values):
            return simple_irr(values)
    
    # Assign the fallback to npf
    npf = NPF_Fallback()
    
from datetime import datetime
import plotly.express as px
import json
import os
import tempfile
import matplotlib.pyplot as plt
from fpdf import FPDF
import re
import warnings

# Handle pyfinance safely
try:
    import pyfinance as pf
    PYFINANCE_AVAILABLE = True
except ImportError:
    PYFINANCE_AVAILABLE = False
    
    
    # Create a fallback for pyfinance functions used in your code
    class PF_Fallback:
        @staticmethod
        def npv(rate, values):
            """Simple NPV implementation"""
            npv = 0
            for i, val in enumerate(values):
                npv += val / ((1 + rate) ** i)
            return npv
        
        @staticmethod
        def irr(values):
            """Simple IRR fallback"""
            return 0.0
    
    # Assign the fallback to pf
    pf = PF_Fallback()

# Ignorer les avertissements de dépréciation
warnings.filterwarnings('ignore')

# Continue with the rest of your code...


# Fonctions d'export intégrées avec toutes les dépendances
def convert_to_serializable(obj):
    """
    Convertit les objets Python complexes en structures JSON sérialisables
    """
    if isinstance(obj, (datetime, pd.Timestamp)):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (pd.DataFrame, pd.Series)):
        return obj.to_dict()
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(i) for i in obj]
    elif isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    else:
        return str(obj)


def get_session_data_as_json():
    """
    Convertit toutes les données de session en format JSON
    """
    # Créer une copie des données de session pour éviter de modifier l'original
    session_data = {}
    
    # Exporter toutes les données importantes
    for key in ["basic_info", "investment_data", "immos", "credits", "subsidies", 
                "frais_preliminaires", "income_statement_params", "cash_flow_params",
                "actif_data", "passif_data", "monthly_cashflow_data", "vat_budget_data",
                "detailed_amortization"]:
        if key in st.session_state:
            # Convertir les structures complexes en structures sérialisables
            session_data[key] = convert_to_serializable(st.session_state[key])
    
    # Ajouter des métadonnées
    session_data["metadata"] = {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "app": "Simulateur d'Étude Financière"
    }
    
    # Convertir en JSON
    return json.dumps(session_data, ensure_ascii=False, indent=2)


def save_data():
    """
    Sauvegarde les données de session dans un fichier local
    """
    try:
        # Créer le dossier de sauvegarde s'il n'existe pas
        save_dir = "saved_data"
        os.makedirs(save_dir, exist_ok=True)
        
        # Générer un nom de fichier unique
        company_name = st.session_state.basic_info.get('company_name', 'entreprise')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{save_dir}/{company_name}_{timestamp}.json"
        
        # Obtenir les données JSON
        data_json = get_session_data_as_json()
        
        # Écrire dans un fichier
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(data_json)
        
        st.success(f"✅ Données sauvegardées dans {filename}")
        return filename
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde: {str(e)}")
        return None


def load_data_from_json(file):
    """
    Charge les données à partir d'un fichier JSON
    """
    try:
        # Lire le fichier JSON
        content = file.read()
        data = json.loads(content)
        
        # Mettre à jour session_state avec les données chargées
        for key, value in data.items():
            if key != "metadata":
                st.session_state[key] = value
        
        return True
    except Exception as e:
        raise Exception(f"Erreur lors du chargement des données: {str(e)}")


def ascii_only(text):
    """Remplace les caractères Unicode problématiques par des alternatives ASCII."""
    if not isinstance(text, str):
        text = str(text)
    return (text.replace("✓", "OK")
                .replace("⚠", "ATTENTION")
                .replace("❌", "ERREUR"))

def generate_pdf_report(report_name, sections):
    """
    Génère un rapport PDF complet incluant toutes les sections de l'application.
    Intègre les sections sélectionnées et assure une gestion robuste des données.
    La fonction est améliorée pour inclure tous les graphiques d'amortissement,
    les tableaux de trésorerie mensuelle et les tableaux de budget TVA.
    """
    import tempfile
    import matplotlib
    matplotlib.use('Agg')  # Backend non-interactif, essentiel pour les environnements sans affichage
    import matplotlib.pyplot as plt
    plt.ioff()  # Désactiver le mode interactif
    import numpy as np
    import pandas as pd
    from datetime import datetime
    import os
    import base64
    from io import BytesIO
    import re
    from PIL import Image
    import seaborn as sns
    import logging

    # Configuration d'un logger pour capturer les erreurs
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('pdf_generator')

    # Fonction utilitaire pour récupérer des données en toute sécurité
    def safe_get(data_dict, key, default=None):
        """Récupère en toute sécurité une valeur d'un dictionnaire, avec une valeur par défaut."""
        if data_dict is None:
            return default
        return data_dict.get(key, default)
    
    # Fonction pour récupérer une liste de manière sécurisée
    def safe_list_get(lst, idx, default=0):
        """Accéde de manière sécurisée à un élément d'une liste."""
        if lst is None:
            return default
        if not isinstance(lst, list):
            return default
        if idx < 0 or idx >= len(lst):
            return default
        return lst[idx]

    # Fonction pour normaliser les listes à une longueur donnée
    def normalize_list(lst, length=3, default_value=0):
        """Normalise une liste à une longueur spécifique."""
        if not isinstance(lst, list):
            lst = [default_value] * length
        else:
            # Tronquer si trop long
            if len(lst) > length:
                lst = lst[:length]
            # Étendre si trop court
            while len(lst) < length:
                lst.append(default_value)
        return lst

    # Fonction pour vérifier la présence de données dans session_state
    def has_data(key):
        """Vérifie si des données valides existent pour une clé session_state."""
        if key not in st.session_state:
            return False
        data = st.session_state[key]
        if data is None:
            return False
        if isinstance(data, (list, dict)) and not data:
            return False
        return True

    # Nouvelle fonction pour sauvegarder des figures de manière fiable
    def save_figure_safely(fig, filename, temp_dir, dpi=150):
        """Sauvegarde une figure de manière fiable et vérifie sa validité."""
        try:
            path = f"{temp_dir}/{filename}"
            fig.savefig(path, format='png', dpi=dpi, bbox_inches='tight')
            plt.close(fig)  # Important: fermer la figure pour libérer la mémoire
            
            # Vérifier que le fichier existe et est valide
            if os.path.exists(path) and os.path.getsize(path) > 100:
                try:
                    with Image.open(path) as img:
                        img.verify()  # Vérifier que l'image est valide
                    logger.info(f"Image sauvegardée avec succès: {path}")
                    return path
                except Exception as e:
                    logger.error(f"Erreur validation image {filename}: {e}")
            else:
                logger.warning(f"Fichier image trop petit ou inexistant: {path}")
            return None
        except Exception as e:
            logger.error(f"Erreur sauvegarde {filename}: {e}")
            return None

    temp_dir = tempfile.mkdtemp()
    logger.info(f"Dossier temporaire créé: {temp_dir}")
    
    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 15)
            self.cell(0, 10, ascii_only(report_name), 0, 1, "C")
            self.ln(10)
        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, ascii_only(f"Page {self.page_no()}/{{nb}}"), 0, 0, "C")
            self.cell(0, 10, ascii_only(f"Genere le {datetime.now().strftime('%d/%m/%Y')}"), 0, 0, "R")
        def chapter_title(self, title):
            self.set_font("Arial", "B", 12)
            self.set_fill_color(200, 220, 255)
            self.cell(0, 6, ascii_only(title), 0, 1, "L", 1)
            self.ln(4)
        def chapter_body(self, txt):
            self.set_font("Arial", "", 10)
            self.multi_cell(0, 5, ascii_only(txt))
            self.ln()
        def add_image(self, img, w=0, h=0, caption=""):
            """Méthode améliorée pour ajouter des images de manière robuste."""
            try:
                if w == 0 and h == 0:
                    w = 190
                
                # Vérifier si l'image existe et est valide avant de l'ajouter
                success = False
                if os.path.exists(img) and os.path.getsize(img) > 100:
                    try:
                        # Vérifier que c'est une image valide
                        with Image.open(img) as test_img:
                            test_img.verify()
                        
                        # Ajouter l'image au PDF
                        self.image(img, x=10, y=None, w=w, h=h)
                        success = True
                        logger.info(f"Image ajoutée au PDF: {img}")
                    except Exception as e:
                        logger.error(f"Erreur validation image {caption}: {e}")
                else:
                    logger.warning(f"Image non disponible ou invalide: {img}")
                
                # Ajouter la légende si l'image a été ajoutée
                if success and caption:
                    self.ln(5)
                    self.set_font("Arial", "I", 8)
                    self.cell(0, 5, ascii_only(caption), 0, 1, "C")
                
                self.ln(5)
                
                # Afficher un message si l'image n'a pas pu être ajoutée
                if not success:
                    self.set_font("Arial", "I", 9)
                    self.cell(0, 5, ascii_only(f"Image non disponible: {caption}"), 0, 1, "C")
                    self.ln(5)
            except Exception as e:
                logger.error(f"Erreur lors de l'ajout de l'image {caption}: {e}")
                self.set_font("Arial", "I", 9)
                self.cell(0, 5, ascii_only(f"Erreur lors de l'ajout de l'image: {str(e)}"), 0, 1, "C")
                self.ln(5)
        def add_table(self, headers, data, col_widths=None):
            """Ajout d'une méthode pour créer des tableaux formatés"""
            try:
                if col_widths is None:
                    # Distribution égale de la largeur disponible
                    col_widths = [180 / len(headers)] * len(headers)
                
                # En-tête du tableau
                self.set_font("Arial", "B", 9)
                self.set_fill_color(232, 232, 232)
                for i, header in enumerate(headers):
                    if i < len(col_widths):  # Vérification pour éviter l'IndexError
                        self.cell(col_widths[i], 7, ascii_only(str(header)), 1, 0, "C", 1)
                self.ln()
                
                # Contenu du tableau
                self.set_font("Arial", "", 8)
                self.set_fill_color(255, 255, 255)
                fill = False
                for row in data:
                    for i, cell in enumerate(row):
                        if i < len(col_widths):  # Vérification pour éviter l'IndexError
                            self.cell(col_widths[i], 6, ascii_only(str(cell)), 1, 0, "L", fill)
                    self.ln()
                    fill = not fill  # Alternance de couleur pour les lignes
            except Exception as e:
                logger.error(f"Erreur lors de la création du tableau: {e}")
                self.chapter_body(f"Erreur lors de la création du tableau: {str(e)}")

    # Fonction pour capturer les graphiques Plotly
    def capture_plotly_figures():
        """Capture tous les graphiques Plotly générés dans l'application."""
        captured_figs = []
        
        try:
            # Parcourir toutes les entrées dans le session state pour trouver des objets Plotly
            for key, value in st.session_state.items():
                if isinstance(value, dict) and 'figure' in value and 'data' in value.get('figure', {}):
                    # Probablement un objet Plotly Figure
                    try:
                        import plotly.io as pio
                        fig_path = f"{temp_dir}/plotly_{key}.png"
                        value['figure'].write_image(fig_path, width=1000, height=600, scale=2)
                        
                        # Vérifier que l'image a été correctement créée
                        if os.path.exists(fig_path) and os.path.getsize(fig_path) > 100:
                            captured_figs.append({
                                'path': fig_path,
                                'name': f"Graphique {key.replace('_', ' ').title()}"
                            })
                            logger.info(f"Graphique Plotly capturé: {key}")
                        else:
                            logger.warning(f"Échec de capture du graphique Plotly {key}: Fichier invalide")
                    except Exception as e:
                        logger.error(f"Erreur lors de la capture du graphique Plotly {key}: {e}")
        except Exception as e:
            logger.error(f"Erreur lors de la recherche des graphiques Plotly: {e}")
        
        return captured_figs

    # Fonction pour extraire les images des éléments Streamlit
    def capture_streamlit_images():
        """Capture toutes les images générées par Streamlit."""
        captured_imgs = []
        
        try:
            # Rechercher dans le HTML rendu pour trouver les balises img
            import re
            
            try:
                # Essayer d'importer BeautifulSoup si disponible
                from bs4 import BeautifulSoup
                bs4_available = True
            except ImportError:
                bs4_available = False
                logger.warning("BeautifulSoup n'est pas disponible, certaines fonctionnalités de capture d'image seront limitées")
            
            # Essayer d'accéder au contexte de rendu de Streamlit
            try:
                # Méthode 1: Utiliser _get_report_ctx (peut ne pas fonctionner dans toutes les versions)
                ctx = st._get_report_ctx()
                if hasattr(ctx, 'ui_report') and hasattr(ctx.ui_report, 'html'):
                    html_content = ctx.ui_report.html
                else:
                    html_content = ""
            except:
                html_content = ""
                logger.warning("Impossible d'accéder au contexte de rapport Streamlit")
            
            # Si la méthode 1 échoue, essayer autre chose
            if not html_content:
                try:
                    # Méthode 2: Utiliser l'accès direct au cache de session (expérimental)
                    for key, val in st.session_state.items():
                        if isinstance(val, str) and val.startswith("data:image"):
                            # Extraire l'image base64
                            img_data_match = re.search(r'base64,(.*)', val)
                            if img_data_match:
                                img_data = img_data_match.group(1)
                                img_bytes = base64.b64decode(img_data)
                                img_path = f"{temp_dir}/streamlit_img_{len(captured_imgs)}.png"
                                
                                with open(img_path, 'wb') as f:
                                    f.write(img_bytes)
                                
                                # Vérifier que l'image est valide
                                try:
                                    with Image.open(img_path) as img:
                                        img.verify()
                                    captured_imgs.append({
                                        'path': img_path,
                                        'name': f"Image {key.replace('_', ' ').title()}"
                                    })
                                    logger.info(f"Image Streamlit capturée: {key}")
                                except Exception as img_err:
                                    logger.error(f"Image Streamlit invalide {key}: {img_err}")
                except Exception as e:
                    logger.error(f"Erreur lors de la méthode 2 de capture d'images: {e}")
            
            # Si HTML est disponible et BeautifulSoup est installé, analyser pour trouver les images
            if html_content and bs4_available:
                soup = BeautifulSoup(html_content, 'html.parser')
                img_tags = soup.find_all('img')
                
                for i, img in enumerate(img_tags):
                    try:
                        src = img.get('src', '')
                        if src.startswith('data:image'):
                            # Extraire l'image base64
                            img_data_match = re.search(r'base64,(.*)', src)
                            if img_data_match:
                                img_data = img_data_match.group(1)
                                img_bytes = base64.b64decode(img_data)
                                img_path = f"{temp_dir}/streamlit_img_{i}.png"
                                
                                with open(img_path, 'wb') as f:
                                    f.write(img_bytes)
                                
                                # Vérifier que l'image est valide
                                try:
                                    with Image.open(img_path) as img:
                                        img.verify()
                                    captured_imgs.append({
                                        'path': img_path,
                                        'name': f"Image {i}"
                                    })
                                    logger.info(f"Image HTML capturée: {i}")
                                except Exception as img_err:
                                    logger.error(f"Image HTML invalide {i}: {img_err}")
                    except Exception as e:
                        logger.error(f"Erreur lors de l'extraction de l'image {i}: {e}")
        except Exception as e:
            logger.error(f"Erreur lors de la capture des images Streamlit: {e}")
        
        return captured_imgs

    # Capture des graphiques Matplotlib/Seaborn qui pourraient être dans le registre interne
    def capture_matplotlib_figures():
        """Capture les graphiques Matplotlib/Seaborn actifs."""
        captured_figs = []
        
        try:
            import matplotlib.pyplot as plt
            for i, fig in enumerate(map(plt.figure, plt.get_fignums())):
                try:
                    fig_path = f"{temp_dir}/matplotlib_{i}.png"
                    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
                    
                    # Vérifier que l'image est valide
                    if os.path.exists(fig_path) and os.path.getsize(fig_path) > 100:
                        try:
                            with Image.open(fig_path) as img:
                                img.verify()
                            captured_figs.append({
                                'path': fig_path,
                                'name': f"Graphique Matplotlib {i}"
                            })
                            logger.info(f"Graphique Matplotlib capturé: {i}")
                        except Exception as img_err:
                            logger.error(f"Graphique Matplotlib invalide {i}: {img_err}")
                except Exception as e:
                    logger.error(f"Erreur lors de la capture du graphique Matplotlib {i}: {e}")
        except Exception as e:
            logger.error(f"Erreur lors de la recherche des graphiques Matplotlib: {e}")
        
        return captured_figs

    # Créer une fonction pour capturer tous les graphiques dans la session state
    def capture_all_graphs_in_session():
        """Capture tous les graphiques stockés dans session_state"""
        captured_figs = []
        
        # Liste des clés qui pourraient contenir des graphiques
        graph_indicators = ['chart', 'graph', 'plot', 'fig', 'pie']
        
        for key in st.session_state:
            # Chercher des clés qui pourraient contenir des graphiques
            if any(indicator in key.lower() for indicator in graph_indicators):
                try:
                    # Essayer de sauvegarder comme objet Plotly
                    if hasattr(st.session_state[key], 'write_image'):
                        fig_path = f"{temp_dir}/session_{key}.png"
                        st.session_state[key].write_image(fig_path, width=1000, height=600, scale=2)
                        
                        # Vérifier que l'image est valide
                        if os.path.exists(fig_path) and os.path.getsize(fig_path) > 100:
                            try:
                                with Image.open(fig_path) as img:
                                    img.verify()
                                captured_figs.append({
                                    'path': fig_path,
                                    'name': f"Graphique: {key.replace('_', ' ').title()}"
                                })
                                logger.info(f"Graphique de session capturé: {key}")
                            except Exception as img_err:
                                logger.error(f"Graphique de session invalide {key}: {img_err}")
                                
                    # Essayer de sauvegarder comme objet Matplotlib
                    elif hasattr(st.session_state[key], 'savefig'):
                        fig_path = f"{temp_dir}/session_{key}.png"
                        st.session_state[key].savefig(fig_path, dpi=150, bbox_inches='tight')
                        
                        # Vérifier que l'image est valide
                        if os.path.exists(fig_path) and os.path.getsize(fig_path) > 100:
                            try:
                                with Image.open(fig_path) as img:
                                    img.verify()
                                captured_figs.append({
                                    'path': fig_path,
                                    'name': f"Graphique: {key.replace('_', ' ').title()}"
                                })
                                logger.info(f"Figure de session capturée: {key}")
                            except Exception as img_err:
                                logger.error(f"Figure de session invalide {key}: {img_err}")
                                
                    # Essayer de sauvegarder comme base64 image
                    elif isinstance(st.session_state[key], str) and st.session_state[key].startswith('data:image'):
                        try:
                            img_data_match = re.search(r'base64,(.*)', st.session_state[key])
                            if img_data_match:
                                img_data = img_data_match.group(1)
                                img_bytes = base64.b64decode(img_data)
                                img_path = f"{temp_dir}/session_{key}.png"
                                
                                with open(img_path, 'wb') as f:
                                    f.write(img_bytes)
                                
                                # Vérifier que l'image est valide
                                try:
                                    with Image.open(img_path) as img:
                                        img.verify()
                                    captured_figs.append({
                                        'path': img_path,
                                        'name': f"Image: {key.replace('_', ' ').title()}"
                                    })
                                    logger.info(f"Image base64 de session capturée: {key}")
                                except Exception as img_err:
                                    logger.error(f"Image base64 de session invalide {key}: {img_err}")
                        except Exception as e:
                            logger.error(f"Erreur lors du traitement de l'image base64 {key}: {e}")
                except Exception as e:
                    logger.error(f"Erreur lors de la capture du graphique {key}: {e}")
        
        return captured_figs

    # Fonction pour générer des graphiques à partir des données de session_state
    def generate_additional_charts():
        """Génère des graphiques supplémentaires à partir des données disponibles"""
        generated_charts = []
        
        # 1. Graphique d'évolution du compte de résultat s'il existe dans session_state
        if 'income_statement' in st.session_state:
            try:
                income_data = st.session_state.income_statement
                if income_data:
                    years = ["N", "N+1", "N+2"]
                    
                    # Graphique à barres du CA et des charges
                    ca_key = "Chiffre d'affaires"
                    charges_key = "Charges d'exploitation"
                    
                    if ca_key in income_data and charges_key in income_data:
                        ca = normalize_list(income_data.get(ca_key), 3, 0)
                        charges = normalize_list(income_data.get(charges_key), 3, 0)
                        
                        fig, ax = plt.subplots(figsize=(10, 6))
                        width = 0.35
                        x = np.arange(len(years))
                        
                        rects1 = ax.bar(x - width/2, ca, width, label='Chiffre d\'affaires')
                        rects2 = ax.bar(x + width/2, charges, width, label='Charges d\'exploitation')
                        
                        ax.set_title('Évolution du CA et des charges')
                        ax.set_xlabel('Années')
                        ax.set_ylabel('Montant (DHS)')
                        ax.set_xticks(x)
                        ax.set_xticklabels(years)
                        ax.legend()
                        
                        # Ajouter les valeurs sur chaque barre
                        for rect in rects1:
                            height = rect.get_height()
                            ax.annotate(f'{height:,.0f}',
                                        xy=(rect.get_x() + rect.get_width() / 2, height),
                                        xytext=(0, 3),
                                        textcoords="offset points",
                                        ha='center', va='bottom', rotation=0)
                                        
                        for rect in rects2:
                            height = rect.get_height()
                            ax.annotate(f'{height:,.0f}',
                                        xy=(rect.get_x() + rect.get_width() / 2, height),
                                        xytext=(0, 3),
                                        textcoords="offset points",
                                        ha='center', va='bottom', rotation=0)
                        
                        img_path = save_figure_safely(fig, "ca_charges_evolution.png", temp_dir)
                        if img_path:
                            generated_charts.append({
                                'path': img_path,
                                'name': 'Évolution du CA et des charges'
                            })
                    
                    # Graphique d'évolution du résultat net
                    result_key = 'Résultat net'
                    if result_key in income_data:
                        result = normalize_list(income_data.get(result_key), 3, 0)
                        
                        fig, ax = plt.subplots(figsize=(10, 6))
                        
                        # Utiliser des couleurs différentes selon que le résultat est positif ou négatif
                        colors = ['green' if x >= 0 else 'red' for x in result]
                        ax.bar(years, result, color=colors)
                        
                        ax.set_title('Évolution du résultat net')
                        ax.set_xlabel('Années')
                        ax.set_ylabel('Montant (DHS)')
                        
                        # Ajouter les valeurs sur chaque barre
                        for i, v in enumerate(result):
                            ax.annotate(f'{v:,.0f}',
                                       xy=(i, v),
                                       xytext=(0, 3 if v >= 0 else -15),
                                       textcoords="offset points",
                                       ha='center', va='bottom' if v >= 0 else 'top')
                        
                        img_path = save_figure_safely(fig, "resultat_evolution.png", temp_dir)
                        if img_path:
                            generated_charts.append({
                                'path': img_path,
                                'name': 'Évolution du résultat net'
                            })
            except Exception as e:
                logger.error(f"Erreur lors de la génération des graphiques du compte de résultat: {e}")
        
        # 2. Graphique de répartition des investissements
        if has_data('immos'):
            try:
                immos = st.session_state.immos
                
                # Regrouper par catégorie si disponible
                categories = {}
                for immo in immos:
                    if not isinstance(immo, dict):
                        continue
                    cat = immo.get("Catégorie", "Autre")
                    try:
                        amount = float(immo.get("Montant", 0))
                    except (ValueError, TypeError):
                        amount = 0
                    
                    if cat in categories:
                        categories[cat] += amount
                    else:
                        categories[cat] = amount
                
                # S'il n'y a pas de catégories, regrouper par nom
                if not categories or all(v == 0 for v in categories.values()):
                    categories = {}
                    for immo in immos:
                        if not isinstance(immo, dict):
                            continue
                        name = immo.get("Nom", "Non spécifié")
                        try:
                            amount = float(immo.get("Montant", 0))
                        except (ValueError, TypeError):
                            amount = 0
                        categories[name] = amount
                
                # Créer un graphique en camembert
                if categories and any(v > 0 for v in categories.values()):
                    fig, ax = plt.subplots(figsize=(10, 8))
                    # Créer un tableau explode de la bonne taille
                    explode = [0.1] + [0] * (len(categories) - 1) if len(categories) > 0 else []
                    
                    wedges, texts, autotexts = ax.pie(
                        list(categories.values()),
                        explode=explode[:len(categories)] if explode else None,
                        labels=list(categories.keys()),
                        autopct='%1.1f%%',
                        shadow=True,
                        startangle=90
                    )
                    
                    # Mettre les labels en blanc pour meilleure visibilité
                    for autotext in autotexts:
                        autotext.set_color('white')
                    
                    ax.axis('equal')
                    ax.set_title('Répartition des investissements')
                    
                    img_path = save_figure_safely(fig, "investments_distribution.png", temp_dir)
                    if img_path:
                        generated_charts.append({
                            'path': img_path,
                            'name': 'Répartition des investissements'
                        })
            except Exception as e:
                logger.error(f"Erreur lors de la génération des graphiques d'investissements: {e}")
        
        # 3. Génération des graphes d'amortissements détaillés
        if has_data('detailed_amortization'):
            try:
                # Graphique de répartition par montant d'amortissement
                detailed_amortization = st.session_state.detailed_amortization
                
                # Préparer les données
                immobilisations = [item["name"] for item in detailed_amortization if item["amount"] > 0]
                amounts = [item["amount"] for item in detailed_amortization if item["amount"] > 0]
                
                if immobilisations and amounts:
                    # Graphique en camembert de répartition
                    fig, ax = plt.subplots(figsize=(10, 8))
                    wedges, texts, autotexts = ax.pie(
                        amounts,
                        labels=immobilisations,
                        autopct='%1.1f%%',
                        shadow=True,
                        startangle=90
                    )
                    
                    for autotext in autotexts:
                        autotext.set_color('white')
                    
                    ax.axis('equal')
                    ax.set_title('Répartition des immobilisations à amortir')
                    
                    img_path = save_figure_safely(fig, "amortization_distribution.png", temp_dir)
                    if img_path:
                        generated_charts.append({
                            'path': img_path,
                            'name': 'Répartition des immobilisations à amortir'
                        })
                
                # Graphique d'évolution des amortissements
                years = ["N", "N+1", "N+2"]  # Ajoutez plus d'années si nécessaire
                yearly_data = {}
                
                for item in detailed_amortization:
                    if item["amount"] > 0:
                        yearly_amort = []
                        yearly_amort.append(item["amortization_n"])
                        yearly_amort.append(item["amortization_n1"])
                        yearly_amort.append(item["amortization_n2"])
                        
                        yearly_data[item["name"]] = yearly_amort
                
                if yearly_data:
                    # Créer un DataFrame pour le graphique
                    yearly_df = pd.DataFrame(yearly_data, index=years)
                    
                    # Transposer pour faciliter le tracé
                    yearly_df_t = yearly_df.transpose()
                    
                    fig, ax = plt.subplots(figsize=(12, 8))
                    yearly_df_t.plot(kind='bar', ax=ax, width=0.8)
                    
                    ax.set_title('Évolution des amortissements par immobilisation')
                    ax.set_xlabel('Immobilisation')
                    ax.set_ylabel('Montant (DHS)')
                    ax.legend(title='Année')
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()
                    
                    img_path = save_figure_safely(fig, "amortization_evolution.png", temp_dir)
                    if img_path:
                        generated_charts.append({
                            'path': img_path,
                            'name': 'Évolution des amortissements par immobilisation'
                        })
                
                # Graphique empilé d'évolution totale des amortissements
                if yearly_data:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    
                    # Calculer les totaux par année
                    yearly_totals = [0] * len(years)
                    for item_values in yearly_data.values():
                        for i, val in enumerate(item_values):
                            yearly_totals[i] += val
                    
                    ax.bar(years, yearly_totals, color='#3b82f6')
                    
                    # Ajouter les valeurs sur les barres
                    for i, total in enumerate(yearly_totals):
                        ax.annotate(f'{total:,.0f}',
                                   xy=(i, total),
                                   xytext=(0, 3),
                                   textcoords="offset points",
                                   ha='center', va='bottom')
                    
                    ax.set_title('Amortissements totaux par année')
                    ax.set_xlabel('Année')
                    ax.set_ylabel('Montant total (DHS)')
                    
                    img_path = save_figure_safely(fig, "total_amortization_by_year.png", temp_dir)
                    if img_path:
                        generated_charts.append({
                            'path': img_path,
                            'name': 'Amortissements totaux par année'
                        })
            except Exception as e:
                logger.error(f"Erreur lors de la génération des graphiques d'amortissements: {e}")
        
        # 4. Tableau de trésorerie mensuelle
        if has_data('monthly_cashflow_data'):
            try:
                monthly_data = st.session_state.monthly_cashflow_data
                
                # Calculer le flux mensuel de façon sécurisée
                def safe_sum(dict_data):
                    if not isinstance(dict_data, dict):
                        return 0
                    total = 0
                    for value in dict_data.values():
                        try:
                            if isinstance(value, (int, float)):
                                total += value
                            elif isinstance(value, str):
                                total += float(value.replace(',', ''))
                        except:
                            pass
                    return total
                    
                total_revenue = safe_sum(monthly_data.get('chiffre_affaires', {}))
                total_expenses = safe_sum(monthly_data.get('charges_exploitation', {}))
                monthly_balance = total_revenue - total_expenses
                
                # Calculer les soldes sur 12 mois
                months = range(1, 13)
                
                # Solde initial = ressources - immobilisations
                initial_balance = safe_sum(monthly_data.get('ressources', {})) - safe_sum(monthly_data.get('immobilisations', {}))
                
                balances = [initial_balance]
                for _ in range(12):
                    balances.append(balances[-1] + monthly_balance)
                
                # Créer le graphique d'évolution de trésorerie
                fig, ax = plt.subplots(figsize=(12, 7))
                ax.plot(months, balances[1:], marker='o', linewidth=2, markersize=8)
                
                # Ajouter une ligne à zéro pour référence
                ax.axhline(y=0, color='r', linestyle='-', alpha=0.3)
                
                # Ajouter des étiquettes
                for i, balance in enumerate(balances[1:]):
                    ax.annotate(f'{balance:,.0f}',
                               xy=(i+1, balance),
                               xytext=(0, 10 if balance >= 0 else -15),
                               textcoords="offset points",
                               ha='center')
                
                ax.set_xlabel('Mois')
                ax.set_ylabel('Solde (DHS)')
                ax.set_title('Évolution du solde de trésorerie sur 12 mois')
                ax.grid(True, alpha=0.3)
                
                img_path = save_figure_safely(fig, "monthly_treasury_evolution.png", temp_dir)
                if img_path:
                    generated_charts.append({
                        'path': img_path,
                        'name': 'Évolution du solde de trésorerie mensuel'
                    })
                
                # Graphique de répartition recettes/dépenses par mois
                fig, ax = plt.subplots(figsize=(12, 7))
                x = np.arange(len(months[:6]))  # Limiter à 6 mois pour la lisibilité
                width = 0.35
                
                recettes = [total_revenue] * 6
                depenses = [total_expenses] * 6
                
                ax.bar(x - width/2, recettes, width, label='Recettes', color='#4CAF50')
                ax.bar(x + width/2, depenses, width, label='Dépenses', color='#F44336')
                
                for i, (rec, dep) in enumerate(zip(recettes, depenses)):
                    ax.annotate(f'{rec:,.0f}',
                               xy=(i - width/2, rec),
                               xytext=(0, 3),
                               textcoords="offset points",
                               ha='center', va='bottom')
                    ax.annotate(f'{dep:,.0f}',
                               xy=(i + width/2, dep),
                               xytext=(0, 3),
                               textcoords="offset points",
                               ha='center', va='bottom')
                
                ax.set_ylabel('Montant (DHS)')
                ax.set_title('Recettes et dépenses mensuelles')
                ax.set_xticks(x)
                ax.set_xticklabels([f"Mois {i+1}" for i in range(6)])
                ax.legend()
                
                img_path = save_figure_safely(fig, "monthly_receipts_expenses.png", temp_dir)
                if img_path:
                    generated_charts.append({
                        'path': img_path,
                        'name': 'Recettes et dépenses mensuelles'
                    })
            except Exception as e:
                logger.error(f"Erreur lors de la génération des graphiques de trésorerie mensuelle: {e}")
        
        # 5. Budget TVA - Graphiques
        if has_data('vat_budget_data'):
            try:
                vat_data = st.session_state.vat_budget_data
                
                # Fonction sécurisée pour extraire les valeurs de TVA
                def safe_tva_sum(section_data, key_filter=None):
                    if not isinstance(section_data, dict):
                        return 0
                    total = 0
                    for key, value in section_data.items():
                        if key_filter and key_filter not in key.lower():
                            continue
                        try:
                            if isinstance(value, (int, float)):
                                total += value
                            elif isinstance(value, str):
                                total += float(value.replace(',', ''))
                        except (ValueError, TypeError):
                            pass
                    return total
                
                # Calculer les montants de TVA
                tva_collectee = safe_tva_sum(vat_data.get("ventes", {}), "tva")
                tva_deductible_achats = safe_tva_sum(vat_data.get("achats", {}), "tva")
                tva_deductible_immo = safe_tva_sum(vat_data.get("tva_immobilisations", {}))
                tva_nette = tva_collectee - tva_deductible_achats - tva_deductible_immo
                
                # Créer un graphique en barres des composantes de la TVA
                fig, ax = plt.subplots(figsize=(12, 7))
                components = ['TVA Collectée', 'TVA Déductible\nAchats', 'TVA Déductible\nImmos', 'TVA Nette']
                values = [tva_collectee, tva_deductible_achats, tva_deductible_immo, tva_nette]
                colors = ['#4CAF50', '#2196F3', '#FFC107', '#FF5722' if tva_nette >= 0 else '#F44336']
                
                bars = ax.bar(components, values, color=colors)
                
                # Ajouter les valeurs sur les barres
                for bar in bars:
                    height = bar.get_height()
                    ax.annotate(f'{height:,.0f}',
                              xy=(bar.get_x() + bar.get_width() / 2, height),
                              xytext=(0, 3 if height >= 0 else -15),
                              textcoords="offset points",
                              ha='center', va='bottom' if height >= 0 else 'top')
                
                ax.set_title("Analyse des composants de la TVA")
                ax.set_ylabel("Montant (DHS)")
                ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
                
                img_path = save_figure_safely(fig, "vat_components.png", temp_dir)
                if img_path:
                    generated_charts.append({
                        'path': img_path,
                        'name': 'Analyse des composants de la TVA'
                    })
                
                # Graphique en camembert de la TVA déductible
                if tva_deductible_achats > 0 or tva_deductible_immo > 0:
                    fig, ax = plt.subplots(figsize=(10, 8))
                    labels = ['TVA Déductible Achats', 'TVA Déductible Immos']
                    values = [tva_deductible_achats, tva_deductible_immo]
                    colors = ['#2196F3', '#FFC107']
                    
                    # Filtrer les valeurs nulles
                    non_zero = [(label, value, color) 
                                for label, value, color in zip(labels, values, colors) 
                                if value > 0]
                    
                    if non_zero:
                        wedges, texts, autotexts = ax.pie(
                            [item[1] for item in non_zero],
                            labels=[item[0] for item in non_zero],
                            colors=[item[2] for item in non_zero],
                            autopct='%1.1f%%',
                            shadow=True,
                            startangle=90
                        )
                        
                        for autotext in autotexts:
                            autotext.set_color('white')
                        
                        ax.axis('equal')
                        ax.set_title('Répartition de la TVA déductible')
                        
                        img_path = save_figure_safely(fig, "vat_deductible_pie.png", temp_dir)
                        if img_path:
                            generated_charts.append({
                                'path': img_path,
                                'name': 'Répartition de la TVA déductible'
                            })
                
                # Projection des soldes de TVA sur 12 mois
                months = range(1, 13)
                # Créer une légère variation pour le réalisme
                import random
                random.seed(42)
                variations = [random.uniform(0.95, 1.05) for _ in range(12)]
                tva_nette_months = [tva_nette * v for v in variations]
                
                fig, ax = plt.subplots(figsize=(12, 7))
                ax.plot(months, tva_nette_months, marker='o', linestyle='-', color='#FF5722', linewidth=2)
                
                # Ajouter une ligne à zéro
                ax.axhline(y=0, color='gray', linestyle='--', alpha=0.3)
                
                # Ajouter les valeurs sur les points
                for i, value in enumerate(tva_nette_months):
                    ax.annotate(f'{value:,.0f}',
                              xy=(months[i], value),
                              xytext=(0, 10 if value >= 0 else -15),
                              textcoords="offset points",
                              ha='center')
                
                ax.set_xlabel('Mois')
                ax.set_ylabel('TVA nette (DHS)')
                ax.set_title('Projection de la TVA nette sur 12 mois')
                ax.grid(True, alpha=0.3)
                
                img_path = save_figure_safely(fig, "vat_projection.png", temp_dir)
                if img_path:
                    generated_charts.append({
                        'path': img_path,
                        'name': 'Projection de la TVA nette sur 12 mois'
                    })
            except Exception as e:
                logger.error(f"Erreur lors de la génération des graphiques de TVA: {e}")
                
        return generated_charts
    
    # Commencer la génération du PDF avec gestion d'erreurs
    try:
        pdf = PDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        
        # Informations générales
        if "Informations générales" in sections and has_data("basic_info"):
            pdf.chapter_title("Informations generales")
            
            # Récupération sécurisée des données
            basic_info = st.session_state.basic_info or {}
            
            # Correction pour éviter l'erreur strftime
            creation_date = basic_info.get('creation_date')
            if isinstance(creation_date, datetime):
                creation_date_str = creation_date.strftime('%d/%m/%Y')
            elif isinstance(creation_date, str):
                # Si c'est déjà une chaîne, l'utiliser directement
                creation_date_str = creation_date
            else:
                # Valeur par défaut si non disponible
                creation_date_str = datetime.now().strftime('%d/%m/%Y')
            
            info_text = f"""
Nom de l'entreprise: {ascii_only(basic_info.get('company_name', 'Non specifie'))}
Forme juridique: {ascii_only(basic_info.get('company_type', 'Non specifie'))}
Date de creation: {ascii_only(creation_date_str)}
Secteur d'activite: {ascii_only(basic_info.get('sector', 'Non specifie'))}
Adresse: {ascii_only(basic_info.get('address', 'Non specifie'))}
            """
            pdf.chapter_body(info_text)
        
        # Importation CSV
        if "📤 Importation CSV" in sections:
            pdf.add_page()
            pdf.chapter_title("Importation et Analyse des Donnees Financieres")
            try:
                # Tenter d'accéder aux données CSV importées, si elles existent
                df_csv = None
                if "imported_csv" in st.session_state:
                    df_csv = st.session_state.imported_csv
                
                if df_csv is None and hasattr(st.session_state, "processed_df"):
                    df_csv = st.session_state.processed_df
                    
                if isinstance(df_csv, pd.DataFrame) and not df_csv.empty:
                    pdf.set_font("Arial", "B", 9)
                    headers = df_csv.columns.tolist()
                    pdf.cell(0, 7, ascii_only("Apercu des 10 premieres lignes du CSV importe:"), 0, 1, "L")
                    
                    # Utiliser la nouvelle méthode add_table
                    table_data = []
                    for idx, row in df_csv.head(10).iterrows():
                        table_data.append([str(val) for val in row])
                    pdf.add_table(headers, table_data)
                    
                    # Ajouter un résumé des métriques financières, si disponible
                    if hasattr(st.session_state, "metrics") and st.session_state.metrics:
                        pdf.ln(10)
                        pdf.set_font("Arial", "B", 10)
                        pdf.cell(0, 7, ascii_only("Synthese des Metriques Financieres:"), 0, 1, "L")
                        
                        metrics = st.session_state.metrics
                        metrics_table = [
                            ["Metriques", "Valeur"],
                            ["Total Immobilisations", f"{metrics.get('total_immobilisations', 0):,.2f} DHS"],
                            ["Total Financements", f"{metrics.get('total_financements', 0):,.2f} DHS"],
                            ["Charges Mensuelles", f"{metrics.get('total_charges', 0):,.2f} DHS"],
                            ["Ventes Mensuelles", f"{metrics.get('total_ventes', 0):,.2f} DHS"],
                            ["Cash-Flow Mensuel", f"{metrics.get('cash_flow_mensuel', 0):,.2f} DHS"],
                            ["ROI Annuel", f"{metrics.get('roi_annuel', 0)*100:.2f}%"],
                            ["Delai de Recuperation", f"{metrics.get('payback_months', 0):.1f} mois"]
                        ]
                        pdf.add_table(["Metriques", "Valeur"], metrics_table[1:], [120, 60])
                        
                    # Ajouter les graphiques de l'import CSV
                    # Ici nous générons des graphiques supplémentaires pour l'analyse des données importées
                    pdf.add_page()
                    pdf.chapter_title("Analyses graphiques des données CSV")
                    
                    # Répartition par type
                    if 'type' in df_csv.columns:
                        try:
                            type_counts = df_csv['type'].value_counts()
                            fig, ax = plt.subplots(figsize=(8, 6))
                            ax.pie(type_counts.values, labels=type_counts.index, autopct='%1.1f%%')
                            ax.axis('equal')
                            plt.title("Répartition par type de données")
                            
                            img_path = save_figure_safely(fig, "csv_type_pie.png", temp_dir)
                            if img_path:
                                pdf.add_image(img_path, w=180, caption="Répartition par type de données")
                                pdf.ln(5)
                        except Exception as e:
                            logger.error(f"Erreur graphique répartition CSV: {e}")
                    
                    # Distribution numérique
                    try:
                        numeric_cols = df_csv.select_dtypes(include=['int64', 'float64']).columns.tolist()
                        if len(numeric_cols) > 0 and len(numeric_cols) <= 5:
                            fig, ax = plt.subplots(figsize=(10, 6))
                            for col in numeric_cols:
                                if not df_csv[col].isnull().all():
                                    sns.histplot(df_csv[col].dropna(), kde=True, label=col, ax=ax)
                            
                            ax.set_title('Distribution des variables numériques')
                            ax.legend()
                            
                            img_path = save_figure_safely(fig, "csv_numeric_distribution.png", temp_dir)
                            if img_path:
                                pdf.add_image(img_path, w=180, caption="Distribution des variables numériques")
                                pdf.ln(5)
                    except Exception as e:
                        logger.error(f"Erreur distribution numérique CSV: {e}")
                else:
                    pdf.chapter_body("Aucune donnee CSV importee ou CSV vide.")
            except Exception as e:
                logger.error(f"Erreur lors de l'affichage du CSV importé: {e}")
                pdf.chapter_body(f"Erreur lors de l'affichage du CSV importe: {ascii_only(str(e))}")

        # Investissements
        if "Investissements" in sections and has_data("immos"):
            pdf.add_page()
            pdf.chapter_title("Investissements et financement")
            
            immos = st.session_state.immos
            immo_table_data = [["Nom", "Categorie", "Montant (DHS)"]]
            total_immo = 0
            
            for immo in immos:
                if not isinstance(immo, dict):
                    continue
                
                try:
                    montant = float(immo.get("Montant", 0))
                except (ValueError, TypeError):
                    montant = 0
                
                immo_table_data.append([
                    ascii_only(immo.get("Nom", "Non specifie")),
                    ascii_only(immo.get("Catégorie", "Non specifie")),
                    f"{montant:,.2f}"
                ])
                total_immo += montant
            
            immo_table_data.append(["TOTAL", "", f"{total_immo:,.2f}"])
            pdf.ln(5)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 5, ascii_only("Tableau des immobilisations"), 0, 1, "L")
            pdf.ln(5)
            
            # Utiliser add_table pour des tableaux plus robustes
            pdf.add_table(["Nom", "Categorie", "Montant (DHS)"], immo_table_data[1:], [70, 60, 40])
            
            try:
                immo_by_cat = {}
                for immo in immos:
                    if not isinstance(immo, dict):
                        continue
                    
                    cat = ascii_only(immo.get("Catégorie", "Autre"))
                    try:
                        amount = float(immo.get("Montant", 0))
                    except (ValueError, TypeError):
                        amount = 0
                    
                    if cat in immo_by_cat:
                        immo_by_cat[cat] += amount
                    else:
                        immo_by_cat[cat] = amount
                
                if immo_by_cat and any(v > 0 for v in immo_by_cat.values()):
                    fig, ax = plt.subplots(figsize=(8, 6))
                    ax.pie(immo_by_cat.values(), labels=immo_by_cat.keys(), autopct='%1.1f%%', startangle=90)
                    ax.axis('equal')
                    plt.title("Repartition des investissements par categorie")
                    
                    img_path = save_figure_safely(fig, "investments_pie.png", temp_dir)
                    if img_path:
                        pdf.ln(10)
                        pdf.add_image(img_path, w=180, caption="Repartition des investissements par categorie")
            except Exception as e:
                logger.error(f"Erreur graphique investissements: {e}")
                pdf.chapter_body(f"Erreur graphique investissements: {ascii_only(str(e))}")

        # Bilan prévisionnel (actif/passif)
        if "Bilan prévisionnel" in sections:
            pdf.add_page()
            pdf.chapter_title("Bilan previsionnel")
            total_actif = 0
            
            if has_data("actif_data"):
                actif_data = st.session_state.actif_data
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 10, ascii_only("ACTIF"), 0, 1, "L")
                actif_groups = {
                    "Immobilisations incorporelles": actif_data.get("immobilisations_incorporelles", []),
                    "Immobilisations corporelles": actif_data.get("immobilisations_corporelles", []),
                    "Actif circulant": actif_data.get("stocks", []),
                    "Tresorerie - Actif": actif_data.get("tresorerie_actif", [])
                }
                
                for group_name, items in actif_groups.items():
                    if not items:  # Ignorer les groupes vides
                        continue
                        
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 8, ascii_only(group_name), 0, 1, "L")
                    group_total = 0
                    
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                            
                        pdf.set_font("Arial", "", 9)
                        label = item.get("label", "")
                        try:
                            amount = float(item.get("value", 0))
                        except (ValueError, TypeError):
                            amount = 0
                        
                        pdf.cell(100, 6, ascii_only(label), 1, 0, "L")
                        pdf.cell(80, 6, f"{amount:,.2f} DHS", 1, 1, "R")
                        group_total += amount
                    
                    pdf.set_font("Arial", "B", 9)
                    pdf.cell(100, 6, ascii_only(f"Total {group_name}"), 1, 0, "L")
                    pdf.cell(80, 6, f"{group_total:,.2f} DHS", 1, 1, "R")
                    total_actif += group_total
                    pdf.ln(5)
                
                pdf.set_font("Arial", "B", 10)
                pdf.cell(100, 8, ascii_only("TOTAL ACTIF"), 1, 0, "L")
                pdf.cell(80, 8, f"{total_actif:,.2f} DHS", 1, 1, "R")
            
            total_passif = 0
            if has_data("passif_data"):
                passif_data = st.session_state.passif_data
                pdf.add_page()
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 10, ascii_only("PASSIF"), 0, 1, "L")
                passif_groups = {
                    "Capitaux propres": passif_data.get("capitaux_propres", []),
                    "Dettes de financement": passif_data.get("dettes_financement", []),
                    "Passif circulant": passif_data.get("passif_circulant", []),
                    "Tresorerie - Passif": passif_data.get("tresorerie_passif", [])
                }
                
                for group_name, items in passif_groups.items():
                    if not items:  # Ignorer les groupes vides
                        continue
                        
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 8, ascii_only(group_name), 0, 1, "L")
                    group_total = 0
                    
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                            
                        pdf.set_font("Arial", "", 9)
                        label = item.get("label", "")
                        try:
                            amount = float(item.get("value", 0))
                        except (ValueError, TypeError):
                            amount = 0
                        
                        pdf.cell(100, 6, ascii_only(label), 1, 0, "L")
                        pdf.cell(80, 6, f"{amount:,.2f} DHS", 1, 1, "R")
                        group_total += amount
                    
                    pdf.set_font("Arial", "B", 9)
                    pdf.cell(100, 6, ascii_only(f"Total {group_name}"), 1, 0, "L")
                    pdf.cell(80, 6, f"{group_total:,.2f} DHS", 1, 1, "R")
                    total_passif += group_total
                    pdf.ln(5)
                
                pdf.set_font("Arial", "B", 10)
                pdf.cell(100, 8, ascii_only("TOTAL PASSIF"), 1, 0, "L")
                pdf.cell(80, 8, f"{total_passif:,.2f} DHS", 1, 1, "R")
                pdf.ln(10)
                
                if abs(total_actif - total_passif) < 0.01:
                    pdf.set_text_color(0, 128, 0)
                    pdf.cell(0, 8, ascii_only("OK Le bilan est equilibre"), 0, 1, "L")
                else:
                    pdf.set_text_color(255, 0, 0)
                    pdf.cell(0, 8, ascii_only(f"ATTENTION Le bilan n'est pas equilibre (Difference: {abs(total_actif - total_passif):,.2f} DHS)"), 0, 1, "L")
                pdf.set_text_color(0, 0, 0)

        # Compte de résultat
        if "Compte de résultat" in sections and has_data("income_statement"):
            pdf.add_page()
            pdf.chapter_title("Compte de resultat previsionnel")
            
            income_data = st.session_state.income_statement
            
            # Normaliser les données pour éviter les erreurs d'index
            ca_values = normalize_list(income_data.get("Chiffre d'affaires", []), 3, 0)
            charges_values = normalize_list(income_data.get("Charges d'exploitation", []), 3, 0)
            result_exploit_values = normalize_list(income_data.get("Resultat d'exploitation", []), 3, 0)
            charges_fin = normalize_list(income_data.get("Charges financieres", []), 3, 0)
            impots = normalize_list(income_data.get("Impots sur les resultats", []), 3, 0)
            result_net = normalize_list(income_data.get("Résultat net", []), 3, 0)
            
            years = ["Année N", "Année N+1", "Année N+2"]
            headers = ["Rubrique"] + years
            table_data = [
                ["Chiffre d'affaires"] + [f"{val:,.2f}" for val in ca_values],
                ["Charges d'exploitation"] + [f"{val:,.2f}" for val in charges_values],
                ["Résultat d'exploitation"] + [f"{val:,.2f}" for val in result_exploit_values],
                ["Charges financières"] + [f"{val:,.2f}" for val in charges_fin],
                ["Impôts sur les résultats"] + [f"{val:,.2f}" for val in impots],
                ["Résultat net"] + [f"{val:,.2f}" for val in result_net],
            ]
            
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 8, ascii_only("Compte de résultat sur 3 ans"), 0, 1, "L")
            pdf.add_table(headers, table_data, [50, 40, 40, 40])
            
            # Ajouter un graphique d'évolution du résultat net
            try:
                fig, ax = plt.subplots(figsize=(10, 6))
                x = np.arange(len(years))
                width = 0.35
                
                ax.bar(x - width/2, ca_values, width, label="CA")
                ax.bar(x + width/2, result_net, width, label="Résultat net")
                
                ax.set_xlabel('Années')
                ax.set_ylabel('Montant (DHS)')
                ax.set_title('Évolution du CA et du résultat net')
                ax.set_xticks(x)
                ax.set_xticklabels(years)
                ax.legend()
                
                for i, v in enumerate(ca_values):
                    ax.text(i - width/2, v + 0.1, f"{v:,.0f}", ha='center')
                
                for i, v in enumerate(result_net):
                    ax.text(i + width/2, v + 0.1, f"{v:,.0f}", ha='center')
                
                img_path = save_figure_safely(fig, "income_evolution.png", temp_dir)
                if img_path:
                    pdf.ln(5)
                    pdf.add_image(img_path, w=180, caption="Évolution du CA et du résultat net")
            except Exception as e:
                logger.error(f"Erreur lors de la génération du graphique d'évolution: {e}")
                pdf.chapter_body(f"Erreur lors de la génération du graphique d'évolution: {ascii_only(str(e))}")

        # Cash-flow et analyse de rentabilité
        if "Cash-flow" in sections and (has_data("cashflow_data") or hasattr(st.session_state, "calculated_data")):
            pdf.add_page()
            pdf.chapter_title("Analyse du Cash Flow")
            
            # Traitement des données du tableau de cash flow
            cashflow_data = None
            if has_data("cashflow_data"):
                cashflow_data = st.session_state.cashflow_data
            
            # Afficher le tableau de cash flow si disponible
            if isinstance(cashflow_data, pd.DataFrame) and not cashflow_data.empty:
                try:
                    headers = cashflow_data.columns.tolist()
                    table_data = []
                    
                    for idx, row in cashflow_data.head(15).iterrows():  # Limiter à 15 lignes pour le PDF
                        table_data.append([str(val) for val in row])
                    
                    pdf.add_table(headers, table_data)
                except Exception as e:
                    logger.error(f"Erreur lors de l'affichage du tableau de cash flow: {e}")
                    pdf.chapter_body(f"Erreur lors de l'affichage du tableau de cash flow: {ascii_only(str(e))}")
            elif hasattr(st.session_state, "calculated_data"):
                # Si les données sont en format dict ou autre
                calculated_data = st.session_state.calculated_data
                pdf.chapter_body("Synthese du cash flow:")
                
                try:
                    total_investissement = float(calculated_data.total_investissement) if hasattr(calculated_data, "total_investissement") else 0
                    total_ca_monthly = float(calculated_data.total_ca_monthly) if hasattr(calculated_data, "total_ca_monthly") else 0
                    total_charges_monthly = float(calculated_data.total_charges_monthly) if hasattr(calculated_data, "total_charges_monthly") else 0
                    cash_flow_mensuel = float(calculated_data.cash_flow_mensuel) if hasattr(calculated_data, "cash_flow_mensuel") else 0
                    
                    data = [
                        ["Métrique", "Valeur"],
                        ["Investissement total", f"{total_investissement:,.2f} DHS"],
                        ["CA mensuel", f"{total_ca_monthly:,.2f} DHS"],
                        ["Charges mensuelles", f"{total_charges_monthly:,.2f} DHS"],
                        ["Cash-flow mensuel", f"{cash_flow_mensuel:,.2f} DHS"],
                    ]
                    
                    if hasattr(calculated_data, "payback_months"):
                        payback = float(calculated_data.payback_months)
                        data.append(["Délai de récupération", f"{payback:.1f} mois"])
                    
                    if hasattr(calculated_data, "roi_annuel"):
                        roi = float(calculated_data.roi_annuel)
                        data.append(["ROI annuel", f"{roi*100:.2f}%"])
                    
                    pdf.add_table(["Métrique", "Valeur"], data[1:], [120, 60])
                except Exception as e:
                    logger.error(f"Erreur lors de l'affichage des métriques: {e}")
                    pdf.chapter_body(f"Erreur lors de l'affichage des métriques: {ascii_only(str(e))}")
            
            # Afficher les détails du cash flow par catégorie
            if has_data("cash_flow_categories") or hasattr(st.session_state, "cash_flow_detailed"):
                pdf.ln(10)
                pdf.chapter_title("Détails du cash flow par catégorie")
                
                # Récupération des données de catégories
                cf_categories = None
                if "cash_flow_categories" in st.session_state:
                    cf_categories = st.session_state.cash_flow_categories
                elif hasattr(st.session_state, "cash_flow_detailed"):
                    cf_categories = st.session_state.cash_flow_detailed
                
                if isinstance(cf_categories, dict):
                    for category, data in cf_categories.items():
                        pdf.set_font("Arial", "B", 10)
                        pdf.cell(0, 8, ascii_only(f"Catégorie: {category}"), 0, 1, "L")
                        
                        if isinstance(data, dict):
                            headers = ["Élément", "Montant (DHS)"]
                            table_data = []
                            
                            for key, value in data.items():
                                try:
                                    if isinstance(value, (int, float)):
                                        table_data.append([key, f"{value:,.2f}"])
                                    else:
                                        table_data.append([key, str(value)])
                                except Exception as e:
                                    logger.error(f"Erreur conversion {key}: {e}")
                                    table_data.append([key, "N/A"])
                            
                            pdf.add_table(headers, table_data, [120, 60])
                            pdf.ln(5)
                        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
                            # Pour les listes de dictionnaires
                            if data:
                                # Prendre les clés du premier dictionnaire comme en-têtes
                                headers = list(data[0].keys())
                                table_data = []
                                
                                for item in data:
                                    row = []
                                    for header in headers:
                                        value = item.get(header, 0)
                                        if isinstance(value, (int, float)):
                                            row.append(f"{value:,.2f}")
                                        else:
                                            row.append(str(value))
                                    table_data.append(row)
                                
                                pdf.add_table(headers, table_data)
                                pdf.ln(5)
                
                # Générer un graphique de répartition du cash flow par catégorie
                try:
                    categories = {}
                    
                    # Essayer de récupérer les données de différentes sources possibles
                    if cf_categories:
                        for cat, data in cf_categories.items():
                            if isinstance(data, dict):
                                total = 0
                                for key, value in data.items():
                                    try:
                                        if isinstance(value, (int, float)):
                                            total += value
                                        elif isinstance(value, str) and value.replace('.', '').replace(',', '').isdigit():
                                            total += float(value.replace(',', ''))
                                    except (ValueError, TypeError):
                                        pass
                                categories[cat] = total
                    
                    if categories and any(v != 0 for v in categories.values()):
                        fig, ax = plt.subplots(figsize=(10, 8))
                        ax.pie(
                            list(categories.values()),
                            labels=list(categories.keys()),
                            autopct='%1.1f%%',
                            startangle=90
                        )
                        ax.axis('equal')
                        
                        img_path = save_figure_safely(fig, "cashflow_by_category.png", temp_dir)
                        if img_path:
                            pdf.ln(10)
                            pdf.add_image(img_path, w=180, caption="Répartition du cash flow par catégorie")
                except Exception as e:
                    logger.error(f"Erreur lors de la génération du graphique par catégorie: {e}")
                    pdf.chapter_body(f"Erreur lors de la génération du graphique par catégorie: {ascii_only(str(e))}")

        # Amortissements
        if "Amortissements" in sections:
            pdf.add_page()
            pdf.chapter_title("Tableau d'Amortissement du Credit")
            
            # Vérifier si des crédits sont disponibles
            if has_data("credits"):
                # Pour chaque crédit, afficher un tableau d'amortissement résumé
                for i, credit in enumerate(st.session_state.credits):
                    if not isinstance(credit, dict):
                        continue
                    
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 8, ascii_only(f"Credit: {credit.get('Nom', f'Credit {i+1}')}"), 0, 1, "L")
                    
                    try:
                        principal = float(credit.get("Montant", 0))
                    except (ValueError, TypeError):
                        principal = 0
                    
                    try:
                        rate = float(credit.get("Taux", 0))
                    except (ValueError, TypeError):
                        rate = 0
                    
                    try:
                        term = int(credit.get("Durée", 0))
                    except (ValueError, TypeError):
                        term = 0
                    
                    pdf.set_font("Arial", "", 9)
                    pdf.cell(0, 6, ascii_only(f"Montant: {principal:,.2f} DHS | Taux: {rate:.2f}% | Duree: {term} ans"), 0, 1, "L")
                    
                    # Générer un tableau d'amortissement simplifié
                    # Calculer les échéances pour le crédit actuel
                    if principal > 0 and rate > 0 and term > 0:
                        monthly_rate = rate / 100 / 12
                        nb_payments = term * 12
                        
                        if monthly_rate > 0:
                            monthly_payment = principal * monthly_rate * (1 + monthly_rate) ** nb_payments / ((1 + monthly_rate) ** nb_payments - 1)
                        else:
                            monthly_payment = principal / nb_payments
                        
                        # Générer un résumé annuel
                        annual_summary = []
                        remaining_principal = principal
                        
                        for year in range(1, term + 1):
                            annual_interest = 0
                            annual_principal = 0
                            
                            for month in range(1, 13):
                                if year * 12 + month > nb_payments:
                                    break
                                
                                month_interest = remaining_principal * monthly_rate
                                month_principal = monthly_payment - month_interest
                                
                                annual_interest += month_interest
                                annual_principal += month_principal
                                remaining_principal -= month_principal
                            
                            annual_summary.append([
                                year,
                                annual_principal,
                                annual_interest,
                                monthly_payment * 12,
                                remaining_principal
                            ])
                        
                        # Créer le tableau
                        table_headers = ["Année", "Capital", "Intérêts", "Annuité", "Capital restant"]
                        table_data = []
                        
                        total_principal = 0
                        total_interest = 0
                        
                        for row in annual_summary:
                            table_data.append([
                                str(row[0]),
                                f"{row[1]:,.2f}",
                                f"{row[2]:,.2f}",
                                f"{row[3]:,.2f}",
                                f"{row[4]:,.2f}"
                            ])
                            total_principal += row[1]
                            total_interest += row[2]
                        
                        pdf.ln(5)
                        pdf.add_table(table_headers, table_data, [20, 40, 40, 40, 40])
                        pdf.ln(5)
                        
                        # Totaux
                        pdf.set_font("Arial", "B", 9)
                        pdf.cell(0, 6, ascii_only(f"Total capital: {total_principal:,.2f} DHS | Total interêts: {total_interest:,.2f} DHS | Coût total du crédit: {(total_principal + total_interest):,.2f} DHS"), 0, 1, "L")
                        pdf.ln(5)
                        
                        # Ajouter un graphique de répartition capital/intérêts
                        try:
                            fig, ax = plt.subplots(figsize=(10, 6))
                            ax.pie([total_principal, total_interest], 
                                  labels=["Capital", "Intérêts"], 
                                  explode=(0, 0.1), 
                                  autopct='%1.1f%%', 
                                  startangle=90)
                            ax.axis('equal')
                            
                            img_path = save_figure_safely(fig, f"credit_pie_{i}.png", temp_dir)
                            if img_path:
                                pdf.add_image(img_path, w=150, caption="Répartition Capital/Intérêts du crédit")
                        except Exception as e:
                            logger.error(f"Erreur graphique crédit {i}: {e}")
                    
                # Tableau d'amortissement détaillé des immobilisations
                pdf.add_page()
                pdf.chapter_title("Tableau d'Amortissement des Immobilisations")
                
                # Vérifier si des données d'amortissement détaillées existent
                if has_data("detailed_amortization"):
                    detailed_amortization = st.session_state.detailed_amortization
                    
                    # Construire le tableau d'amortissement détaillé
                    headers = ["Immobilisation", "Montant", "Durée", "Taux", "Amort. N", "Amort. N+1", "Amort. N+2", "Total", "VNA"]
                    table_data = []
                    
                    total_amount = 0
                    total_amort_n = 0
                    total_amort_n1 = 0
                    total_amort_n2 = 0
                    
                    for item in detailed_amortization:
                        if not isinstance(item, dict):
                            continue
                        
                        amount = item.get('amount', 0)
                        duration = item.get('duration', 0)
                        rate = item.get('rate', 0)
                        amort_n = item.get('amortization_n', 0)
                        amort_n1 = item.get('amortization_n1', 0)
                        amort_n2 = item.get('amortization_n2', 0)
                        
                        total_amort = amort_n + amort_n1 + amort_n2
                        vna = amount - total_amort
                        
                        table_data.append([
                            ascii_only(item.get('name', '')),
                            f"{amount:,.2f}",
                            str(duration),
                            f"{rate}%",
                            f"{amort_n:,.2f}",
                            f"{amort_n1:,.2f}",
                            f"{amort_n2:,.2f}",
                            f"{total_amort:,.2f}",
                            f"{vna:,.2f}"
                        ])
                        
                        total_amount += amount
                        total_amort_n += amort_n
                        total_amort_n1 += amort_n1
                        total_amort_n2 += amort_n2
                    
                    total_amort_sum = total_amort_n + total_amort_n1 + total_amort_n2
                    total_vna = total_amount - total_amort_sum
                    
                    # Ajouter une ligne Total
                    table_data.append([
                        "TOTAL",
                        f"{total_amount:,.2f}",
                        "",
                        "",
                        f"{total_amort_n:,.2f}",
                        f"{total_amort_n1:,.2f}",
                        f"{total_amort_n2:,.2f}",
                        f"{total_amort_sum:,.2f}",
                        f"{total_vna:,.2f}"
                    ])
                    
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 8, ascii_only("Tableau détaillé des amortissements"), 0, 1, "L")
                    pdf.ln(5)
                    
                    # Ajuster les largeurs des colonnes pour le tableau d'amortissement
                    pdf.add_table(headers, table_data, [40, 30, 15, 15, 25, 25, 25, 25, 25])
                    
                    # Ajouter les graphiques d'amortissement
                    try:
                        # 1. Graphique de répartition des immobilisations
                        immobilisations = [item.get('name', '') for item in detailed_amortization if item.get('amount', 0) > 0]
                        amounts = [item.get('amount', 0) for item in detailed_amortization if item.get('amount', 0) > 0]
                        
                        if immobilisations and amounts:
                            fig, ax = plt.subplots(figsize=(10, 7))
                            ax.pie(
                                amounts,
                                labels=immobilisations,
                                autopct='%1.1f%%',
                                startangle=90,
                                shadow=True
                            )
                            ax.axis('equal')
                            ax.set_title('Répartition des immobilisations par montant')
                            
                            img_path = save_figure_safely(fig, "amortization_pie.png", temp_dir)
                            if img_path:
                                pdf.add_page()
                                pdf.chapter_title("Graphiques d'Analyse des Amortissements")
                                pdf.add_image(img_path, w=180, caption="Répartition des immobilisations par montant")
                                pdf.ln(5)
                        
                        # 2. Graphique d'évolution des amortissements par année
                        years = ["N", "N+1", "N+2"]
                        yearly_data = {"Année": years}
                        
                        for item in detailed_amortization:
                            if item.get('amount', 0) > 0:
                                name = item.get('name', '')
                                yearly_amort = [
                                    item.get('amortization_n', 0),
                                    item.get('amortization_n1', 0),
                                    item.get('amortization_n2', 0)
                                ]
                                yearly_data[name] = yearly_amort
                        
                        if len(yearly_data) > 1:  # Si des données existent en plus des années
                            fig, ax = plt.subplots(figsize=(12, 7))
                            
                            bar_width = 0.15
                            index = np.arange(len(years))
                            num_items = len(yearly_data) - 1  # -1 pour la clé "Année"
                            
                            # Positionner les barres correctement
                            positions = np.linspace(-(num_items-1)*bar_width/2, (num_items-1)*bar_width/2, num_items)
                            
                            i = 0
                            for name, values in yearly_data.items():
                                if name != "Année":
                                    ax.bar(index + positions[i], values, bar_width, label=name)
                                    i += 1
                            
                            ax.set_xlabel('Années')
                            ax.set_ylabel('Montant des amortissements (DHS)')
                            ax.set_title('Évolution des amortissements par immobilisation')
                            ax.set_xticks(index)
                            ax.set_xticklabels(years)
                            ax.legend()
                            
                            img_path = save_figure_safely(fig, "amortization_evolution.png", temp_dir)
                            if img_path:
                                pdf.add_image(img_path, w=180, caption="Évolution des amortissements par année")
                    except Exception as e:
                        logger.error(f"Erreur graphiques analyse amortissements: {e}")
                        pdf.chapter_body(f"Erreur graphiques analyse amortissements: {ascii_only(str(e))}")

        # Tableau de trésorerie mensuel
        if "Tableau de Trésorerie Mensuel" in sections and has_data("monthly_cashflow_data"):
            pdf.add_page()
            pdf.chapter_title("Tableau de Tresorerie Mensuel")
            
            monthly_data = st.session_state.monthly_cashflow_data
            if isinstance(monthly_data, dict):
                try:
                    # IMPORTANT: Ajout d'un tableau récapitulatif mensuel clair
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 8, ascii_only("Récapitulatif Mensuel de Trésorerie"), 0, 1, "L")
                    
                    # Définir un nombre de mois à afficher
                    num_months = 6  # Limiter pour que ça rentre dans le PDF
                    
                    # Fonction pour calcul sécurisé
                    def safe_sum(dict_obj):
                        if not isinstance(dict_obj, dict):
                            return 0
                        total = 0
                        for v in dict_obj.values():
                            try:
                                if isinstance(v, (int, float)):
                                    total += v
                                elif isinstance(v, str) and v.strip():
                                    total += float(v.replace(',', ''))
                            except:
                                pass
                        return total
                    
                    # Calculer les totaux
                    total_ressources = safe_sum(monthly_data.get("ressources", {}))
                    total_ca = safe_sum(monthly_data.get("chiffre_affaires", {}))
                    total_immos = safe_sum(monthly_data.get("immobilisations", {}))
                    total_charges = safe_sum(monthly_data.get("charges_exploitation", {}))
                    
                    monthly_balance = total_ca - total_charges
                    initial_balance = total_ressources - total_immos
                    
                    # Préparer les soldes cumulés
                    soldes = [initial_balance]
                    for i in range(num_months):
                        soldes.append(soldes[-1] + monthly_balance)
                    
                    # Structure des données pour le tableau
                    headers = ["Éléments"] + [f"Mois {i+1}" for i in range(num_months)]
                    table_data = []
                    
                    # Organiser les données par section
                    sections_data = {
                        "Ressources": monthly_data.get("ressources", {}),
                        "Chiffre d'affaires": monthly_data.get("chiffre_affaires", {}),
                        "Immobilisations": monthly_data.get("immobilisations", {}),
                        "Charges d'exploitation": monthly_data.get("charges_exploitation", {})
                    }
                    
                    for section_title, section_data in sections_data.items():
                        if not section_data:
                            continue
                            
                        pdf.set_font("Arial", "B", 10)
                        pdf.cell(0, 8, ascii_only(section_title), 0, 1, "L")
                        
                        table_data = []
                        for key, value in section_data.items():
                            try:
                                value_float = float(value) if isinstance(value, (int, float, str)) else 0
                            except (ValueError, TypeError):
                                value_float = 0
                            
                            # Pour les ressources et immobilisations, une seule fois au mois 1
                            if section_title in ["Ressources", "Immobilisations"]:
                                row = [key, f"{value_float:,.2f}"] + [""] * (num_months-1)
                            else:
                                # Pour charges et CA, répété chaque mois
                                row = [key] + [f"{value_float:,.2f}"] * num_months
                                
                            table_data.append(row)
                        
                        # Ajouter le total de la section
                        total_section = safe_sum(section_data)
                        if section_title in ["Ressources", "Immobilisations"]:
                            row = ["TOTAL " + section_title, f"{total_section:,.2f}"] + [""] * (num_months-1)
                        else:
                            row = ["TOTAL " + section_title] + [f"{total_section:,.2f}"] * num_months
                        
                        table_data.append(row)
                        
                        # Ajouter le tableau au PDF
                        section_headers = ["Élément"] + [f"Mois {i+1}" for i in range(num_months)]
                        
                        # Calculer les largeurs des colonnes
                        col_widths = [60]  # Première colonne plus large
                        remaining_width = 120  # Largeur restante pour les colonnes des mois
                        month_width = remaining_width / num_months
                        col_widths.extend([month_width] * num_months)
                        
                        pdf.add_table(section_headers, table_data, col_widths)
                        pdf.ln(5)
                    
                    # Tableau de synthèse des soldes
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 8, ascii_only("Synthèse des Soldes Mensuels"), 0, 1, "L")
                    
                    summary_data = [
                        ["Solde initial", f"{initial_balance:,.2f}", "", "", "", "", ""],
                        ["Recettes mensuelles", f"{total_ca:,.2f}", f"{total_ca:,.2f}", f"{total_ca:,.2f}", f"{total_ca:,.2f}", f"{total_ca:,.2f}", f"{total_ca:,.2f}"],
                        ["Dépenses mensuelles", f"{total_charges:,.2f}", f"{total_charges:,.2f}", f"{total_charges:,.2f}", f"{total_charges:,.2f}", f"{total_charges:,.2f}", f"{total_charges:,.2f}"],
                        ["Balance mensuelle", f"{monthly_balance:,.2f}", f"{monthly_balance:,.2f}", f"{monthly_balance:,.2f}", f"{monthly_balance:,.2f}", f"{monthly_balance:,.2f}", f"{monthly_balance:,.2f}"],
                        ["Solde cumulé", f"{soldes[1]:,.2f}", f"{soldes[2]:,.2f}", f"{soldes[3]:,.2f}", f"{soldes[4]:,.2f}", f"{soldes[5]:,.2f}", f"{soldes[6]:,.2f}"]
                    ]
                    
                    pdf.add_table(["Élément"] + [f"Mois {i+1}" for i in range(num_months)], summary_data, col_widths)
                    
                    # Ajouter un graphique d'évolution du solde
                    try:
                        fig, ax = plt.subplots(figsize=(12, 7))
                        months = range(1, num_months+1)
                        ax.plot(months, soldes[1:num_months+1], marker='o', linewidth=2, markersize=8)
                        
                        # Ajouter une ligne à zéro pour référence
                        ax.axhline(y=0, color='r', linestyle='--', alpha=0.3)
                        
                        # Ajouter des annotations pour les valeurs
                        for i, bal in enumerate(soldes[1:num_months+1]):
                            ax.annotate(f'{bal:,.0f}', 
                                       xy=(i+1, bal), 
                                       xytext=(0, 10 if bal >= 0 else -15),
                                       textcoords="offset points",
                                       ha='center')
                        
                        ax.set_title('Évolution du solde de trésorerie sur 6 mois')
                        ax.set_xlabel('Mois')
                        ax.set_ylabel('Solde (DHS)')
                        ax.grid(True, alpha=0.3)
                        
                        img_path = save_figure_safely(fig, "monthly_treasury_evolution.png", temp_dir)
                        if img_path:
                            pdf.ln(10)
                            pdf.add_image(img_path, w=180, caption="Évolution du solde de trésorerie sur 6 mois")
                    except Exception as e:
                        logger.error(f"Erreur graphique évolution trésorerie: {e}")
                        pdf.chapter_body(f"Erreur graphique évolution trésorerie: {ascii_only(str(e))}")
                        
                except Exception as e:
                    logger.error(f"Erreur tableau trésorerie mensuelle: {e}")
                    pdf.chapter_body(f"Erreur lors de la génération du tableau de trésorerie mensuelle: {ascii_only(str(e))}")
            
        # Budget TVA
        if "Budget TVA" in sections and has_data("vat_budget_data"):
            pdf.add_page()
            pdf.chapter_title("Budget TVA")
            
            vat_data = st.session_state.vat_budget_data
            if isinstance(vat_data, dict):
                try:
                    # IMPORTANT: Ajout d'un tableau récapitulatif TVA clair
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 8, ascii_only("Récapitulatif du Budget TVA"), 0, 1, "L")
                    
                    # Taux de TVA (valeur par défaut 20%)
                    tva_rate = 20
                    if "tva_rate" in st.session_state:
                        try:
                            tva_rate = float(st.session_state.tva_rate)
                        except (ValueError, TypeError):
                            pass
                    
                    # Fonction pour calcul sécurisé des montants TVA
                    def safe_sum_tva(dict_obj, key_filter=None):
                        if not isinstance(dict_obj, dict):
                            return 0
                        total = 0
                        for k, v in dict_obj.items():
                            if key_filter and key_filter not in k.lower():
                                continue
                            try:
                                if isinstance(v, (int, float)):
                                    total += v
                                elif isinstance(v, str) and v.strip():
                                    total += float(v.replace(',', ''))
                            except:
                                pass
                        return total
                    
                    # Calculer les totaux
                    achats_ht = safe_sum_tva(vat_data.get("achats", {}), "ht")
                    tva_deduct_achats = safe_sum_tva(vat_data.get("achats", {}), "tva")
                    ventes_ht = safe_sum_tva(vat_data.get("ventes", {}), "ht")
                    tva_collect_ventes = safe_sum_tva(vat_data.get("ventes", {}), "tva")
                    tva_deduct_immos = safe_sum_tva(vat_data.get("tva_immobilisations", {}))
                    
                    # Si pas de TVA déductible sur achats mais montant HT disponible
                    if tva_deduct_achats == 0 and achats_ht > 0:
                        tva_deduct_achats = achats_ht * (tva_rate / 100)
                    
                    # Si pas de TVA collectée sur ventes mais montant HT disponible
                    if tva_collect_ventes == 0 and ventes_ht > 0:
                        tva_collect_ventes = ventes_ht * (tva_rate / 100)
                    
                    # Calculer la TVA nette à payer
                    tva_nette = tva_collect_ventes - tva_deduct_achats - tva_deduct_immos
                    
                    # Tableau d'achats
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 8, ascii_only("1. Achats et TVA déductible"), 0, 1, "L")
                    
                    achats_headers = ["Élément", "Montant HT (DHS)", "TVA déductible (DHS)"]
                    achats_data = []
                    
                    for key, value in vat_data.get("achats", {}).items():
                        if "tva" in key.lower():
                            continue  # Skip TVA entries, they'll be calculated
                            
                        try:
                            montant_ht = float(value) if isinstance(value, (int, float, str)) else 0
                        except (ValueError, TypeError):
                            montant_ht = 0
                            
                        montant_tva = montant_ht * (tva_rate / 100)
                        
                        achats_data.append([
                            key,
                            f"{montant_ht:,.2f}",
                            f"{montant_tva:,.2f}"
                        ])
                    
                    # Ajouter le total
                    achats_data.append([
                        "TOTAL",
                        f"{achats_ht:,.2f}",
                        f"{tva_deduct_achats:,.2f}"
                    ])
                    
                    pdf.add_table(achats_headers, achats_data, [80, 50, 50])
                    pdf.ln(5)
                    
                    # Tableau de ventes
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 8, ascii_only("2. Ventes et TVA collectée"), 0, 1, "L")
                    
                    ventes_headers = ["Élément", "Montant HT (DHS)", "TVA collectée (DHS)"]
                    ventes_data = []
                    
                    for key, value in vat_data.get("ventes", {}).items():
                        if "tva" in key.lower():
                            continue  # Skip TVA entries, they'll be calculated
                            
                        try:
                            montant_ht = float(value) if isinstance(value, (int, float, str)) else 0
                        except (ValueError, TypeError):
                            montant_ht = 0
                            
                        montant_tva = montant_ht * (tva_rate / 100)
                        
                        ventes_data.append([
                            key,
                            f"{montant_ht:,.2f}",
                            f"{montant_tva:,.2f}"
                        ])
                    
                    # Ajouter le total
                    ventes_data.append([
                        "TOTAL",
                        f"{ventes_ht:,.2f}",
                        f"{tva_collect_ventes:,.2f}"
                    ])
                    
                    pdf.add_table(ventes_headers, ventes_data, [80, 50, 50])
                    pdf.ln(5)
                    
                    # Tableau de TVA déductible sur immobilisations
                    if vat_data.get("tva_immobilisations", {}):
                        pdf.set_font("Arial", "B", 10)
                        pdf.cell(0, 8, ascii_only("3. TVA déductible sur immobilisations"), 0, 1, "L")
                        
                        immo_tva_headers = ["Immobilisation", "TVA déductible (DHS)"]
                        immo_tva_data = []
                        
                        for key, value in vat_data.get("tva_immobilisations", {}).items():
                            try:
                                montant_tva = float(value) if isinstance(value, (int, float, str)) else 0
                            except (ValueError, TypeError):
                                montant_tva = 0
                                
                            immo_tva_data.append([
                                key,
                                f"{montant_tva:,.2f}"
                            ])
                        
                        # Ajouter le total
                        immo_tva_data.append([
                            "TOTAL",
                            f"{tva_deduct_immos:,.2f}"
                        ])
                        
                        pdf.add_table(immo_tva_headers, immo_tva_data, [130, 50])
                        pdf.ln(5)
                    
                    # Récapitulatif de la TVA
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 8, ascii_only("4. Récapitulatif de la TVA"), 0, 1, "L")
                    
                    recap_headers = ["Élément", "Montant (DHS)"]
                    recap_data = [
                        ["TVA collectée sur ventes", f"{tva_collect_ventes:,.2f}"],
                        ["TVA déductible sur achats", f"{tva_deduct_achats:,.2f}"],
                        ["TVA déductible sur immobilisations", f"{tva_deduct_immos:,.2f}"],
                        ["TVA nette à payer", f"{tva_nette:,.2f}"]
                    ]
                    
                    pdf.add_table(recap_headers, recap_data, [130, 50])
                    
                    # Ajouter un graphique de répartition de la TVA
                    try:
                        fig, ax = plt.subplots(figsize=(10, 7))
                        
                        labels = ['TVA collectée', 'TVA déductible achats', 'TVA déductible immos']
                        values = [tva_collect_ventes, tva_deduct_achats, tva_deduct_immos]
                        colors = ['#ff9999', '#66b3ff', '#99ff99']
                        
                        ax.bar(labels, values, color=colors)
                        ax.set_ylabel('Montant (DHS)')
                        ax.set_title('Composantes de la TVA')
                        
                        # Ajouter les valeurs sur les barres
                        for i, v in enumerate(values):
                            ax.text(i, v/2, f"{v:,.0f}", ha='center')
                        
                        img_path = save_figure_safely(fig, "tva_components.png", temp_dir)
                        if img_path:
                            pdf.ln(10)
                            pdf.add_image(img_path, w=180, caption="Composantes de la TVA")
                            
                        # Graphique de la TVA nette
                        fig, ax = plt.subplots(figsize=(10, 7))
                        
                        ax.bar(['TVA nette à payer'], [tva_nette], 
                               color='#ff9999' if tva_nette > 0 else '#99ff99')
                        ax.set_ylabel('Montant (DHS)')
                        ax.set_title('TVA nette à payer')
                        
                        # Ajouter les valeurs sur les barres
                        ax.text(0, tva_nette/2, f"{tva_nette:,.0f}", ha='center')
                        
                        img_path = save_figure_safely(fig, "tva_nette.png", temp_dir)
                        if img_path:
                            pdf.ln(10)
                            pdf.add_image(img_path, w=150, caption="TVA nette à payer")
                            
                    except Exception as e:
                        logger.error(f"Erreur graphique TVA: {e}")
                        pdf.chapter_body(f"Erreur graphique TVA: {ascii_only(str(e))}")
                        
                except Exception as e:
                    logger.error(f"Erreur budget TVA: {e}")
                    pdf.chapter_body(f"Erreur lors de la génération du budget TVA: {ascii_only(str(e))}")
        
        # Annexe avec tous les graphiques générés
        pdf.add_page()
        pdf.chapter_title("Annexe: Graphiques Supplementaires")
        
        # Capturer tous les graphiques générés dans l'application
        all_graphs = []
        try:
            # Générer des graphiques additionnels
            generated_charts = generate_additional_charts()
            if generated_charts:
                all_graphs.extend(generated_charts)
                
            # Capturer graphiques Plotly
            plotly_graphs = capture_plotly_figures()
            if plotly_graphs:
                all_graphs.extend(plotly_graphs)
                
            # Capturer graphiques Matplotlib
            matplotlib_graphs = capture_matplotlib_figures()
            if matplotlib_graphs:
                all_graphs.extend(matplotlib_graphs)
                
            # Capturer autres graphiques en session
            session_graphs = capture_all_graphs_in_session()
            if session_graphs:
                all_graphs.extend(session_graphs)
                
            # Capturer les images Streamlit
            streamlit_images = capture_streamlit_images()
            if streamlit_images:
                all_graphs.extend(streamlit_images)
                
            # Limiter à un nombre raisonnable de graphiques
            if all_graphs:
                included_graphs = all_graphs[:10]  # Maximum 10 graphiques supplémentaires
                
                pdf.set_font("Arial", "", 10)
                pdf.multi_cell(0, 5, f"Cette annexe contient {len(included_graphs)} graphiques supplémentaires générés pour ce rapport.")
                pdf.ln(5)
                
                for i, graph in enumerate(included_graphs):
                    try:
                        if i > 0 and i % 2 == 0:
                            pdf.add_page()
                        
                        pdf.set_font("Arial", "B", 10)
                        pdf.cell(0, 8, ascii_only(f"Graphique {i+1}: {graph.get('name', 'Sans titre')}"), 0, 1, "L")
                        pdf.add_image(graph['path'], w=170, caption="")
                        pdf.ln(10)
                    except Exception as e:
                        logger.error(f"Erreur lors de l'ajout du graphique {i}: {e}")
                        continue
            else:
                pdf.set_font("Arial", "", 10)
                pdf.multi_cell(0, 5, "Aucun graphique supplémentaire n'a été trouvé.")
        except Exception as e:
            logger.error(f"Erreur lors de la génération des graphiques supplémentaires: {e}")
            pdf.chapter_body(f"Erreur lors de la génération des graphiques supplémentaires: {ascii_only(str(e))}")
        
        # Finir le PDF
        output_file = f"{temp_dir}/financial_report.pdf"
        pdf.output(output_file)
        
        logger.info(f"PDF généré avec succès: {output_file}")
        return output_file
            
    except Exception as e:
        logger.error(f"Erreur fatale lors de la génération du PDF: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Créer un PDF d'erreur
        error_pdf = PDF()
        error_pdf.add_page()
        error_pdf.set_font("Arial", "B", 14)
        error_pdf.cell(0, 10, "Erreur lors de la génération du rapport", 0, 1, "C")
        error_pdf.set_font("Arial", "", 10)
        
        import traceback
        error_details = f"""
Une erreur est survenue lors de la génération du rapport PDF.

Type d'erreur: {type(e).__name__}
Message d'erreur: {str(e)}

Détails techniques:
{traceback.format_exc()}

Contactez le support technique avec ces informations pour résoudre le problème.
        """
        
        error_pdf.multi_cell(0, 5, ascii_only(error_details))
        
        output_file = f"{temp_dir}/error_report.pdf"
        error_pdf.output(output_file)
        return output_file
    
def add_export_sidebar_widgets():
    """
    Ajoute les widgets pour la sauvegarde et l'export dans la sidebar
    """
    st.sidebar.write("---")
    st.sidebar.write("#### 💾 Sauvegarde & Export")
    
    # Section de sauvegarde des données
    with st.sidebar.expander("Sauvegarde des données", expanded=False):
        st.caption("Sauvegardez ou restaurez l'état actuel de votre projet")
        
        # Bouton pour sauvegarder les données
        if st.button("💾 Sauvegarder", key="save_data_btn"):
            try:
                save_data()
            except Exception as e:
                st.error(f"Erreur: {str(e)}")
        
        # Bouton pour télécharger les données
        try:
            data_json = get_session_data_as_json()
            company_name = st.session_state.basic_info.get('company_name', 'entreprise')
            
            st.download_button(
                label="⬇️ Télécharger (JSON)",
                data=data_json,
                file_name=f"{company_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                key="download_json_btn"
            )
        except Exception as e:
            st.error(f"Erreur de préparation des données: {str(e)}")
        
        # Option pour charger des données sauvegardées
        uploaded_file = st.file_uploader("Charger une sauvegarde", type=['json'], key="json_uploader")
        if uploaded_file is not None:
            try:
                load_data_from_json(uploaded_file)
                st.success("✅ Données chargées avec succès!")
                if st.button("Actualiser l'affichage", key="refresh_after_load"):
                    st.rerun()
            except Exception as e:
                st.error(f"Erreur: {str(e)}")
    
    # Section de génération de rapport PDF
    with st.sidebar.expander("Génération de rapport PDF", expanded=False):
        st.caption("Créez un rapport PDF complet de votre projet")
        
        # Options du rapport
        company_name = st.session_state.basic_info.get('company_name', 'Entreprise')
        report_name = st.text_input(
            "Nom du rapport", 
            value=f"Étude Financière - {company_name}",
            key="pdf_report_name"
        )
        
        include_sections = st.multiselect(
            "Sections à inclure",
            options=["Informations générales", "Investissements", "Bilan prévisionnel", 
                    "Compte de résultat", "Trésorerie", "Analyse TVA", "Amortissements"],
            default=["Informations générales", "Investissements", "Bilan prévisionnel", 
                    "Compte de résultat", "Trésorerie"],
            key="pdf_sections"
        )
        
        # Génération du PDF
        if st.button("🖨️ Générer le PDF", key="generate_pdf_btn"):
            with st.spinner("Génération du rapport en cours..."):
                try:
                    pdf_file = generate_pdf_report(report_name, include_sections)
                    st.success("✅ Rapport PDF généré avec succès!")
                    
                    # Téléchargement du PDF
                    with open(pdf_file, "rb") as f:
                        pdf_bytes = f.read()
                    
                    st.download_button(
                        label="⬇️ Télécharger le PDF",
                        data=pdf_bytes,
                        file_name=f"{report_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        key="download_pdf_btn"
                    )
                except Exception as e:
                    st.error(f"Erreur lors de la génération du PDF: {str(e)}")

# ========== INITIALISATION DES VARIABLES DE SESSION ==========
def init_session_state():
    # Données d'entreprise
    if 'basic_info' not in st.session_state:
        st.session_state.basic_info = {
            'company_name': 'CLICLINC',
            'company_type': 'SARL',
            'creation_date': datetime(2024, 6, 1),
            'closing_date': '31 DECEMBRE',
            'sector': 'COMMERCE ; RÉPARATION D\'AUTOMOBILES ET DE MOTOCYCLES',
            'tax_id': '',
            'partners': 1,
            'address': '',
            'phone': '',
            'email': ''
        }
    
    # Investissements
    if 'investment_data' not in st.session_state:
        st.session_state.investment_data = {
            'brand_registration': 1700.0,
            'sarl_formation': 4000.0,
            'web_dev': 80000.0,
            'cash_contribution': 50511.31,
            'in_kind': 20000.0
        }
    
    # Immobilisations
    if 'immos' not in st.session_state:
        st.session_state.immos = []
    
    # Crédits
    if 'credits' not in st.session_state:
        st.session_state.credits = []
    
    # Subventions
    if 'subsidies' not in st.session_state:
        st.session_state.subsidies = []
    
    # Frais préliminaires
    if 'frais_preliminaires' not in st.session_state:
        st.session_state.frais_preliminaires = [
            {"nom": "Enregistrement de marque", "valeur": 1700.0},
            {"nom": "Frais de constitution", "valeur": 4000.0}
        ]
    
    # Paramètres du compte de résultat
    if 'income_statement_params' not in st.session_state:
        st.session_state.income_statement_params = {
            'growth_n': 0.20,
            'growth_n1': 0.20,
            'base_ca': 150000.0,
            'cost_ratio': 0.8,
            'efficiency_improvement': 0.02
        }
    
    # Paramètres du cash flow
    if 'cash_flow_params' not in st.session_state:
        st.session_state.cash_flow_params = {
            'taux_actualisation': 0.03,
            'annees_projection': 3
        }
    
    # Bilan - Actif
    if 'actif_data' not in st.session_state:
        st.session_state.actif_data = {
            'immobilisations_non_valeur': [
                {'label': "Frais préliminaires", 'value': 5700.0},
                {'label': "Charges à répartir", 'value': 0.0},
                {'label': "Primes de remboursement", 'value': 0.0}
            ],
            'immobilisations_incorporelles': [
                {'label': "Recherche & développement", 'value': 0.0},
                {'label': "Brevets, marques", 'value': 0.0},
                {'label': "Fonds commercial", 'value': 80000.0}
            ],
            'immobilisations_corporelles': [
                {'label': "Terrains", 'value': 3500.0},
                {'label': "Constructions", 'value': 94080.0},
                {'label': "Installations techniques", 'value': 14400.0},
                {'label': "Matériel de transport", 'value': 0.0},
                {'label': "Mobilier, bureau", 'value': 0.0},
                {'label': "Autres immobilisations", 'value': 0.0}
            ],
            'stocks': [
                {'label': "Marchandises", 'value': 0.0},
                {'label': "Matières premières", 'value': 0.0}
            ],
            'tresorerie_actif': [
                {'label': "Banque, chèques postaux", 'value': 0.0},
                {'label': "Caisse, avances", 'value': 0.0}
            ]
        }
    
    # Bilan - Passif
    if 'passif_data' not in st.session_state:
        st.session_state.passif_data = {
            'capitaux_propres': [
                {'label': "Capital social", 'value': 70511.31},
                {'label': "Capitaux propres assimilés", 'value': 0.0},
                {'label': "Subvention d'investissement", 'value': 0.0}
            ],
            'dettes_financement': [
                {'label': "Emprunts obligataires", 'value': 0.0},
                {'label': "Autres dettes de financement", 'value': 0.0}
            ],
            'passif_circulant': [
                {'label': "Fournisseurs et comptes rattachés", 'value': 0.0},
                {'label': "Ecart de conversion", 'value': 0.0},
                {'label': "Autres provisions", 'value': 0.0}
            ],
            'tresorerie_passif': [
                {'label': "Banque (solde créditeur)", 'value': 0.0}
            ]
        }
    
    # Données de trésorerie mensuelle
    if 'monthly_cashflow_data' not in st.session_state:
        st.session_state.monthly_cashflow_data = {
            'ressources': {
                'Apports personnels': 70511.31,
                'Emprunts': 134000.00,
                'Subventions': 90000.00
            },
            'chiffre_affaires': {
                'Ventes de produits & service au Maroc': 45004.71
            },
            'immobilisations': {
                'Immobilisations incorporelles': 86840.00,
                'Immobilisations corporelles': 96300.00
            },
            'charges_exploitation': {
                'Achat de matières premières (charges variables)': 0.00,
                'Echéances d\'emprunt': 1849.30,
                'Impôts et taxes': 7760.94,
                'Charges externes': 6200.00,
                'Salaires et charges sociales': 25946.22,
                'Frais bancaires et charges financières': 80.00
            }
        }
    
    # Budget TVA
    if 'vat_budget_data' not in st.session_state:
        st.session_state.vat_budget_data = {
            'achats': {
                'Achat HT': 6200.00,
                'TVA déductible sur achat': 1240.00
            },
            'ventes': {
                'Vente en HT': 45004.71,
                'TVA collecte sur vente': 9000.94
            },
            'tva_immobilisations': {
                'TVA dedustible sur immobilisation': 36628.00
            }
        }
    
    # Tableau d'amortissement détaillé des immobilisations
    if 'detailed_amortization' not in st.session_state:
        st.session_state.detailed_amortization = [
            {
                'name': "Frais préliminaire & d'approche",
                'amount': 5700.00,
                'duration': 5,
                'rate': 20,
                'amortization_n': 1140.00,
                'amortization_n1': 1140.00,
                'amortization_n2': 1140.00
            },
            {
                'name': "Terrain / Local",
                'amount': 0.00,
                'duration': 10,
                'rate': 10,
                'amortization_n': 0.00,
                'amortization_n1': 0.00,
                'amortization_n2': 0.00
            },
            {
                'name': "Construction / Aménagement",
                'amount': 3500.00,
                'duration': 5,
                'rate': 10,
                'amortization_n': 700.00,
                'amortization_n1': 700.00,
                'amortization_n2': 700.00
            },
            {
                'name': "Matériel d'équipement",
                'amount': 78400.00,
                'duration': 5,
                'rate': 20,
                'amortization_n': 15680.00,
                'amortization_n1': 15680.00,
                'amortization_n2': 15680.00
            },
            {
                'name': "Mobilier & matériel de bureau",
                'amount': 12000.00,
                'duration': 5,
                'rate': 20,
                'amortization_n': 2400.00,
                'amortization_n1': 2400.00,
                'amortization_n2': 2400.00
            },
            {
                'name': "Matériel de transport & manutension",
                'amount': 0.00,
                'duration': 5,
                'rate': 20,
                'amortization_n': 0.00,
                'amortization_n1': 0.00,
                'amortization_n2': 0.00
            },
            {
                'name': "Système d'information",
                'amount': 80000.00,
                'duration': 5,
                'rate': 20,
                'amortization_n': 16000.00,
                'amortization_n1': 16000.00,
                'amortization_n2': 16000.00
            }
        ]
    
    # Données calculées (partagées entre modules)
    if 'calculated_data' not in st.session_state:
        st.session_state.calculated_data = {}
    
    # Données du compte de résultat
    if 'income_statement' not in st.session_state:
        st.session_state.income_statement = {}


# Fonction pour calculer les métriques financières
def calculate_financial_metrics(df):
    """
    Calcule des métriques financières avancées à partir du DataFrame d'importation
    """
    metrics = {}
    
    # Calculer les montants totaux par catégorie
    total_immobilisations = df[df['type'] == 'immobilisation']['montant'].sum()
    total_financements = df[df['type'] == 'financement']['montant'].sum()
    total_charges_mensuelles = df[df['type'] == 'charges']['montant'].sum()
    total_ventes_mensuelles = df[df['type'] == 'ventes']['montant'].sum()
    
    metrics['total_immobilisations'] = total_immobilisations
    metrics['total_financements'] = total_financements
    metrics['total_charges'] = total_charges_mensuelles
    metrics['total_ventes'] = total_ventes_mensuelles
    
    # Calcul du flux de trésorerie mensuel
    metrics['cash_flow_mensuel'] = total_ventes_mensuelles - total_charges_mensuelles
    
    # Calcul du ROI (Retour sur investissement) si les données sont disponibles
    if total_immobilisations > 0:
        roi_mensuel = metrics['cash_flow_mensuel'] / total_immobilisations
        metrics['roi_mensuel'] = roi_mensuel
        metrics['roi_annuel'] = roi_mensuel * 12
        
        # Calcul du délai de récupération de l'investissement (Payback period)
        if metrics['cash_flow_mensuel'] > 0:
            metrics['payback_months'] = total_immobilisations / metrics['cash_flow_mensuel']
            metrics['payback_years'] = metrics['payback_months'] / 12
        else:
            metrics['payback_months'] = float('inf')
            metrics['payback_years'] = float('inf')
    else:
        metrics['roi_mensuel'] = 0
        metrics['roi_annuel'] = 0
        metrics['payback_months'] = 0
        metrics['payback_years'] = 0
    
    # Calcul de la VAN (Valeur Actuelle Nette) sur 5 ans avec un taux d'actualisation de 8%
    if PYFINANCE_AVAILABLE:
        try:
            if metrics['cash_flow_mensuel'] > 0:
                # Créer un flux de trésorerie sur 60 mois (5 ans)
                cash_flows = [-total_immobilisations] + [metrics['cash_flow_mensuel']] * 60
                
                # Taux d'actualisation mensuel (8% annuel)
                monthly_rate = 0.08 / 12
                
                # Calculer la VAN
                metrics['van'] = pf.npv(rate=monthly_rate, values=cash_flows)
                
                # Calculer le TRI
                try:
                    metrics['tri'] = pf.irr(values=cash_flows) * 12  # Convertir le TRI mensuel en annuel
                except:
                    metrics['tri'] = None
            else:
                metrics['van'] = -total_immobilisations
                metrics['tri'] = None
        except:
            metrics['van'] = None
            metrics['tri'] = None
    else:
        # Version simplifiée de calcul si PyFinance n'est pas disponible
        if metrics['cash_flow_mensuel'] > 0:
            # Calcul simplifié de la VAN sur 5 ans
            van = -total_immobilisations
            monthly_rate = 0.08 / 12
            
            for i in range(60):
                van += metrics['cash_flow_mensuel'] / ((1 + monthly_rate) ** (i + 1))
            
            metrics['van'] = van
            metrics['tri'] = None  # TRI indisponible sans PyFinance
        else:
            metrics['van'] = -total_immobilisations
            metrics['tri'] = None
    
    # Calculer l'amortissement total annuel
    annual_amort = 0
    for _, immo in df[df['type'] == 'immobilisation'].iterrows():
        if immo['duree_amort'] > 0:
            annual_amort += immo['montant'] * (immo['taux_amort'] / 100)
    
    metrics['amortissement_annuel'] = annual_amort
    
    # Calculer la TVA
    try:
        # TVA sur ventes
        tva_collectee = df[df['type'] == 'ventes'].apply(lambda x: x['montant'] * (x['taux_tva']/100), axis=1).sum()
        
        # TVA sur achats
        tva_deductible_achats = df[df['type'] == 'charges'].apply(lambda x: x['montant'] * (x['taux_tva']/100), axis=1).sum()
        
        # TVA sur immobilisations
        tva_deductible_immo = df[df['type'] == 'immobilisation'].apply(lambda x: x['montant'] * (x['taux_tva']/100), axis=1).sum()
        
        metrics['tva_collectee'] = tva_collectee
        metrics['tva_deductible_achats'] = tva_deductible_achats
        metrics['tva_deductible_immo'] = tva_deductible_immo
        metrics['tva_nette'] = tva_collectee - tva_deductible_achats - tva_deductible_immo
    except:
        metrics['tva_collectee'] = 0
        metrics['tva_deductible_achats'] = 0
        metrics['tva_deductible_immo'] = 0
        metrics['tva_nette'] = 0
    
    return metrics


# Fonction pour traiter le fichier CSV avec une IA simplifiée
def process_with_ai(df):
    """
    Fonction d'analyse qui traite automatiquement les données importées
    et les structure dans le bon format
    """
    # Vérifier si le dataframe est vide
    if df.empty:
        return None, "Le fichier CSV est vide.", {}
    
    # Initialiser le message de traitement
    processing_log = []
    
    # Compter les lignes avant traitement
    initial_rows = len(df)
    processing_log.append(f"Fichier importé avec {initial_rows} entrées.")
    
    # Liste des colonnes attendues
    expected_columns = ['type', 'categorie', 'nom', 'montant', 'taux_tva', 'duree_amort', 'taux_amort', 'date']
    
    # Vérifier si toutes les colonnes attendues sont présentes
    missing_columns = [col for col in expected_columns if col not in df.columns]
    
    # Si des colonnes sont manquantes, tenter de déduire les colonnes à partir des données
    if missing_columns:
        processing_log.append(f"Colonnes manquantes détectées: {', '.join(missing_columns)}")
        processing_log.append("Tentative de déduction des colonnes à partir des données...")
        
        # Copier le dataframe pour le retraiter
        new_df = pd.DataFrame(columns=expected_columns)
        
        # Essayer de correspondre les colonnes existantes avec les attendues
        column_mapping = {}
        for col in df.columns:
            # Essayer de deviner la colonne en fonction du nom ou du contenu
            col_lower = col.lower()
            
            if any(x in col_lower for x in ['type', 'catégorie', 'élément']):
                column_mapping[col] = 'type'
            elif any(x in col_lower for x in ['catégorie', 'cat', 'groupe']):
                column_mapping[col] = 'categorie'
            elif any(x in col_lower for x in ['nom', 'designation', 'libellé', 'description']):
                column_mapping[col] = 'nom'
            elif any(x in col_lower for x in ['montant', 'valeur', 'prix', 'somme', 'coût']):
                column_mapping[col] = 'montant'
            elif any(x in col_lower for x in ['tva', 'taxe']):
                column_mapping[col] = 'taux_tva'
            elif any(x in col_lower for x in ['durée', 'duree', 'période', 'periode', 'années']):
                column_mapping[col] = 'duree_amort'
            elif any(x in col_lower for x in ['amort', 'pourcentage', 'taux']):
                column_mapping[col] = 'taux_amort'
            elif any(x in col_lower for x in ['date', 'jour']):
                column_mapping[col] = 'date'
        
        # Appliquer la correspondance
        for old_col, new_col in column_mapping.items():
            new_df[new_col] = df[old_col]
        
        # Si certaines colonnes sont toujours manquantes, les créer avec des valeurs par défaut
        for col in expected_columns:
            if col not in new_df.columns:
                if col == 'type':
                    # Essayer de déduire le type à partir des autres colonnes
                    new_df[col] = 'autre'
                    if 'categorie' in new_df.columns:
                        cat_to_type = {
                            'equipement': 'immobilisation',
                            'transport': 'immobilisation',
                            'terrain': 'immobilisation',
                            'bureau': 'immobilisation',
                            'informatique': 'immobilisation',
                            'apport': 'financement',
                            'emprunt': 'financement',
                            'subvention': 'financement',
                            'loyer': 'charges',
                            'personnel': 'charges',
                            'services': 'charges',
                            'produit': 'ventes',
                            'service': 'ventes'
                        }
                        new_df[col] = new_df['categorie'].map(lambda x: next((v for k, v in cat_to_type.items() if k in str(x).lower()), 'autre'))
                elif col == 'categorie':
                    new_df[col] = 'autre'
                elif col == 'taux_tva':
                    new_df[col] = 20.0
                elif col in ['duree_amort', 'taux_amort']:
                    new_df[col] = 0.0
                    if 'type' in new_df.columns:
                        # Si c'est une immobilisation, mettre des valeurs par défaut d'amortissement
                        is_immo = new_df['type'] == 'immobilisation'
                        new_df.loc[is_immo, 'duree_amort'] = 5.0
                        new_df.loc[is_immo, 'taux_amort'] = 20.0
                elif col == 'date':
                    new_df[col] = datetime.now().strftime('%Y-%m-%d')
        
        df = new_df
        processing_log.append("Colonnes déduites et valeurs par défaut appliquées.")
    
    # Convertir les colonnes numériques
    for col in ['montant', 'taux_tva', 'duree_amort', 'taux_amort']:
        if col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # Remplacer les NaN par 0
                df[col].fillna(0, inplace=True)
                processing_log.append(f"Colonne {col} convertie en format numérique.")
            except:
                processing_log.append(f"Erreur lors de la conversion de la colonne {col} en format numérique.")
    
    # Convertir la colonne date en format date
    if 'date' in df.columns:
        try:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            # Remplacer les NaN par la date actuelle
            df['date'].fillna(pd.Timestamp.now(), inplace=True)
            processing_log.append("Colonne date convertie en format date.")
        except:
            processing_log.append("Erreur lors de la conversion de la colonne date.")
    
    # Dernières vérifications et nettoyages
    df = df.drop_duplicates()
    
    # Calcul des métriques financières
    metrics = calculate_financial_metrics(df)
    processing_log.append("Métriques financières calculées.")
    
    # Calculer le nombre de lignes après traitement
    final_rows = len(df)
    processing_log.append(f"Traitement terminé: {final_rows} entrées valides.")
    
    return df, "\n".join(processing_log), metrics


# Fonction pour afficher la page d'importation CSV
def show_csv_import():
    st.header("📤 Importation et Analyse des Données Financières")
    
    with st.expander("ℹ️ Guide d'importation", expanded=True):
        st.markdown("""
        ### Format du fichier CSV
        
        Le fichier CSV doit contenir les colonnes suivantes:
        - `type`: Type d'élément (immobilisation, financement, charges, ventes)
        - `categorie`: Sous-catégorie (equipement, transport, apport, etc.)
        - `nom`: Nom ou description de l'élément
        - `montant`: Montant en DHS
        - `taux_tva`: Taux de TVA applicable (%)
        - `duree_amort`: Durée d'amortissement (années) - pour les immobilisations
        - `taux_amort`: Taux d'amortissement (%) - pour les immobilisations
        - `date`: Date d'acquisition ou de transaction
        
        ### Comment importer
        
        1. Téléchargez le modèle de fichier CSV ci-dessous
        2. Complétez-le avec vos données
        3. Glissez-déposez le fichier dans la zone prévue
        4. Le système analysera automatiquement vos données
        5. Vérifiez les résultats et appliquez-les à votre projet
        """)
        
        # Modèle CSV à télécharger
        csv_template = """type,categorie,nom,montant,taux_tva,duree_amort,taux_amort,date
immobilisation,equipement,Matériel d'équipement,78400.00,20,5,20,2023-01-15
immobilisation,transport,Matériel de transport,45000.00,20,5,20,2023-02-10
immobilisation,terrain,Terrain / Local,120000.00,20,10,10,2023-01-01
financement,apport,Apport personnel,50000.00,0,0,0,2023-01-01
financement,emprunt,Crédit bancaire,150000.00,0,0,0,2023-01-15
financement,subvention,Subvention,30000.00,0,0,0,2023-02-01
charges,loyer,Loyer mensuel,3500.00,20,0,0,2023-01-01
charges,personnel,Salaire employé 1,5000.00,0,0,0,2023-01-01
charges,personnel,Salaire employé 2,6000.00,0,0,0,2023-01-01
charges,services,Téléphone et Internet,500.00,20,0,0,2023-01-01
charges,services,Électricité,800.00,14,0,0,2023-01-01
ventes,produit,Produit A,12000.00,20,0,0,2023-01-15
ventes,produit,Produit B,8000.00,20,0,0,2023-01-20
ventes,service,Service conseil,15000.00,20,0,0,2023-02-01"""
        
        st.download_button(
            label="📥 Télécharger le modèle CSV",
            data=csv_template,
            file_name="modele_donnees_financieres.csv",
            mime="text/csv"
        )
    
    # Interface d'importation
    uploaded_file = st.file_uploader("Glissez-déposez votre fichier CSV ici", type=["csv"])
    
    if uploaded_file is not None:
        try:
            # Traitement du fichier avec indicateur de chargement
            with st.spinner("Analyse du fichier CSV en cours..."):
                # Lecture du fichier
                df = pd.read_csv(uploaded_file, sep=None, engine='python')
                
                # Traitement et analyse
                processed_df, log_message, metrics = process_with_ai(df)
                
                if processed_df is not None:
                    st.success("✅ Fichier importé et traité avec succès!")
                    
                    # Afficher le rapport de traitement
                    with st.expander("📋 Rapport de traitement", expanded=False):
                        st.code(log_message)
                    
                    # Dashboard de résultats financiers avec onglets
                    tab1, tab2, tab3, tab4 = st.tabs(["Synthèse", "Rentabilité", "TVA", "Données importées"])
                    
                    with tab1:
                        # Métriques principales
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric(
                                "Total Immobilisations", 
                                f"{metrics['total_immobilisations']:,.2f} DHS"
                            )
                        
                        with col2:
                            st.metric(
                                "Total Financements", 
                                f"{metrics['total_financements']:,.2f} DHS"
                            )
                        
                        with col3:
                            st.metric(
                                "Charges Mensuelles", 
                                f"{metrics['total_charges']:,.2f} DHS"
                            )
                        
                        with col4:
                            st.metric(
                                "Ventes Mensuelles", 
                                f"{metrics['total_ventes']:,.2f} DHS",
                                f"{metrics['cash_flow_mensuel']:+,.2f} DHS"
                            )
                        
                        # Visualisations
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Graphique de répartition par type
                            pie_data = processed_df.groupby('type')['montant'].sum().reset_index()
                            if not pie_data.empty:
                                fig = px.pie(
                                    pie_data,
                                    values='montant',
                                    names='type',
                                    title="Répartition par type de données",
                                    color_discrete_sequence=px.colors.qualitative.Bold
                                )
                                fig.update_layout(
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    font_color='white'
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            # Graphique des immobilisations par catégorie
                            immo_data = processed_df[processed_df['type'] == 'immobilisation']
                            if not immo_data.empty:
                                immo_by_cat = immo_data.groupby('categorie')['montant'].sum().reset_index()
                                fig = px.bar(
                                    immo_by_cat,
                                    x='categorie',
                                    y='montant',
                                    title="Immobilisations par catégorie",
                                    color='categorie',
                                    color_discrete_sequence=px.colors.qualitative.Pastel
                                )
                                fig.update_layout(
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    font_color='white',
                                    xaxis_title="Catégorie",
                                    yaxis_title="Montant (DHS)"
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("Aucune immobilisation trouvée dans les données importées.")
                    
                    with tab2:
                        # Métriques de rentabilité
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric(
                                "Cash-Flow Mensuel",
                                f"{metrics['cash_flow_mensuel']:,.2f} DHS",
                                f"{metrics['cash_flow_mensuel']*12:+,.2f} DHS (annuel)"
                            )
                            
                            if metrics['payback_months'] != float('inf'):
                                st.metric(
                                    "Délai de récupération",
                                    f"{metrics['payback_months']:.1f} mois",
                                    f"{metrics['payback_years']:.2f} ans"
                                )
                            else:
                                st.metric(
                                    "Délai de récupération",
                                    "N/A",
                                    "Cash-flow négatif ou nul"
                                )
                        
                        with col2:
                            st.metric(
                                "ROI (Retour sur investissement)",
                                f"{metrics.get('roi_annuel', 0)*100:.2f}% par an",
                                f"{metrics.get('roi_mensuel', 0)*100:.2f}% par mois"
                            )
                            
                            st.metric(
                                "VAN (Valeur Actuelle Nette)",
                                f"{metrics.get('van', 0):,.2f} DHS",
                                f"TRI: {metrics.get('tri', 0)*100:.2f}%" if metrics.get('tri') else "TRI: N/A"
                            )
                        
                        # Graphique de projection des flux de trésorerie
                        if metrics['cash_flow_mensuel'] > 0:
                            months = list(range(0, 25))
                            cumulative_cash_flow = [-metrics['total_immobilisations']]
                            
                            for i in range(1, 25):
                                cumulative_cash_flow.append(cumulative_cash_flow[-1] + metrics['cash_flow_mensuel'])
                            
                            cash_flow_df = pd.DataFrame({
                                'Mois': months,
                                'Flux de trésorerie cumulé': cumulative_cash_flow
                            })
                            
                            fig = px.line(
                                cash_flow_df, 
                                x='Mois', 
                                y='Flux de trésorerie cumulé',
                                markers=True,
                                title="Projection du flux de trésorerie sur 24 mois"
                            )
                            
                            # Ligne horizontale à y=0
                            fig.add_shape(
                                type='line',
                                x0=0,
                                y0=0,
                                x1=24,
                                y1=0,
                                line=dict(color='gray', dash='dash')
                            )
                            
                            fig.update_layout(
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font_color='white',
                                xaxis_title="Mois",
                                yaxis_title="Flux de trésorerie cumulé (DHS)"
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Analyse détaillée de la rentabilité
                            with st.expander("🔍 Analyse de rentabilité détaillée"):
                                st.markdown("""
                                ### Analyse de la rentabilité
                                
                                L'analyse est basée sur les hypothèses suivantes:
                                - Les charges et revenus mensuels sont constants
                                - Le taux d'actualisation utilisé pour la VAN est de 8% annuel
                                - L'horizon d'investissement est de 5 ans
                                
                                **Interprétation des résultats:**
                                """)
                                
                                if metrics.get('van', 0) > 0:
                                    st.success("✅ La VAN est positive, ce qui indique que le projet est rentable sur 5 ans.")
                                else:
                                    st.warning("⚠️ La VAN est négative, ce qui indique que le projet n'est pas rentable sur 5 ans.")
                                
                                if metrics.get('payback_months', float('inf')) < 24:
                                    st.success(f"✅ Le délai de récupération est de {metrics.get('payback_months', 0):.1f} mois, ce qui est inférieur à 2 ans.")
                                elif metrics.get('payback_months', float('inf')) < 60:
                                    st.info(f"ℹ️ Le délai de récupération est de {metrics.get('payback_months', 0):.1f} mois, ce qui est acceptable mais pourrait être amélioré.")
                                else:
                                    st.warning(f"⚠️ Le délai de récupération est de {metrics.get('payback_months', 0):.1f} mois, ce qui est relativement long.")
                        else:
                            st.info("Impossible de générer une projection de trésorerie: cash-flow mensuel nul ou négatif.")
                    
                    with tab3:
                        # Analyse TVA
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric(
                                "TVA Collectée", 
                                f"{metrics.get('tva_collectee', 0):,.2f} DHS"
                            )
                        
                        with col2:
                            st.metric(
                                "TVA Déductible", 
                                f"{metrics.get('tva_deductible_achats', 0) + metrics.get('tva_deductible_immo', 0):,.2f} DHS",
                                f"Achats: {metrics.get('tva_deductible_achats', 0):,.2f} | Immos: {metrics.get('tva_deductible_immo', 0):,.2f}"
                            )
                        
                        with col3:
                            st.metric(
                                "TVA Nette", 
                                f"{metrics.get('tva_nette', 0):,.2f} DHS"
                            )
                        
                        # Graphique de répartition de la TVA
                        tva_data = {
                            'Composant': ['TVA Collectée', 'TVA Déductible Achats', 'TVA Déductible Immos'],
                            'Montant': [
                                metrics.get('tva_collectee', 0), 
                                metrics.get('tva_deductible_achats', 0), 
                                metrics.get('tva_deductible_immo', 0)
                            ]
                        }
                        
                        tva_df = pd.DataFrame(tva_data)
                        
                        if tva_df['Montant'].sum() > 0:
                            fig = px.bar(
                                tva_df,
                                x='Composant',
                                y='Montant',
                                title="Répartition des composants de la TVA",
                                color='Composant',
                                color_discrete_sequence=px.colors.qualitative.Pastel
                            )
                            
                            fig.update_layout(
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font_color='white',
                                xaxis_title="",
                                yaxis_title="Montant (DHS)"
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Détail TVA par catégorie
                        st.subheader("Détail de la TVA par catégorie")
                        
                        # Construire le tableau détaillé
                        tva_details = []
                        
                        # Ventes
                        ventes_df = processed_df[processed_df['type'] == 'ventes']
                        if not ventes_df.empty:
                            for _, row in ventes_df.groupby('categorie').agg({'montant': 'sum', 'taux_tva': 'mean'}).reset_index().iterrows():
                                tva_details.append({
                                    'Type': 'Ventes',
                                    'Catégorie': row['categorie'],
                                    'Montant HT': row['montant'],
                                    'Taux TVA': f"{row['taux_tva']:.1f}%",
                                    'TVA': row['montant'] * (row['taux_tva']/100),
                                    'Type TVA': 'Collectée'
                                })
                        
                        # Charges
                        charges_df = processed_df[processed_df['type'] == 'charges']
                        if not charges_df.empty:
                            for _, row in charges_df.groupby('categorie').agg({'montant': 'sum', 'taux_tva': 'mean'}).reset_index().iterrows():
                                tva_details.append({
                                    'Type': 'Charges',
                                    'Catégorie': row['categorie'],
                                    'Montant HT': row['montant'],
                                    'Taux TVA': f"{row['taux_tva']:.1f}%",
                                    'TVA': row['montant'] * (row['taux_tva']/100),
                                    'Type TVA': 'Déductible'
                                })
                        
                        # Immobilisations
                        immos_df = processed_df[processed_df['type'] == 'immobilisation']
                        if not immos_df.empty:
                            for _, row in immos_df.groupby('categorie').agg({'montant': 'sum', 'taux_tva': 'mean'}).reset_index().iterrows():
                                tva_details.append({
                                    'Type': 'Immobilisation',
                                    'Catégorie': row['categorie'],
                                    'Montant HT': row['montant'],
                                    'Taux TVA': f"{row['taux_tva']:.1f}%",
                                    'TVA': row['montant'] * (row['taux_tva']/100),
                                    'Type TVA': 'Déductible'
                                })
                        
                        # Afficher le tableau s'il y a des données
                        if tva_details:
                            tva_details_df = pd.DataFrame(tva_details)
                            # Formatter pour l'affichage
                            tva_details_df['Montant HT'] = tva_details_df['Montant HT'].apply(lambda x: f"{x:,.2f} DHS")
                            tva_details_df['TVA'] = tva_details_df['TVA'].apply(lambda x: f"{x:,.2f} DHS")
                            st.dataframe(tva_details_df, use_container_width=True)
                        else:
                            st.info("Aucune donnée TVA détaillée disponible.")
                    
                    with tab4:
                        # Données importées
                        st.subheader("Données importées")
                        
                        # Option de filtrage par type
                        type_filter = st.multiselect(
                            "Filtrer par type",
                            options=sorted(processed_df['type'].unique()),
                            default=sorted(processed_df['type'].unique())
                        )
                        
                        filtered_df = processed_df[processed_df['type'].isin(type_filter)]
                        
                        # Formatter pour l'affichage
                        display_df = filtered_df.copy()
                        display_df['montant'] = display_df['montant'].apply(lambda x: f"{x:,.2f}")
                        display_df['taux_tva'] = display_df['taux_tva'].apply(lambda x: f"{x:.1f}%")
                        display_df['duree_amort'] = display_df['duree_amort'].apply(lambda x: f"{x:.0f}" if x > 0 else "-")
                        display_df['taux_amort'] = display_df['taux_amort'].apply(lambda x: f"{x:.1f}%" if x > 0 else "-")
                        
                        st.dataframe(display_df, use_container_width=True)
                    
                    # Application des données
                    st.subheader("Application des données")
                    
                    # Options d'application
                    col1, col2 = st.columns(2)
                    with col1:
                        apply_all = st.checkbox("Tout appliquer", value=True)
                    
                    if not apply_all:
                        with col2:
                            sections_to_apply = st.multiselect(
                                "Sections à appliquer",
                                options=["Immobilisations", "Financements", "Charges", "Ventes", "Amortissements", "TVA"],
                                default=["Immobilisations", "Financements"]
                            )
                    else:
                        sections_to_apply = ["Immobilisations", "Financements", "Charges", "Ventes", "Amortissements", "TVA"]
                    
                    # Bouton d'application
                    if st.button("Appliquer les données", type="primary"):
                        # Filtrer par type pour la mise à jour
                        immos = processed_df[processed_df['type'] == 'immobilisation']
                        finances = processed_df[processed_df['type'] == 'financement']
                        charges = processed_df[processed_df['type'] == 'charges']
                        ventes = processed_df[processed_df['type'] == 'ventes']
                        
                        updates_made = []
                        
                        # Mise à jour des immobilisations
                        if "Immobilisations" in sections_to_apply and not immos.empty:
                            st.session_state.immos = []
                            for _, row in immos.iterrows():
                                st.session_state.immos.append({
                                    "Nom": row['nom'],
                                    "Montant": row['montant'],
                                    "Catégorie": row['categorie'],
                                    "Date": row['date']
                                })
                            updates_made.append("Immobilisations")
                        
                        # Mise à jour des financements
                        if "Financements" in sections_to_apply and not finances.empty:
                            # Apports
                            apports = finances[finances['categorie'] == 'apport']['montant'].sum()
                            if apports > 0:
                                st.session_state.investment_data['cash_contribution'] = apports
                                
                            # Emprunts
                            emprunts = finances[finances['categorie'] == 'emprunt']
                            if not emprunts.empty:
                                st.session_state.credits = []
                                for _, row in emprunts.iterrows():
                                    st.session_state.credits.append({
                                        "Nom": row['nom'],
                                        "Montant": row['montant'],
                                        "Date": row['date']
                                    })
                                # Mise à jour dans monthly_cashflow_data
                                st.session_state.monthly_cashflow_data['ressources']['Emprunts'] = emprunts['montant'].sum()
                            
                            # Subventions
                            subventions = finances[finances['categorie'] == 'subvention']
                            if not subventions.empty:
                                st.session_state.subsidies = []
                                for _, row in subventions.iterrows():
                                    st.session_state.subsidies.append({
                                        "Nom": row['nom'],
                                        "Montant": row['montant'],
                                        "Date": row['date']
                                    })
                                # Mise à jour dans monthly_cashflow_data
                                st.session_state.monthly_cashflow_data['ressources']['Subventions'] = subventions['montant'].sum()
                            
                            updates_made.append("Financements")
                        
                        # Mise à jour du tableau de trésorerie
                        if "Charges" in sections_to_apply and not charges.empty:
                            charges_by_cat = charges.groupby('categorie')['montant'].sum()
                            # Adapter les catégories aux clés existantes ou créer de nouvelles
                            for cat, amount in charges_by_cat.items():
                                found = False
                                for key in st.session_state.monthly_cashflow_data['charges_exploitation'].keys():
                                    if cat.lower() in key.lower():
                                        st.session_state.monthly_cashflow_data['charges_exploitation'][key] = amount
                                        found = True
                                        break
                                
                                if not found:
                                    # Ajouter une nouvelle catégorie
                                    cat_name = cat.capitalize()
                                    st.session_state.monthly_cashflow_data['charges_exploitation'][cat_name] = amount
                            
                            updates_made.append("Charges")
                        
                        if "Ventes" in sections_to_apply and not ventes.empty:
                            ventes_by_cat = ventes.groupby('categorie')['montant'].sum()
                            # Adapter les catégories aux clés existantes ou créer de nouvelles
                            for cat, amount in ventes_by_cat.items():
                                found = False
                                for key in st.session_state.monthly_cashflow_data['chiffre_affaires'].keys():
                                    if cat.lower() in key.lower():
                                        st.session_state.monthly_cashflow_data['chiffre_affaires'][key] = amount
                                        found = True
                                        break
                                
                                if not found:
                                    # Ajouter une nouvelle catégorie
                                    cat_name = cat.capitalize()
                                    st.session_state.monthly_cashflow_data['chiffre_affaires'][cat_name] = amount
                            
                            updates_made.append("Ventes")
                        
                        # Mise à jour du tableau d'amortissement
                        if "Amortissements" in sections_to_apply and not immos.empty:
                            for _, row in immos.iterrows():
                                # Trouver l'immobilisation correspondante ou la plus proche
                                best_match = None
                                best_match_score = 0
                                
                                for i, item in enumerate(st.session_state.detailed_amortization):
                                    # Vérifier si le nom correspond exactement
                                    if item["name"].lower() == row['nom'].lower():
                                        best_match = i
                                        break
                                    
                                    # Sinon vérifier si la catégorie est dans le nom
                                    elif row['categorie'].lower() in item["name"].lower():
                                        match_score = len(row['categorie'])
                                        if match_score > best_match_score:
                                            best_match = i
                                            best_match_score = match_score
                                
                                # Mettre à jour l'élément trouvé ou en ajouter un nouveau
                                if best_match is not None:
                                    st.session_state.detailed_amortization[best_match]["amount"] = row['montant']
                                    st.session_state.detailed_amortization[best_match]["duration"] = row['duree_amort']
                                    st.session_state.detailed_amortization[best_match]["rate"] = row['taux_amort']
                                    
                                    # Recalculer l'amortissement
                                    annual_amort = row['montant'] * (row['taux_amort'] / 100)
                                    st.session_state.detailed_amortization[best_match]["amortization_n"] = annual_amort
                                    st.session_state.detailed_amortization[best_match]["amortization_n1"] = annual_amort
                                    st.session_state.detailed_amortization[best_match]["amortization_n2"] = annual_amort
                                else:
                                    # Ajouter une nouvelle entrée
                                    annual_amort = row['montant'] * (row['taux_amort'] / 100)
                                    st.session_state.detailed_amortization.append({
                                        "name": row['nom'],
                                        "amount": row['montant'],
                                        "duration": row['duree_amort'],
                                        "rate": row['taux_amort'],
                                        "amortization_n": annual_amort,
                                        "amortization_n1": annual_amort,
                                        "amortization_n2": annual_amort
                                    })
                            
                            updates_made.append("Amortissements")
                        
                        # Mise à jour de la TVA
                        if "TVA" in sections_to_apply:
                            # TVA sur achats
                            if not charges.empty:
                                charges_ht = charges['montant'].sum()
                                tva_charges = charges.apply(lambda x: x['montant'] * (x['taux_tva']/100), axis=1).sum()
                                
                                st.session_state.vat_budget_data['achats']['Achat HT'] = charges_ht
                                st.session_state.vat_budget_data['achats']['TVA déductible sur achat'] = tva_charges
                            
                            # TVA sur ventes
                            if not ventes.empty:
                                ventes_ht = ventes['montant'].sum()
                                tva_ventes = ventes.apply(lambda x: x['montant'] * (x['taux_tva']/100), axis=1).sum()
                                
                                st.session_state.vat_budget_data['ventes']['Vente en HT'] = ventes_ht
                                st.session_state.vat_budget_data['ventes']['TVA collecte sur vente'] = tva_ventes
                            
                            # TVA sur immobilisations
                            if not immos.empty:
                                tva_immo = immos.apply(lambda x: x['montant'] * (x['taux_tva']/100), axis=1).sum()
                                
                                st.session_state.vat_budget_data['tva_immobilisations']["TVA dedustible sur immobilisation"] = tva_immo
                            
                            updates_made.append("TVA")
                        
                        # Afficher un résumé des mises à jour effectuées
                        if updates_made:
                            st.success(f"✅ Données appliquées avec succès : {', '.join(updates_made)}")
                            st.balloons()
                        else:
                            st.warning("⚠️ Aucune donnée sélectionnée pour l'application.")
        
        except Exception as e:
            st.error(f"Une erreur s'est produite lors du traitement du fichier : {str(e)}")
            st.info("Veuillez vérifier le format de votre fichier CSV et réessayer.")


# ========== FONCTION PRINCIPALE ==========
def main():
    # Initialisation des données
    init_session_state()
    
    # Titre de l'application
    st.title("💼 Simulateur d'Étude Financière")
    
    # Menu de navigation avec la nouvelle option d'importation CSV
    menu = [
        "Fiche Entreprise", 
        "Investissements", 
        "Bilan", 
        "Compte de Résultat", 
        "Cash Flow", 
        "Amortissements",
        "Amortissement Détaillé",
        "Tableau de Trésorerie Mensuel", 
        "Budget TVA",
        "📤 Importation CSV"  # Option existante
    ]
    choice = st.sidebar.selectbox("Navigation", menu)
    
    # Informations dans la sidebar
    with st.sidebar:
        st.write("---")
        
        # Afficher la date et le nom d'entreprise
        st.caption(f"Entreprise: {st.session_state.basic_info['company_name']}")
        st.caption(f"Date: {datetime.now().strftime('%d/%m/%Y')}")
        
        # Promotion de la nouvelle fonctionnalité
        st.info("🆕 **NOUVEAU!** Importez vos données facilement par CSV")
        
        # Boutons d'actions globales
        st.write("#### Actions")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 Importer", key="quick_import"):
                choice = "📤 Importation CSV"
                st.rerun()
        with col2:
            if st.button("🔄 Réinitialiser", key="reset_all"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                init_session_state()
                st.rerun()
        
        # Section de sauvegarde des données dans la sidebar
        st.write("---")
        st.write("#### 💾 Sauvegarde & Export")
        
        # Section de sauvegarde des données
        with st.expander("Sauvegarde des données", expanded=False):
            st.caption("Sauvegardez ou restaurez l'état actuel de votre projet")
            
            # Bouton pour sauvegarder les données
            if st.button("💾 Sauvegarder", key="save_data_btn"):
                try:
                    save_data()
                except Exception as e:
                    st.error(f"Erreur: {str(e)}")
            
            # Bouton pour télécharger les données
            try:
                data_json = get_session_data_as_json()
                company_name = st.session_state.basic_info.get('company_name', 'entreprise')
                
                st.download_button(
                    label="⬇️ Télécharger (JSON)",
                    data=data_json,
                    file_name=f"{company_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                    mime="application/json",
                    key="download_json_btn"
                )
            except Exception as e:
                st.error(f"Erreur de préparation des données: {str(e)}")
            
            # Option pour charger des données sauvegardées
            uploaded_file = st.file_uploader("Charger une sauvegarde", type=['json'], key="json_uploader")
            if uploaded_file is not None:
                try:
                    load_data_from_json(uploaded_file)
                    st.success("✅ Données chargées avec succès!")
                    if st.button("Actualiser l'affichage", key="refresh_after_load"):
                        st.rerun()
                except Exception as e:
                    st.error(f"Erreur: {str(e)}")
        
        # Section de génération de rapport PDF
        with st.expander("Génération de rapport PDF", expanded=False):
            st.caption("Créez un rapport PDF complet de votre projet")
            
            # Options du rapport
            company_name = st.session_state.basic_info.get('company_name', 'Entreprise')
            report_name = st.text_input(
                "Nom du rapport", 
                value=f"Étude Financière - {company_name}",
                key="pdf_report_name"
            )
            
            include_sections = st.multiselect(
                "Sections à inclure",
                options=["Informations générales", "Investissements", "Bilan prévisionnel", 
                        "Compte de résultat", "Trésorerie", "Analyse TVA", "Amortissements"],
                default=["Informations générales", "Investissements", "Bilan prévisionnel", 
                        "Compte de résultat", "Trésorerie"],
                key="pdf_sections"
            )
            
            # Génération du PDF
            if st.button("🖨️ Générer le PDF", key="generate_pdf_btn"):
                with st.spinner("Génération du rapport en cours..."):
                    try:
                        pdf_file = generate_pdf_report(report_name, include_sections)
                        st.success("✅ Rapport PDF généré avec succès!")
                        
                        # Téléchargement du PDF
                        with open(pdf_file, "rb") as f:
                            pdf_bytes = f.read()
                        
                        st.download_button(
                            label="⬇️ Télécharger le PDF",
                            data=pdf_bytes,
                            file_name=f"{report_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            key="download_pdf_btn"
                        )
                    except Exception as e:
                        st.error(f"Erreur lors de la génération du PDF: {str(e)}")
        
        st.write("---")
        st.caption("© 2024 - Simulateur d'Étude Financière")
    
    # Affichage de la page sélectionnée
    if choice == "Fiche Entreprise":
        show_company_info()
    elif choice == "Investissements":
        show_investments()
    elif choice == "Bilan":
        show_balance_sheet()
    elif choice == "Compte de Résultat":
        show_income_statement()
    elif choice == "Cash Flow":
        show_cash_flow()
    elif choice == "Amortissements":
        show_amortization()
    elif choice == "Amortissement Détaillé":
        show_detailed_amortization()
    elif choice == "Tableau de Trésorerie Mensuel":
        show_monthly_cashflow()
    elif choice == "Budget TVA":
        show_vat_budget()
    elif choice == "📤 Importation CSV":
        show_csv_import()



# ========== FICHE ENTREPRISE ==========
def show_company_info():
    st.header("Fiche d'Entreprise")

    with st.expander("Informations Générales", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.basic_info['company_name'] = st.text_input(
                "Raison sociale", 
                value=st.session_state.basic_info['company_name'])
            
            st.session_state.basic_info['company_type'] = st.selectbox(
                "Type de société", 
                ["SARL", "SA", "SNC", "SARLAU", "COOPERATIVE"],
                index=["SARL", "SA", "SNC", "SARLAU", "COOPERATIVE"].index(st.session_state.basic_info['company_type']))
            
            st.session_state.basic_info['creation_date'] = st.date_input(
                "Année de création", 
                st.session_state.basic_info['creation_date'])
            
            st.session_state.basic_info['closing_date'] = st.text_input(
                "Date de clôture d'exercice", 
                st.session_state.basic_info['closing_date'])

        with col2:
            # Changed from selectbox to text_input for sector
            st.session_state.basic_info['sector'] = st.text_input(
                "Secteur d'activité",
                value=st.session_state.basic_info['sector'])
            
            st.session_state.basic_info['tax_id'] = st.text_input(
                "Identifiant fiscal", 
                st.session_state.basic_info['tax_id'])
            
            st.session_state.basic_info['partners'] = st.number_input(
                "Nombre d'associés", 1, 100, 
                st.session_state.basic_info['partners'], step=1)

    with st.expander("Coordonnées"):
        st.session_state.basic_info['address'] = st.text_area(
            "Adresse", 
            st.session_state.basic_info['address'])
        
        st.session_state.basic_info['phone'] = st.text_input(
            "Téléphone", 
            st.session_state.basic_info['phone'])
        
        st.session_state.basic_info['email'] = st.text_input(
            "Courriel", 
            st.session_state.basic_info['email'])
    
    # Affichage d'un résumé
    with st.expander("Résumé", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**{st.session_state.basic_info['company_name']}**")
            st.write(f"Type: {st.session_state.basic_info['company_type']}")
            st.write(f"Secteur: {st.session_state.basic_info['sector']}")
        with col2:
            st.write(f"Date de création: {st.session_state.basic_info['creation_date'].strftime('%d/%m/%Y')}")
            st.write(f"Clôture d'exercice: {st.session_state.basic_info['closing_date']}")
            if st.session_state.basic_info['email']:
                st.write(f"Contact: {st.session_state.basic_info['email']}")

# ========== INVESTISSEMENTS ==========
def show_investments():
    st.header("Investissements et Financement")

    with st.expander("Détail des Investissements", expanded=True):
        st.subheader("Frais Préliminaires")
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.investment_data['brand_registration'] = st.number_input(
                "Enregistrement de la marque (DHS)", 
                min_value=0.0,
                value=st.session_state.investment_data['brand_registration'])
        with col2:
            st.session_state.investment_data['sarl_formation'] = st.number_input(
                "Frais de constitution SARL (DHS)",
                min_value=0.0,
                value=st.session_state.investment_data['sarl_formation'])
        
        # Mettre à jour les frais préliminaires pour la cohérence avec d'autres pages
        if len(st.session_state.frais_preliminaires) >= 1:
            st.session_state.frais_preliminaires[0]["valeur"] = st.session_state.investment_data['brand_registration']
        if len(st.session_state.frais_preliminaires) >= 2:
            st.session_state.frais_preliminaires[1]["valeur"] = st.session_state.investment_data['sarl_formation']

        st.subheader("Immobilisations Corporelles")
        new_name = st.text_input("Nom de l'immobilisation", key="new_imm_name")
        new_value = st.number_input("Montant (DHS)", key="new_imm_value", value=0.0, min_value=0.0)
        
        if st.button("➕ Ajouter une immobilisation", key="add_immo"):
            if new_name and new_value > 0:
                st.session_state.immos.append({"Nom": new_name, "Montant": float(new_value)})

        if st.session_state.immos:
            df_immos = pd.DataFrame(st.session_state.immos)
            
            # Ajouter des boutons de suppression pour chaque immobilisation
            edited_df = st.data_editor(
                df_immos,
                use_container_width=True,
                num_rows="dynamic",
                key="immos_editor"
            )
            
            # Mettre à jour les immobilisations avec les valeurs éditées
            st.session_state.immos = edited_df.to_dict('records')
            
            total_immos = edited_df["Montant"].sum()
        else:
            total_immos = 0.0
        
        st.write(f"**Total Immobilisations Corporelles : {total_immos:,.2f} DHS**")
        
        # Stocker le total pour les autres pages
        st.session_state.calculated_data['total_immos'] = total_immos

        st.subheader("Système d'Information")
        st.session_state.investment_data['web_dev'] = st.number_input(
            "Développement application web (DHS)", 
            min_value=0.0,
            value=st.session_state.investment_data['web_dev'])

    with st.expander("Plan de Financement", expanded=True):
        st.subheader("Apports")
        st.session_state.investment_data['cash_contribution'] = st.number_input(
            "Apport en numéraire (DHS)", 
            min_value=0.0,
            value=st.session_state.investment_data['cash_contribution'])
        
        st.session_state.investment_data['in_kind'] = st.number_input(
            "Apport en nature (DHS)", 
            min_value=0.0,
            value=st.session_state.investment_data['in_kind'])

        st.subheader("Crédits")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            new_credit_name = st.text_input("Nom du crédit", key="new_credit_name")
        with col2:
            new_credit_amount = st.number_input("Montant (DHS)", key="new_credit_amount", value=0.0, min_value=0.0)
        with col3:
            new_credit_rate = st.number_input("Taux (%)", key="new_credit_rate", value=0.0, min_value=0.0, max_value=100.0) / 100
        with col4:
            new_credit_duration = st.number_input("Durée (ans)", key="new_credit_duration", value=0, step=1, min_value=0)
        
        if st.button("➕ Ajouter un crédit", key="add_credit"):
            if new_credit_name and new_credit_amount > 0:
                st.session_state.credits.append({
                    "Nom": new_credit_name,
                    "Montant": float(new_credit_amount),
                    "Taux": float(new_credit_rate),
                    "Durée": int(new_credit_duration)
                })
        
        if st.session_state.credits:
            df_credits = pd.DataFrame(st.session_state.credits)
            
            # Ajouter des boutons de suppression pour chaque crédit
            edited_df = st.data_editor(
                df_credits,
                use_container_width=True,
                num_rows="dynamic",
                key="credits_editor"
            )
            
            # Mettre à jour les crédits avec les valeurs éditées
            st.session_state.credits = edited_df.to_dict('records')
            
            total_credits = edited_df["Montant"].sum()
        else:
            total_credits = 0.0
        
        st.write(f"**Total Crédits : {total_credits:,.2f} DHS**")
        
        # Stocker le total pour les autres pages
        st.session_state.calculated_data['total_credits'] = total_credits

        st.subheader("Subventions")
        col1, col2 = st.columns(2)
        with col1:
            new_subsidy_name = st.text_input("Nom de la subvention", key="new_subsidy_name")
        with col2:
            new_subsidy_amount = st.number_input("Montant (DHS)", key="new_subsidy_amount", value=0.0, min_value=0.0)
        
        if st.button("➕ Ajouter une subvention", key="add_subsidy"):
            if new_subsidy_name and new_subsidy_amount > 0:
                st.session_state.subsidies.append({
                    "Nom": new_subsidy_name,
                    "Montant": float(new_subsidy_amount)
                })
        
        if st.session_state.subsidies:
            df_subsidies = pd.DataFrame(st.session_state.subsidies)
            
            # Ajouter des boutons de suppression pour chaque subvention
            edited_df = st.data_editor(
                df_subsidies,
                use_container_width=True,
                num_rows="dynamic", 
                key="subsidies_editor"
            )
            
            # Mettre à jour les subventions avec les valeurs éditées
            st.session_state.subsidies = edited_df.to_dict('records')
            
            total_subsidies = edited_df["Montant"].sum()
        else:
            total_subsidies = 0.0
        
        st.write(f"**Total Subventions : {total_subsidies:,.2f} DHS**")
        
        # Stocker le total pour les autres pages
        st.session_state.calculated_data['total_subsidies'] = total_subsidies
        
        # Calculer et stocker les totaux globaux
        total_frais = st.session_state.investment_data['brand_registration'] + st.session_state.investment_data['sarl_formation']
        st.session_state.calculated_data['total_frais'] = total_frais
        st.session_state.calculated_data['total_investissement'] = total_frais + total_immos + st.session_state.investment_data['web_dev']
        st.session_state.calculated_data['total_financement'] = st.session_state.investment_data['cash_contribution'] + st.session_state.investment_data['in_kind'] + total_credits + total_subsidies

    # Résumé du plan de financement
    with st.expander("Résumé du Plan de Financement", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Sources")
            st.write(f"Apport en numéraire: {st.session_state.investment_data['cash_contribution']:,.2f} DHS")
            st.write(f"Apport en nature: {st.session_state.investment_data['in_kind']:,.2f} DHS")
            st.write(f"Crédits: {st.session_state.calculated_data['total_credits']:,.2f} DHS")
            st.write(f"Subventions: {st.session_state.calculated_data['total_subsidies']:,.2f} DHS")
            st.write(f"**Total: {st.session_state.calculated_data['total_financement']:,.2f} DHS**")
        
        with col2:
            st.subheader("Emplois")
            st.write(f"Frais préliminaires: {st.session_state.calculated_data['total_frais']:,.2f} DHS")
            st.write(f"Immobilisations corporelles: {st.session_state.calculated_data['total_immos']:,.2f} DHS")
            st.write(f"Système d'information: {st.session_state.investment_data['web_dev']:,.2f} DHS")
            st.write(f"**Total: {st.session_state.calculated_data['total_investissement']:,.2f} DHS**")
        
        # Calcul de l'équilibre
        equilibre = st.session_state.calculated_data['total_financement'] - st.session_state.calculated_data['total_investissement']
        
        if abs(equilibre) < 0.01:
            st.success("✅ Plan de financement équilibré")
        else:
            if equilibre > 0:
                st.warning(f"⚠️ Excédent de financement : {equilibre:,.2f} DHS")
            else:
                st.error(f"❌ Déficit de financement : {abs(equilibre):,.2f} DHS")

# ========== BILAN ==========
def show_balance_sheet():
    st.header("Bilan d'Ouverture")
    
    # Mettre à jour les valeurs importantes avec les données des autres onglets
    if 'calculated_data' in st.session_state:
        # Frais préliminaires
        if len(st.session_state.actif_data['immobilisations_non_valeur']) > 0:
            st.session_state.actif_data['immobilisations_non_valeur'][0]['value'] = st.session_state.calculated_data.get('total_frais', 5700.0)
        
        # Immobilisations incorporelles (système d'information)
        if len(st.session_state.actif_data['immobilisations_incorporelles']) > 2:
            st.session_state.actif_data['immobilisations_incorporelles'][2]['value'] = st.session_state.investment_data.get('web_dev', 80000.0)
        
        # Apports (capital social)
        total_apports = st.session_state.investment_data.get('cash_contribution', 50511.31) + st.session_state.investment_data.get('in_kind', 20000.0)
        if len(st.session_state.passif_data['capitaux_propres']) > 0:
            st.session_state.passif_data['capitaux_propres'][0]['value'] = total_apports
        
        # Subventions
        if len(st.session_state.passif_data['capitaux_propres']) > 2:
            st.session_state.passif_data['capitaux_propres'][2]['value'] = st.session_state.calculated_data.get('total_subsidies', 0.0)
        
        # Dettes de financement
        if len(st.session_state.passif_data['dettes_financement']) > 0:
            st.session_state.passif_data['dettes_financement'][0]['value'] = st.session_state.calculated_data.get('total_credits', 0.0)

    # Fonctions pour gérer les lignes
    def add_line(category, section, default_label="Nouvelle ligne", default_value=0.0):
        if category == 'actif':
            st.session_state.actif_data[section].append({'label': default_label, 'value': default_value})
        else:
            st.session_state.passif_data[section].append({'label': default_label, 'value': default_value})

    def remove_line(category, section, index):
        if category == 'actif':
            st.session_state.actif_data[section].pop(index)
        else:
            st.session_state.passif_data[section].pop(index)

    # Layout en colonnes
    col1, col2 = st.columns(2)
    
    # COLONNE ACTIF
    with col1:
        with st.expander("ACTIF", expanded=True):
            # ACTIF IMMOBILISÉ
            st.subheader("ACTIF IMMOBILISÉ")
            
            # Gestion des sections actif
            sections_actif = [
                ('immobilisations_non_valeur', "Immobilisations en non-valeur"),
                ('immobilisations_incorporelles', "Immobilisations incorporelles"),
                ('immobilisations_corporelles', "Immobilisations corporelles")
            ]
            
            for section_key, section_title in sections_actif:
                with st.container():
                    st.markdown(f"**{section_title}**")
                    
                    # Utiliser un data_editor pour une meilleure UX
                    df_section = pd.DataFrame(st.session_state.actif_data[section_key])
                    
                    edited_df = st.data_editor(
                        df_section,
                        column_config={
                            "label": "Libellé",
                            "value": st.column_config.NumberColumn("Montant (DHS)", format="%.2f")
                        },
                        hide_index=True,
                        num_rows="dynamic",
                        key=f"editor_actif_{section_key}"
                    )
                    
                    # Mettre à jour les données de session
                    st.session_state.actif_data[section_key] = edited_df.to_dict('records')
                    
                    # Calcul du total par section
                    total_section = sum(item['value'] for item in st.session_state.actif_data[section_key])
                    st.markdown(f"**Total {section_title} : {total_section:,.2f} DHS**")
            
            # ACTIF CIRCULANT
            st.subheader("ACTIF CIRCULANT")
            
            sections_circulant = [
                ('stocks', "Stocks"),
                ('tresorerie_actif', "Trésorerie-Actif")
            ]
            
            for section_key, section_title in sections_circulant:
                with st.container():
                    st.markdown(f"**{section_title}**")
                    
                    # Utiliser un data_editor pour cette section aussi
                    df_section = pd.DataFrame(st.session_state.actif_data[section_key])
                    
                    edited_df = st.data_editor(
                        df_section,
                        column_config={
                            "label": "Libellé",
                            "value": st.column_config.NumberColumn("Montant (DHS)", format="%.2f")
                        },
                        hide_index=True,
                        num_rows="dynamic",
                        key=f"editor_actif_{section_key}"
                    )
                    
                    # Mettre à jour les données de session
                    st.session_state.actif_data[section_key] = edited_df.to_dict('records')
                    
                    # Calcul du total par section
                    total_section = sum(item['value'] for item in st.session_state.actif_data[section_key])
                    st.markdown(f"**Total {section_title} : {total_section:,.2f} DHS**")
            
            # Calcul du total général actif
            total_actif = sum(
                sum(item['value'] for item in st.session_state.actif_data[section]) 
                for section in st.session_state.actif_data
            )
            st.markdown(f"**TOTAL GENERAL ACTIF : {total_actif:,.2f} DHS**")
    
    # COLONNE PASSIF
    with col2:
        with st.expander("PASSIF", expanded=True):
            # CAPITAUX PROPRES
            st.subheader("CAPITAUX PROPRES")
            
            with st.container():
                df_capitaux = pd.DataFrame(st.session_state.passif_data['capitaux_propres'])
                
                edited_df = st.data_editor(
                    df_capitaux,
                    column_config={
                        "label": "Libellé",
                        "value": st.column_config.NumberColumn("Montant (DHS)", format="%.2f")
                    },
                    hide_index=True,
                    num_rows="dynamic",
                    key="editor_passif_capitaux"
                )
                
                # Mettre à jour les données de session
                st.session_state.passif_data['capitaux_propres'] = edited_df.to_dict('records')
                
                total_capitaux = sum(item['value'] for item in st.session_state.passif_data['capitaux_propres'])
                st.markdown(f"**Total Capitaux propres : {total_capitaux:,.2f} DHS**")
            
            # DETTES DE FINANCEMENT
            st.subheader("DETTES DE FINANCEMENT")
            
            with st.container():
                df_dettes = pd.DataFrame(st.session_state.passif_data['dettes_financement'])
                
                edited_df = st.data_editor(
                    df_dettes,
                    column_config={
                        "label": "Libellé",
                        "value": st.column_config.NumberColumn("Montant (DHS)", format="%.2f")
                    },
                    hide_index=True,
                    num_rows="dynamic",
                    key="editor_passif_dettes"
                )
                
                # Mettre à jour les données de session
                st.session_state.passif_data['dettes_financement'] = edited_df.to_dict('records')
                
                total_dettes = sum(item['value'] for item in st.session_state.passif_data['dettes_financement'])
                st.markdown(f"**Total Dettes financement : {total_dettes:,.2f} DHS**")
            
            st.markdown(f"**TOTAL FINANCEMENT PERMANENT : {total_capitaux + total_dettes:,.2f} DHS**")
            
            # PASSIF CIRCULANT
            st.subheader("PASSIF CIRCULANT")
            
            with st.container():
                df_circulant = pd.DataFrame(st.session_state.passif_data['passif_circulant'])
                
                edited_df = st.data_editor(
                    df_circulant,
                    column_config={
                        "label": "Libellé",
                        "value": st.column_config.NumberColumn("Montant (DHS)", format="%.2f")
                    },
                    hide_index=True,
                    num_rows="dynamic",
                    key="editor_passif_circulant"
                )
                
                # Mettre à jour les données de session
                st.session_state.passif_data['passif_circulant'] = edited_df.to_dict('records')
                
                total_circulant = sum(item['value'] for item in st.session_state.passif_data['passif_circulant'])
                st.markdown(f"**Total Passif circulant : {total_circulant:,.2f} DHS**")
            
            # TRÉSORERIE-PASSIF
            st.subheader("TRÉSORERIE-PASSIF")
            
            with st.container():
                df_tresorerie = pd.DataFrame(st.session_state.passif_data['tresorerie_passif'])
                
                edited_df = st.data_editor(
                    df_tresorerie,
                    column_config={
                        "label": "Libellé",
                        "value": st.column_config.NumberColumn("Montant (DHS)", format="%.2f")
                    },
                    hide_index=True,
                    num_rows="dynamic",
                    key="editor_passif_tresorerie"
                )
                
                # Mettre à jour les données de session
                st.session_state.passif_data['tresorerie_passif'] = edited_df.to_dict('records')
                
                total_tresorerie = sum(item['value'] for item in st.session_state.passif_data['tresorerie_passif'])
                st.markdown(f"**Total Trésorerie-passif : {total_tresorerie:,.2f} DHS**")
            
            # Calcul du total général passif
            total_passif = total_capitaux + total_dettes + total_circulant + total_tresorerie
            st.markdown(f"**TOTAL GENERAL PASSIF : {total_passif:,.2f} DHS**")

            # Vérification équilibre bilan
            st.session_state.calculated_data['total_actif'] = total_actif
            st.session_state.calculated_data['total_passif'] = total_passif
            
            if abs(total_actif - total_passif) > 0.01:
                st.error(f"⚠️ Déséquilibre bilan : Actif ({total_actif:,.2f}) ≠ Passif ({total_passif:,.2f})")
            else:
                st.success("✓ Bilan équilibré")

# ========== COMPTE DE RÉSULTAT ==========
def show_income_statement():
    st.header("📊 Compte de Résultat Prévisionnel Dynamique")

    # Configuration des paramètres
    with st.expander("⚙️ Configuration des Taux de Croissance", expanded=True):
        st.write("Définissez précisément la croissance annuelle :")
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.income_statement_params['growth_n'] = st.slider(
                "Taux N → N+1 (%)", 
                min_value=-20.0,
                max_value=100.0,
                value=float(st.session_state.income_statement_params['growth_n'] * 100),
                step=1.0,
                help="Croissance attendue entre l'année N et N+1"
            ) / 100
        
        with col2:
            same_growth = st.checkbox("Même taux pour N+1 → N+2", value=True)
            
            if same_growth:
                st.session_state.income_statement_params['growth_n1'] = st.session_state.income_statement_params['growth_n']
            else:
                st.session_state.income_statement_params['growth_n1'] = st.slider(
                    "Taux N+1 → N+2 (%)", 
                    min_value=-20.0,
                    max_value=100.0,
                    value=float(st.session_state.income_statement_params['growth_n1'] * 100),
                    step=1.0
                ) / 100

    # Paramètres complémentaires dans la sidebar
    with st.expander("🔧 Paramètres Avancés"):
        st.session_state.income_statement_params['base_ca'] = st.number_input(
            "CA de Base (Année N)", 
            value=st.session_state.income_statement_params['base_ca'],
            min_value=0.0,
            step=10000.0,
            format="%.2f"
        )
        
        st.session_state.income_statement_params['cost_ratio'] = st.slider(
            "Ratio Charges/CA Initial", 
            min_value=0.5,
            max_value=0.95,
            value=st.session_state.income_statement_params['cost_ratio'],
            step=0.01,
            format="%.2f"
        )
        
        st.session_state.income_statement_params['efficiency_improvement'] = st.slider(
            "Gain d'Efficacité Annuel", 
            min_value=0.0,
            max_value=0.1,
            value=st.session_state.income_statement_params['efficiency_improvement'],
            step=0.005,
            format="%.3f"
        )

    # Calcul des projections
    years = ["N", "N+1", "N+2"]
    ca_projections = [
        st.session_state.income_statement_params['base_ca'],
        st.session_state.income_statement_params['base_ca'] * (1 + st.session_state.income_statement_params['growth_n']),
        st.session_state.income_statement_params['base_ca'] * (1 + st.session_state.income_statement_params['growth_n']) * (1 + st.session_state.income_statement_params['growth_n1'])
    ]
    
    # Calcul des charges avec amélioration progressive
    charge_ratios = [
        st.session_state.income_statement_params['cost_ratio'] * (1 - st.session_state.income_statement_params['efficiency_improvement'])**i 
        for i in range(3)
    ]
    charge_projections = [ca * ratio for ca, ratio in zip(ca_projections, charge_ratios)]

    # Calcul des charges financières
    def calculate_financial_charges():
        charges = []
        for credit in st.session_state.get("credits", []):
            try:
                principal = float(credit.get("Montant", 0))
                rate = float(credit.get("Taux", 5)) / 100  # Convertir le taux en décimal
                term = int(credit.get("Durée", 1))
                
                if principal > 0 and rate > 0 and term > 0:
                    # Calcul simplifié des intérêts annuels
                    annual_interest = principal * rate
                    charges.append(annual_interest)
            except (ValueError, TypeError, KeyError):
                continue  # Ignorer les crédits avec données invalides
        
        return sum(charges) if charges else 3350.0  # Valeur par défaut

    financial_charges = calculate_financial_charges()
    
    # Calcul des résultats
    operating_results = [ca - ch for ca, ch in zip(ca_projections, charge_projections)]
    pretax_results = [op - financial_charges for op in operating_results]
    tax_rate = 0.15  # Taux d'IS
    taxes = [max(0, pr * tax_rate) for pr in pretax_results]  # Évite impôts négatifs
    net_results = [pr - tax for pr, tax in zip(pretax_results, taxes)]

    # Création du DataFrame
    df = pd.DataFrame({
        "Année": years,
        "Taux Croissance": ["-", f"{st.session_state.income_statement_params['growth_n']:.1%}", f"{st.session_state.income_statement_params['growth_n1']:.1%}"],
        "Chiffre d'affaires": ca_projections,
        "Charges d'exploitation": charge_projections,
        "Résultat d'exploitation": operating_results,
        "Charges financières": [financial_charges] * 3,
        "Résultat avant impôt": pretax_results,
        "Impôt sur les sociétés": taxes,
        "Résultat net": net_results
    })

    # Stocker les résultats dans session_state pour les autres pages
    st.session_state.income_statement = {
        "Chiffre d'affaires": ca_projections,
        "Charges d'exploitation": charge_projections,
        "Résultat d'exploitation": operating_results,
        "Charges financières": [financial_charges] * 3,
        "Résultat net": net_results
    }

    # Affichage des résultats - PARTIE AMÉLIORÉE POUR LA LISIBILITÉ
    with st.expander("📋 Détails des Résultats", expanded=True):
        # Définir des formats personnalisés pour les nombres
        formats = {
            "Chiffre d'affaires": "{:,.2f} DHS",
            "Charges d'exploitation": "{:,.2f} DHS",
            "Résultat d'exploitation": "{:,.2f} DHS",
            "Charges financières": "{:,.2f} DHS",
            "Résultat avant impôt": "{:,.2f} DHS",
            "Impôt sur les sociétés": "{:,.2f} DHS",
            "Résultat net": "{:,.2f} DHS"
        }
        
        # Fonction pour colorer les valeurs négatives avec un contraste adapté au fond sombre
        def color_negative_values(val):
            if isinstance(val, (int, float)):
                color = '#FF6B6B' if val < 0 else '#E8FFEA'  # Rouge clair pour négatif, blanc verdâtre pour positif
                return f'color: {color}; font-weight: bold'
            return ''
        
        # Style amélioré avec meilleur contraste et formatage
        styled_df = df.style \
            .format(formats) \
            .applymap(color_negative_values, subset=pd.IndexSlice[:, df.columns[2:]]) \
            .set_properties(**{
                'text-align': 'right',
                'font-size': '15px',
                'border': '1px solid #3A3F44',
                'padding': '8px',
                'background-color': '#1E2227',
                'white-space': 'nowrap'  # Empêche le retour à la ligne dans les cellules
            }) \
            .set_table_styles([
                {'selector': 'th', 
                 'props': [
                    ('font-size', '16px'),
                    ('text-align', 'center'),
                    ('background-color', '#2A313B'),
                    ('color', 'white'),
                    ('font-weight', 'bold'),
                    ('padding', '10px'),
                    ('border', '1px solid #3A3F44')
                ]},
                {'selector': 'tbody tr:nth-of-type(odd)',
                 'props': [('background-color', '#1A1D22')]},
                {'selector': 'tbody tr:hover',
                 'props': [('background-color', '#323842')]},
                {'selector': '.col0', 
                 'props': [('font-weight', 'bold'), ('text-align', 'center')]},  # Style pour la colonne Année
            ]) \
            .background_gradient(cmap='Greens', subset=["Chiffre d'affaires"], vmin=min(ca_projections), vmax=max(ca_projections)*1.1) \
            .background_gradient(cmap='Blues', subset=["Résultat net"], vmin=min(net_results), vmax=max(net_results)*1.1)
        
        # On utilise HTML brut plutôt que st.dataframe pour un meilleur contrôle de l'apparence
        html_table = styled_df.to_html()
        
        # Ajout de styles CSS supplémentaires pour améliorer la lisibilité
        st.markdown("""
        <style>
        table.dataframe {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        table.dataframe th {
            position: sticky;
            top: 0;
            z-index: 10;
            box-shadow: 0 2px 2px -1px rgba(0, 0, 0, 0.4);
        }
        table.dataframe td, table.dataframe th {
            border: 1px solid #3A3F44;
            padding: 8px 10px;
        }
        /* Améliorer le contraste pour les valeurs négatives */
        .negative {
            color: #FF6B6B !important;
            font-weight: bold;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Afficher le tableau avec style amélioré
        st.write(html_table, unsafe_allow_html=True)

    # Visualisations
    tab1, tab2 = st.tabs(["Évolution du CA", "Analyse des Résultats"])
    
    with tab1:
        fig = px.line(df, x="Année", y="Chiffre d'affaires",
                     title=f"Projection du Chiffre d'Affaires<br><sup>Croissance: N→N+1 {st.session_state.income_statement_params['growth_n']:.1%} | N+1→N+2 {st.session_state.income_statement_params['growth_n1']:.1%}</sup>",
                     markers=True)
        fig.update_layout(
            yaxis_title="DHS",
            hovermode="x unified",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0.05)',
            font_color='white',
            yaxis=dict(
                gridcolor='rgba(255,255,255,0.1)',
                zerolinecolor='rgba(255,255,255,0.2)'
            )
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # Transformer les données pour un meilleur affichage avec Plotly
        plot_data = pd.melt(
            df, 
            id_vars=["Année"], 
            value_vars=["Résultat d'exploitation", "Résultat net"],
            var_name="Indicateur",
            value_name="Montant"
        )
        
        fig = px.bar(
            plot_data,
            x="Année",
            y="Montant",
            color="Indicateur",
            barmode='group',
            title="Analyse des Résultats",
            labels={"Montant": "DHS"},
            color_discrete_map={
                "Résultat d'exploitation": "#36A2EB",
                "Résultat net": "#4BC0C0"
            }
        )
        
        # Amélioration des paramètres visuels du graphique
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0.05)',
            font_color='white',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                bgcolor='rgba(0,0,0,0.2)'
            ),
            yaxis=dict(
                gridcolor='rgba(255,255,255,0.1)',
                zerolinecolor='rgba(255,255,255,0.2)'
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)

    # Indicateurs Clés
    st.subheader("📌 Indicateurs Clés")
    kpi1, kpi2, kpi3 = st.columns(3)
    
    with kpi1:
        avg_growth = (ca_projections[-1]/ca_projections[0])**(1/2) - 1
        st.metric("Croissance Annuelle Moyenne", f"{avg_growth:.1%}")
    
    with kpi2:
        avg_margin = np.mean([net/ca for net, ca in zip(net_results, ca_projections)])
        st.metric("Marge Nette Moyenne", f"{avg_margin:.1%}")
    
    with kpi3:
        financial_leverage = financial_charges / np.mean(ca_projections)
        st.metric("Taux d'Endettement", f"{financial_leverage:.1%}")

    # Export des données
    st.download_button(
        label="💾 Exporter en Excel",
        data=df.to_csv(index=False, sep=";", decimal=",").encode('utf-8'),
        file_name="compte_resultat_previsionnel.csv",
        mime="text/csv",
        help="Exportez les données au format CSV pour Excel"
    )
# ========== CASH FLOW ==========
def show_cash_flow():
    st.header("💰 Tableau de Flux de Trésorerie")

    # Section 1: Configuration
    with st.expander("⚙️ Paramètres généraux", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.cash_flow_params['taux_actualisation'] = st.number_input(
                "Taux d'actualisation (%)", 
                value=float(st.session_state.cash_flow_params['taux_actualisation'] * 100), 
                min_value=0.0, 
                max_value=20.0, 
                step=0.5
            ) / 100
        with col2:
            st.session_state.cash_flow_params['annees_projection'] = st.number_input(
                "Nombre d'années à projeter", 
                value=st.session_state.cash_flow_params['annees_projection'], 
                min_value=1, 
                max_value=5
            )

    # Section 2: Frais préliminaires
    with st.expander("📝 Frais préliminaires", expanded=True):
        # Utiliser un data_editor pour tous les frais préliminaires
        df_frais = pd.DataFrame(st.session_state.frais_preliminaires)
        
        edited_df_frais = st.data_editor(
            df_frais,
            column_config={
                "nom": "Description",
                "valeur": st.column_config.NumberColumn("Montant (DHS)", format="%.2f")
            },
            hide_index=True,
            num_rows="dynamic",
            key="editor_frais_prelim"
        )
        
        # Mettre à jour les données de session
        st.session_state.frais_preliminaires = edited_df_frais.to_dict('records')
        
        total_frais = edited_df_frais["valeur"].sum()
        st.metric("Total Frais Préliminaires", f"{total_frais:,.2f} DHS")

        # Synchroniser avec les valeurs de la page Investissements
        if total_frais > 0:
            st.session_state.calculated_data['total_frais'] = total_frais

    # Section 3: Investissements
    with st.expander("🏗️ Investissements initiaux", expanded=True):
        systeme_info = st.number_input(
            "Coût du système d'information (DHS)", 
            value=st.session_state.investment_data['web_dev'], 
            min_value=0.0, 
            step=1000.0
        )
        st.session_state.investment_data['web_dev'] = systeme_info
        
        total_immos = st.session_state.calculated_data.get('total_immos', 0.0)
        st.metric("Total Immobilisations", f"{total_immos:,.2f} DHS")

    # Section 4: Financement
    with st.expander("💵 Financement", expanded=True):
        cash_contrib = st.session_state.investment_data.get('cash_contribution', 50511.31)
        in_kind = st.session_state.investment_data.get('in_kind', 20000.0)
        subventions = st.session_state.calculated_data.get('total_subsidies', 0.0)
        emprunts = st.session_state.calculated_data.get('total_credits', 0.0)
        
        cols = st.columns(4)
        cols[0].metric("Apport numéraire", f"{cash_contrib:,.2f} DHS")
        cols[1].metric("Apport en nature", f"{in_kind:,.2f} DHS") 
        cols[2].metric("Subventions", f"{subventions:,.2f} DHS")
        cols[3].metric("Emprunts", f"{emprunts:,.2f} DHS")

    # Section 5: Calcul des flux
    years = ["N"] + [f"N+{i+1}" for i in range(st.session_state.cash_flow_params['annees_projection'])]
    
    # Fonction de conversion sécurisée en float
    def safe_float_convert(x):
        try:
            return float(x)
        except (ValueError, TypeError):
            return 0.0

    flux_investissement = pd.DataFrame({
        "Année": years,
        "Frais préliminaires": [safe_float_convert(-total_frais)] + [0.0] * st.session_state.cash_flow_params['annees_projection'],
        "Immobilisations": [safe_float_convert(-total_immos)] + [0.0] * st.session_state.cash_flow_params['annees_projection'],
        "Système d'info": [safe_float_convert(-systeme_info)] + [0.0] * st.session_state.cash_flow_params['annees_projection']
    })

    flux_financement = pd.DataFrame({
        "Année": years,
        "Apports": [safe_float_convert(cash_contrib + in_kind)] + [0.0] * st.session_state.cash_flow_params['annees_projection'],
        "Subventions": [safe_float_convert(subventions)] + [0.0] * st.session_state.cash_flow_params['annees_projection'],
        "Emprunts": [safe_float_convert(emprunts)] + [0.0] * st.session_state.cash_flow_params['annees_projection']
    })

    # Utiliser les données du compte de résultat si disponibles
    if 'income_statement' in st.session_state:
        ca = st.session_state.income_statement.get("Chiffre d'affaires", [])
        charges = st.session_state.income_statement.get("Charges d'exploitation", [])
        
        # S'assurer que les listes ont la bonne longueur
        while len(ca) < len(years):
            last_value = ca[-1] if ca else 150000
            growth = st.session_state.income_statement_params.get('growth_n1', 0.2)
            ca.append(last_value * (1 + growth))
        
        while len(charges) < len(years):
            last_value = charges[-1] if charges else 120000
            efficiency = st.session_state.income_statement_params.get('efficiency_improvement', 0.02)
            charges.append(last_value * (1 - efficiency))
        
        # Tronquer si nécessaire
        ca = ca[:len(years)]
        charges = charges[:len(years)]
    else:
        ca = [safe_float_convert(150000 * (1.2**i)) for i in range(len(years))]
        charges = [safe_float_convert(ca[i] * 0.8 * (0.98**i)) for i in range(len(years))]

    # Calculer les amortissements sur 5 ans pour les immobilisations et le système d'info
    amort_annual = (total_immos + systeme_info) / 5
    amortissements = [safe_float_convert(amort_annual)] * len(years)
    
    flux_exploitation = pd.DataFrame({
        "Année": years,
        "CA": ca,
        "Charges (hors amort.)": [safe_float_convert(ch - amort) for ch, amort in zip(charges, amortissements)],
        "Amortissements": [safe_float_convert(amort) for amort in amortissements],
        "IS": [safe_float_convert(-max(0, (ca[i] - charges[i])) * 0.15) for i in range(len(years))]
    })

    # Fusion des données
    df = pd.DataFrame({"Année": years})
    df["Investissements"] = flux_investissement.drop("Année", axis=1).sum(axis=1)
    df["Financement"] = flux_financement.drop("Année", axis=1).sum(axis=1)
    df["Exploitation"] = flux_exploitation.drop("Année", axis=1).sum(axis=1)
    df["Flux Nets"] = df["Investissements"] + df["Financement"] + df["Exploitation"]
    df["Flux Cumulés"] = df["Flux Nets"].cumsum()
    df["Flux Actualisés"] = df["Flux Nets"] / (1 + st.session_state.cash_flow_params['taux_actualisation'])**np.arange(len(years))
    
    # Section 6: Affichage avec formatage sécurisé
    st.subheader("📊 Synthèse des flux de trésorerie")
    
    def safe_format_df(df):
        """Formatage sécurisé des DataFrames"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        styled = df.style.format({col: "{:,.2f}" for col in numeric_cols})
        return styled
    
    st.dataframe(safe_format_df(df), use_container_width=True)
    
    # Visualisation
    fig = px.area(df, x="Année", y="Flux Cumulés", title="Évolution de la trésorerie")
    st.plotly_chart(fig, use_container_width=True)
    
    # Indicateurs
    st.subheader("📈 Indicateurs clés")
    van = safe_float_convert(df["Flux Actualisés"].sum())
    try:
        # Supprimer le premier flux si nécessaire pour le calcul du TRI
        flux_tri = df["Flux Nets"].values
        if len(flux_tri) > 1:  # S'assurer qu'il y a assez de flux
            tri = safe_float_convert(npf.irr(flux_tri)) * 100
        else:
            tri = 0.0
    except:
        tri = 0.0
    
    # Trouver l'année de retour sur investissement
    try:
        payback_year = next((i for i, val in enumerate(df['Flux Cumulés']) if val >= 0), None)
        if payback_year is not None:
            payback = f"{years[payback_year]}"
        else:
            payback = "Non atteint"
    except:
        payback = "Non calculé"
    
    cols = st.columns(3)
    cols[0].metric("VAN", f"{van:,.2f} DHS")
    cols[1].metric("TRI", f"{tri:.1f}%")
    cols[2].metric("Délai de récupération", payback)

    # Détails par catégorie
    with st.expander("🔍 Détails par catégorie"):
        tab1, tab2, tab3 = st.tabs(["Investissements", "Financement", "Exploitation"])
        with tab1:
            st.dataframe(safe_format_df(flux_investissement), use_container_width=True)
        with tab2:
            st.dataframe(safe_format_df(flux_financement), use_container_width=True)
        with tab3:
            st.dataframe(safe_format_df(flux_exploitation), use_container_width=True)
    
    # Export
    st.download_button(
        "📤 Exporter en CSV", 
        df.to_csv(index=False), 
        "flux_tresorerie.csv",
        help="Télécharger le tableau de flux en format CSV"
    )

# ========== AMORTISSEMENTS (suite) ==========
def show_amortization():
    st.header("Tableau d'Amortissement du Crédit")
    
    if not st.session_state.credits:
        st.warning("⚠️ Aucun crédit n'a été ajouté dans la section Investissements")
        st.info("👉 Allez dans la section 'Investissements' pour ajouter des crédits")
        return
    
    credit_choice = st.selectbox(
        "Sélectionnez un crédit à amortir",
        options=[credit["Nom"] for credit in st.session_state.credits],
        key="credit_choice_select"
    )
    
    selected_credit = next(
        (credit for credit in st.session_state.credits if credit["Nom"] == credit_choice),
        None
    )
    
    if selected_credit:
        principal = float(selected_credit["Montant"])
        rate = float(selected_credit["Taux"])
        term = int(selected_credit["Durée"])
        
        # Paramètres supplémentaires
        col1, col2 = st.columns(2)
        with col1:
            frequency = st.selectbox(
                "Fréquence de remboursement", 
                ["Mensuelle", "Trimestrielle", "Semestrielle", "Annuelle"],
                index=0
            )
        
        with col2:
            grace_period = st.number_input(
                "Période de grâce (mois)", 
                min_value=0, 
                max_value=24, 
                value=0
            )
        
        # Ajuster selon la fréquence
        periods_per_year = {
            "Mensuelle": 12,
            "Trimestrielle": 4,
            "Semestrielle": 2,
            "Annuelle": 1
        }
        
        periods = term * periods_per_year[frequency]
        periodic_rate = rate / periods_per_year[frequency]
        
        if principal > 0 and rate > 0 and term > 0:
            if grace_period > 0:
                st.info(f"Pendant la période de grâce de {grace_period} mois, seuls les intérêts sont payés.")
            
            payment = principal * (periodic_rate * (1 + periodic_rate)**(periods)) / ((1 + periodic_rate)**(periods) - 1)
            
            schedule = []
            balance = principal
            total_interest = 0
            
            # Période de grâce (intérêts seulement)
            for month in range(1, grace_period + 1):
                interest = balance * (rate / 12)  # Intérêts mensuels durant la grâce
                total_interest += interest
                schedule.append([
                    month, 
                    interest,  # Paiement = intérêts seulement
                    0.0,       # Pas d'amortissement du principal
                    interest,  # Intérêts
                    balance    # Solde inchangé
                ])
            
            # Remboursement normal après la période de grâce
            for period in range(periods):
                month = grace_period + 1 + period
                interest = balance * periodic_rate
                principal_payment = payment - interest
                balance -= principal_payment
                total_interest += interest
                
                schedule.append([
                    month,
                    payment,
                    principal_payment,
                    interest,
                    max(0.0, balance)
                ])
            
            # Création du DataFrame
            df = pd.DataFrame(schedule, columns=["Période", "Paiement", "Capital", "Intérêts", "Solde"])
            
            # Ajout de colonnes supplémentaires pour l'année et le trimestre
            if frequency == "Mensuelle":
                df["Année"] = (df["Période"] - 1) // 12 + 1
                df["Trimestre"] = ((df["Période"] - 1) % 12) // 3 + 1
            
            # Résumé avant le tableau
            st.subheader("Résumé du crédit")
            col1, col2, col3 = st.columns(3)
            col1.metric("Capital emprunté", f"{principal:,.2f} DHS")
            col2.metric("Total des intérêts", f"{total_interest:,.2f} DHS")
            col3.metric("Coût total", f"{(principal + total_interest):,.2f} DHS")
            
            # Afficher le tableau d'amortissement
            st.subheader("Tableau d'amortissement")
            
            # Options d'affichage
            display_options = st.radio(
                "Options d'affichage",
                ["Détail complet", "Résumé annuel"],
                horizontal=True
            )
            
            if display_options == "Résumé annuel" and frequency == "Mensuelle":
                # Créer un résumé annuel
                annual_summary = df.groupby("Année").agg({
                    "Paiement": "sum",
                    "Capital": "sum",
                    "Intérêts": "sum"
                }).reset_index()
                
                annual_summary["Solde fin d'année"] = principal - annual_summary["Capital"].cumsum()
                
                st.dataframe(
                    annual_summary.style.format({
                        "Paiement": "{:,.2f}",
                        "Capital": "{:,.2f}",
                        "Intérêts": "{:,.2f}",
                        "Solde fin d'année": "{:,.2f}"
                    }),
                    use_container_width=True
                )
            else:
                # Afficher les 12 premiers mois par défaut
                rows_to_show = st.slider("Nombre de périodes à afficher", 12, len(df), 12)
                
                st.dataframe(
                    df.head(rows_to_show).style.format({
                        "Paiement": "{:,.2f}",
                        "Capital": "{:,.2f}",
                        "Intérêts": "{:,.2f}",
                        "Solde": "{:,.2f}"
                    }),
                    use_container_width=True
                )
            
            # Visualisations
            st.subheader("Visualisations")
            tab1, tab2 = st.tabs(["Répartition Capital/Intérêts", "Évolution du solde"])
            
            with tab1:
                if frequency == "Mensuelle" and display_options == "Résumé annuel":
                    chart_data = annual_summary.melt(
                        id_vars=["Année"], 
                        value_vars=["Capital", "Intérêts"],
                        var_name="Type",
                        value_name="Montant"
                    )
                    fig = px.bar(
                        chart_data,
                        x="Année",
                        y="Montant",
                        color="Type",
                        title="Répartition annuelle Capital/Intérêts",
                        barmode="group"
                    )
                else:
                    periods_to_chart = min(60, len(df))  # Limiter à 60 périodes pour la lisibilité
                    chart_data = df.head(periods_to_chart).melt(
                        id_vars=["Période"], 
                        value_vars=["Capital", "Intérêts"],
                        var_name="Type",
                        value_name="Montant"
                    )
                    fig = px.bar(
                        chart_data,
                        x="Période",
                        y="Montant",
                        color="Type",
                        title=f"Répartition {frequency.lower()} Capital/Intérêts",
                        barmode="stack"
                    )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                fig = px.line(
                    df,
                    x="Période",
                    y="Solde",
                    title="Évolution du solde restant dû",
                    markers=True
                )
                fig.update_layout(yaxis_title="Solde (DHS)")
                st.plotly_chart(fig, use_container_width=True)

            # Export des données
            st.download_button(
                label="💾 Exporter en Excel",
                data=df.to_csv(index=False, sep=";").encode('utf-8'),
                file_name=f"tableau_amortissement_{selected_credit['Nom']}.csv",
                mime="text/csv",
                help="Exportez les données au format CSV pour Excel"
            )

# ========== AMORTISSEMENT DÉTAILLÉ ==========
def show_detailed_amortization():
    st.header("📊 Tableau d'Amortissement des Immobilisations")
    
    # Configuration et options
    with st.expander("⚙️ Configuration", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            years_to_display = st.slider("Nombre d'années à afficher", min_value=3, max_value=10, value=3)
        with col2:
            sync_immobilisations = st.checkbox("Synchroniser avec les immobilisations", value=True)
        
        if sync_immobilisations:
            # Synchroniser avec les données d'immobilisations
            if 'immos' in st.session_state and st.session_state.immos:
                # Créer une correspondance entre les noms dans le tableau d'amortissement et les immobilisations
                name_mapping = {
                    "Frais préliminaire & d'approche": ["frais", "préliminaire", "approche"],
                    "Terrain / Local": ["terrain", "local"],
                    "Construction / Aménagement": ["construction", "aménagement", "amenagement"],
                    "Matériel d'équipement": ["équipement", "equipement"],
                    "Mobilier & matériel de bureau": ["mobilier", "bureau"],
                    "Matériel de transport & manutension": ["transport", "manutention"],
                    "Système d'information": ["système", "systeme", "information", "informatique"]
                }
                
                # Parcourir les immobilisations et mettre à jour les montants
                for immo in st.session_state.immos:
                    immo_name = immo["Nom"].lower()
                    for amort_name, keywords in name_mapping.items():
                        if any(keyword in immo_name for keyword in keywords):
                            # Trouver l'indice de cette immobilisation dans le tableau d'amortissement
                            for i, item in enumerate(st.session_state.detailed_amortization):
                                if item["name"] == amort_name:
                                    # Mettre à jour le montant
                                    st.session_state.detailed_amortization[i]["amount"] = immo["Montant"]
                                    # Recalculer les amortissements
                                    rate = st.session_state.detailed_amortization[i]["rate"] / 100
                                    duration = st.session_state.detailed_amortization[i]["duration"]
                                    if duration > 0:
                                        annual_amort = immo["Montant"] * rate
                                        st.session_state.detailed_amortization[i]["amortization_n"] = annual_amort
                                        st.session_state.detailed_amortization[i]["amortization_n1"] = annual_amort
                                        st.session_state.detailed_amortization[i]["amortization_n2"] = annual_amort
                                    break
                            break
            
            # Synchroniser avec les frais préliminaires
            if 'frais_preliminaires' in st.session_state and st.session_state.frais_preliminaires:
                total_frais = sum(frais["valeur"] for frais in st.session_state.frais_preliminaires)
                for i, item in enumerate(st.session_state.detailed_amortization):
                    if item["name"] == "Frais préliminaire & d'approche":
                        st.session_state.detailed_amortization[i]["amount"] = total_frais
                        rate = st.session_state.detailed_amortization[i]["rate"] / 100
                        annual_amort = total_frais * rate
                        st.session_state.detailed_amortization[i]["amortization_n"] = annual_amort
                        st.session_state.detailed_amortization[i]["amortization_n1"] = annual_amort
                        st.session_state.detailed_amortization[i]["amortization_n2"] = annual_amort
                        break
            
            # Synchroniser avec le système d'information
            if 'investment_data' in st.session_state and 'web_dev' in st.session_state.investment_data:
                web_dev = st.session_state.investment_data['web_dev']
                for i, item in enumerate(st.session_state.detailed_amortization):
                    if item["name"] == "Système d'information":
                        st.session_state.detailed_amortization[i]["amount"] = web_dev
                        rate = st.session_state.detailed_amortization[i]["rate"] / 100
                        annual_amort = web_dev * rate
                        st.session_state.detailed_amortization[i]["amortization_n"] = annual_amort
                        st.session_state.detailed_amortization[i]["amortization_n1"] = annual_amort
                        st.session_state.detailed_amortization[i]["amortization_n2"] = annual_amort
                        break
    
    # Édition des données du tableau d'amortissement
    with st.expander("🛠️ Édition des immobilisations et taux d'amortissement", expanded=False):
        # Convertir la liste en DataFrame pour l'édition
        amort_df = pd.DataFrame(st.session_state.detailed_amortization)
        
        # Utiliser st.data_editor pour permettre l'édition
        edited_df = st.data_editor(
            amort_df,
            column_config={
                "name": st.column_config.TextColumn("Immobilisation"),
                "amount": st.column_config.NumberColumn("Montant à amortir (DHS)", format="%.2f"),
                "duration": st.column_config.NumberColumn("Durée (années)", min_value=0, max_value=50, step=1),
                "rate": st.column_config.NumberColumn("Taux (%)", min_value=0, max_value=100, step=1),
                "amortization_n": st.column_config.NumberColumn("Amortissement N (DHS)", format="%.2f"),
                "amortization_n1": st.column_config.NumberColumn("Amortissement N+1 (DHS)", format="%.2f"),
                "amortization_n2": st.column_config.NumberColumn("Amortissement N+2 (DHS)", format="%.2f")
            },
            hide_index=True,
            use_container_width=True,
            key="amort_editor"
        )
        
        # Mettre à jour les données de session avec les valeurs éditées
        st.session_state.detailed_amortization = edited_df.to_dict('records')
        
        # Option pour recalculer automatiquement les amortissements
        if st.button("Recalculer les amortissements"):
            for i, item in enumerate(st.session_state.detailed_amortization):
                if item["duration"] > 0:
                    rate = item["rate"] / 100
                    annual_amort = item["amount"] * rate
                    st.session_state.detailed_amortization[i]["amortization_n"] = annual_amort
                    st.session_state.detailed_amortization[i]["amortization_n1"] = annual_amort
                    st.session_state.detailed_amortization[i]["amortization_n2"] = annual_amort
    
    # Affichage du tableau d'amortissement
    st.subheader("Tableau d'Amortissement")
    
    # Construction des données pour l'affichage
    # Créer les colonnes pour les années
    columns = ["Immobilisation", "Montant à amortir", "Durée (année)", "Taux"]
    years = ["N", "N+1", "N+2"] + [f"N+{i}" for i in range(3, years_to_display)]
    columns.extend(years)
    columns.extend(["TOTAL", "VNA"])
    
    # Préparer les données
    data = []
    total_row = [""] * len(columns)
    total_row[0] = "TOTAL"
    
    # Initialiser les totaux par colonne
    for i in range(4, len(columns)):
        total_row[i] = 0
    
    for item in st.session_state.detailed_amortization:
        row = [
            item["name"],
            item["amount"],
            item["duration"],
            f"{item['rate']}%"
        ]
        
        # Ajouter les amortissements pour les années N, N+1, N+2
        row.append(item["amortization_n"])
        row.append(item["amortization_n1"])
        row.append(item["amortization_n2"])
        
        # Calculer les amortissements pour les années supplémentaires
        annual_amort = item["amount"] * (item["rate"] / 100) if item["duration"] > 0 else 0
        for i in range(3, years_to_display):
            if i < item["duration"]:
                row.append(annual_amort)
            else:
                row.append(0)
        
        # Calculer le total des amortissements
        total_amort = min(item["duration"], years_to_display) * annual_amort
        row.append(total_amort)
        
        # Calculer la Valeur Nette d'Amortissement (VNA)
        vna = item["amount"] - total_amort
        row.append(vna)
        
        data.append(row)
        
        # Mettre à jour les totaux
        for i in range(4, len(columns)):
            if isinstance(total_row[i], (int, float)) and isinstance(row[i], (int, float)):
                total_row[i] += row[i]
    
    # Ajouter la ligne des totaux
    data.append(total_row)
    
    # Créer le DataFrame
    df = pd.DataFrame(data, columns=columns)
    
    # Fonction pour styliser le tableau - AMÉLIORÉE POUR FOND SOMBRE
    def style_amortization_table(df):
        # Créer un formatage sécurisé qui vérifie le type avant d'appliquer le format
        formatter = {}
        for col in df.columns:
            if col not in ["Immobilisation", "Taux", "Durée (année)"]:
                formatter[col] = lambda x: "{:,.2f} MAD".format(x) if isinstance(x, (int, float)) else str(x)
        
        styler = df.style.format(formatter)
        
        # Appliquer un style spécifique à l'en-tête avec couleurs adaptées au mode sombre
        styler = styler.set_table_styles([
            {'selector': 'thead th', 'props': [('background-color', '#1e3a8a'), ('color', 'white'), ('font-weight', 'bold')]},
        ])
        
        # Utiliser des couleurs plus sombres mais contrastées pour les lignes alternées
        even_rows = list(range(0, len(df), 2))
        odd_rows = list(range(1, len(df), 2))
        
        # Lignes paires - couleur plus foncée mais visible
        styler = styler.set_properties(subset=pd.IndexSlice[even_rows, :], 
                                    **{'background-color': '#2d3748', 'color': 'white'})
        
        # Lignes impaires - couleur légèrement différente pour le contraste
        styler = styler.set_properties(subset=pd.IndexSlice[odd_rows, :], 
                                    **{'background-color': '#1f2937', 'color': 'white'})
        
        # Mettre en évidence la ligne des totaux avec une couleur plus vive
        if len(df) > 0:
            styler = styler.set_properties(subset=pd.IndexSlice[len(df)-1, :], 
                                       **{'background-color': '#3b82f6', 'color': 'white', 'font-weight': 'bold'})
        
        # Mettre en évidence les valeurs négatives avec une couleur visible sur fond sombre
        def color_negative(val):
            if isinstance(val, (int, float)) and val < 0:
                return 'color: #f87171'  # Rouge clair visible sur fond sombre
            return ''
        
        styler = styler.applymap(color_negative)
        
        return styler
    
    # Afficher le tableau avec le style amélioré pour fond sombre
    st.dataframe(style_amortization_table(df), use_container_width=True, height=400)
    
    # Visualisations
    st.subheader("Analyse des Amortissements")
    
    tab1, tab2 = st.tabs(["Répartition des amortissements", "Évolution par année"])
    
    with tab1:
        # Préparer les données pour le graphique de répartition
        immobilisations = [item["name"] for item in st.session_state.detailed_amortization if item["amount"] > 0]
        amounts = [item["amount"] for item in st.session_state.detailed_amortization if item["amount"] > 0]
        
        if amounts:  # Vérification pour éviter les erreurs avec graphique vide
            fig = px.pie(
                names=immobilisations,
                values=amounts,
                title="Répartition des Immobilisations par Montant",
                # Paramètres supplémentaires pour améliorer la visibilité sur fond sombre
                color_discrete_sequence=px.colors.qualitative.Set2  # Palette plus visible
            )
            fig.update_traces(textposition='inside', textinfo='percent+label', textfont_color='white')
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',  # Fond transparent
                plot_bgcolor='rgba(0,0,0,0)',   # Fond transparent
                font_color='white'              # Texte blanc
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune immobilisation à afficher dans le graphique.")
    
    with tab2:
        # Préparer les données pour le graphique d'évolution
        yearly_data = {
            'Année': years,
        }
        
        has_data = False
        for item in st.session_state.detailed_amortization:
            if item["amount"] > 0:
                has_data = True
                yearly_amort = []
                yearly_amort.append(item["amortization_n"])
                yearly_amort.append(item["amortization_n1"])
                yearly_amort.append(item["amortization_n2"])
                
                annual_amort = item["amount"] * (item["rate"] / 100) if item["duration"] > 0 else 0
                for i in range(3, years_to_display):
                    if i < item["duration"]:
                        yearly_amort.append(annual_amort)
                    else:
                        yearly_amort.append(0)
                
                yearly_data[item["name"]] = yearly_amort
        
        if has_data:
            # Créer le DataFrame pour le graphique
            yearly_df = pd.DataFrame(yearly_data)
            
            # Transformer pour Plotly
            yearly_df_melted = yearly_df.melt(id_vars=['Année'], var_name='Immobilisation', value_name='Amortissement')
            
            fig = px.bar(
                yearly_df_melted,
                x='Année',
                y='Amortissement',
                color='Immobilisation',
                title="Évolution des Amortissements par Année",
                labels={'Amortissement': 'Montant (DHS)'},
                # Paramètres supplémentaires pour améliorer la visibilité sur fond sombre
                color_discrete_sequence=px.colors.qualitative.Bold  # Palette vive
            )
            fig.update_layout(
                barmode='stack', 
                xaxis={'categoryorder': 'array', 'categoryarray': years},
                paper_bgcolor='rgba(0,0,0,0)',  # Fond transparent
                plot_bgcolor='rgba(0,0,0,0)',   # Fond transparent
                font_color='white'              # Texte blanc
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnée à afficher dans le graphique d'évolution.")
    
    # Synthèse
    st.subheader("Synthèse des Amortissements")
    
    col1, col2, col3 = st.columns(3)
    
    total_investment = sum(item["amount"] for item in st.session_state.detailed_amortization)
    with col1:
        st.metric("Total des Immobilisations", f"{total_investment:,.2f} DHS")
    
    with col2:
        total_annual_amort = sum(item["amortization_n"] for item in st.session_state.detailed_amortization)
        st.metric("Dotation Annuelle aux Amortissements", f"{total_annual_amort:,.2f} DHS")
    
    with col3:
        avg_duration = sum(item["amount"] * item["duration"] for item in st.session_state.detailed_amortization if item["amount"] > 0) / total_investment if total_investment > 0 else 0
        st.metric("Durée Moyenne d'Amortissement", f"{avg_duration:.1f} ans")
    
    # Export des données
    st.download_button(
        "💾 Exporter le tableau d'amortissement",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name="tableau_amortissement_immobilisations.csv",
        mime="text/csv",
        help="Télécharger le tableau au format CSV"
    )

# ========== TABLEAU DE TRÉSORERIE MENSUEL ==========
def show_monthly_cashflow():
    st.header("📊 Tableau de Trésorerie Mensuel")
    
    # Configuration du tableau
    with st.expander("⚙️ Configuration du tableau", expanded=True):
        num_months = st.slider("Nombre de mois à afficher", 
                             min_value=3, 
                             max_value=12, 
                             value=12)
        
        # Option pour charger des données à partir des autres onglets
        sync_data = st.checkbox("Synchroniser avec les données des autres onglets", value=True)
        
        if sync_data and 'calculated_data' in st.session_state:
            # Synchronisation avec les données existantes
            if 'total_credits' in st.session_state.calculated_data:
                st.session_state.monthly_cashflow_data['ressources']['Emprunts'] = st.session_state.calculated_data['total_credits']
            
            if 'total_subsidies' in st.session_state.calculated_data:
                st.session_state.monthly_cashflow_data['ressources']['Subventions'] = st.session_state.calculated_data['total_subsidies']
            
            # Synchroniser les apports
            if 'investment_data' in st.session_state:
                apports = st.session_state.investment_data.get('cash_contribution', 50511.31) + st.session_state.investment_data.get('in_kind', 20000.0)
                st.session_state.monthly_cashflow_data['ressources']['Apports personnels'] = apports
            
            # Synchroniser les immobilisations
            if 'total_immos' in st.session_state.calculated_data:
                st.session_state.monthly_cashflow_data['immobilisations']['Immobilisations corporelles'] = st.session_state.calculated_data['total_immos']
            
            if 'web_dev' in st.session_state.investment_data:
                st.session_state.monthly_cashflow_data['immobilisations']['Immobilisations incorporelles'] = st.session_state.investment_data['web_dev']

    # Édition des valeurs du tableau
    with st.expander("🛠️ Édition des données", expanded=False):
        st.subheader("Ressources")
        resources_df = pd.DataFrame({
            'Élément': list(st.session_state.monthly_cashflow_data['ressources'].keys()),
            'Valeur': list(st.session_state.monthly_cashflow_data['ressources'].values())
        })
        
        edited_resources = st.data_editor(
            resources_df,
            column_config={
                "Élément": st.column_config.TextColumn("Élément"),
                "Valeur": st.column_config.NumberColumn("Valeur (DHS)", format="%.2f")
            },
            num_rows="dynamic",
            hide_index=True,
            key="resources_editor"
        )
        
        # Mettre à jour les ressources
        st.session_state.monthly_cashflow_data['ressources'] = {row['Élément']: row['Valeur'] for _, row in edited_resources.iterrows()}
        
        st.subheader("Chiffre d'affaires")
        ca_df = pd.DataFrame({
            'Élément': list(st.session_state.monthly_cashflow_data['chiffre_affaires'].keys()),
            'Valeur': list(st.session_state.monthly_cashflow_data['chiffre_affaires'].values())
        })
        
        edited_ca = st.data_editor(
            ca_df,
            column_config={
                "Élément": st.column_config.TextColumn("Élément"),
                "Valeur": st.column_config.NumberColumn("Valeur mensuelle (DHS)", format="%.2f")
            },
            num_rows="dynamic",
            hide_index=True,
            key="ca_editor"
        )
        
        # Mettre à jour le CA
        st.session_state.monthly_cashflow_data['chiffre_affaires'] = {row['Élément']: row['Valeur'] for _, row in edited_ca.iterrows()}
        
        st.subheader("Immobilisations")
        immo_df = pd.DataFrame({
            'Élément': list(st.session_state.monthly_cashflow_data['immobilisations'].keys()),
            'Valeur': list(st.session_state.monthly_cashflow_data['immobilisations'].values())
        })
        
        edited_immo = st.data_editor(
            immo_df,
            column_config={
                "Élément": st.column_config.TextColumn("Élément"),
                "Valeur": st.column_config.NumberColumn("Valeur (DHS)", format="%.2f")
            },
            num_rows="dynamic",
            hide_index=True,
            key="immo_editor"
        )
        
        # Mettre à jour les immobilisations
        st.session_state.monthly_cashflow_data['immobilisations'] = {row['Élément']: row['Valeur'] for _, row in edited_immo.iterrows()}
        
        st.subheader("Charges d'exploitation")
        charges_df = pd.DataFrame({
            'Élément': list(st.session_state.monthly_cashflow_data['charges_exploitation'].keys()),
            'Valeur': list(st.session_state.monthly_cashflow_data['charges_exploitation'].values())
        })
        
        edited_charges = st.data_editor(
            charges_df,
            column_config={
                "Élément": st.column_config.TextColumn("Élément"),
                "Valeur": st.column_config.NumberColumn("Valeur mensuelle (DHS)", format="%.2f")
            },
            num_rows="dynamic",
            hide_index=True,
            key="charges_editor"
        )
        
        # Mettre à jour les charges
        st.session_state.monthly_cashflow_data['charges_exploitation'] = {row['Élément']: row['Valeur'] for _, row in edited_charges.iterrows()}
    
    # Construction du tableau
    st.subheader("Tableau de Trésorerie Mensuel")
    
    # CORRECTION: Définir correctement le nombre de colonnes
    columns = ["ELEMENTS"] + [str(i) for i in range(1, num_months+1)]
    
    # Préparer les données
    data = []
    
    # Section Ressources
    data.append(["Ressources", sum(st.session_state.monthly_cashflow_data['ressources'].values())] + [""] * (num_months-1))
    for key, value in st.session_state.monthly_cashflow_data['ressources'].items():
        data.append(["  " + key, value] + [""] * (num_months-1))
    
    # Section Chiffre d'affaires
    total_ca_monthly = sum(st.session_state.monthly_cashflow_data['chiffre_affaires'].values())
    data.append(["Chiffre d'affaires", total_ca_monthly] + [total_ca_monthly] * (num_months-1))
    for key, value in st.session_state.monthly_cashflow_data['chiffre_affaires'].items():
        data.append(["  " + key, value] + [value] * (num_months-1))
    
    # Section Immobilisations
    data.append(["Immobilisations", sum(st.session_state.monthly_cashflow_data['immobilisations'].values())] + [""] * (num_months-1))
    for key, value in st.session_state.monthly_cashflow_data['immobilisations'].items():
        data.append(["  " + key, value] + [""] * (num_months-1))
    
    # Section Charges d'exploitation
    total_charges_monthly = sum(st.session_state.monthly_cashflow_data['charges_exploitation'].values())
    data.append(["Charges d'exploitation", total_charges_monthly] + [total_charges_monthly] * (num_months-1))
    for key, value in st.session_state.monthly_cashflow_data['charges_exploitation'].items():
        data.append(["  " + key, value] + [value] * (num_months-1))
    
    # Calcul des totaux
    total_encaissement = total_ca_monthly
    data.append(["Total encaissement", total_encaissement] + [total_encaissement] * (num_months-1))
    
    total_decaissement = total_charges_monthly
    data.append(["Total décaissement", total_decaissement] + [total_decaissement] * (num_months-1))
    
    # Calcul du solde de trésorerie
    solde_initial = sum(st.session_state.monthly_cashflow_data['ressources'].values()) - sum(st.session_state.monthly_cashflow_data['immobilisations'].values())
    soldes = [solde_initial]
    
    for i in range(num_months):
        if i == 0:
            current_solde = solde_initial
        else:
            current_solde = soldes[-1]
        
        monthly_balance = total_encaissement - total_decaissement
        solde_month = current_solde + monthly_balance
        soldes.append(solde_month)
    
    # CORRECTION: Assurer que chaque ligne ait exactement le même nombre de colonnes que défini
    data.append(["Solde de trésorerie"] + soldes)  # Une colonne pour ELEMENTS + num_months colonnes pour les soldes
    data.append(["  Solde précédent"] + [""] + soldes[:-1])  # Une colonne vide + num_months colonnes pour les soldes précédents
    data.append(["  Solde du mois"] + [monthly_balance] * (num_months + 1))  # num_months + 1 colonnes pour les soldes mensuels
    
    # CORRECTION: Uniformiser la longueur de chaque ligne
    for i, row in enumerate(data):
        if len(row) > len(columns):
            # Tronquer si trop longue
            data[i] = row[:len(columns)]
        elif len(row) < len(columns):
            # Ajouter des valeurs vides si trop courte
            data[i] = row + [""] * (len(columns) - len(row))
    
    # Créer le DataFrame avec le nombre correct de colonnes
    df = pd.DataFrame(data, columns=columns)
    
    # Styliser le tableau - Adapté pour le thème sombre
    def style_cashflow_table(df):
        # Créer un style par défaut avec format de nombre sécurisé
        formatter = {}
        for col in df.columns:
            if col != "ELEMENTS":
                formatter[col] = lambda x: "{:,.2f}".format(x) if isinstance(x, (int, float)) else str(x)
        
        styler = df.style.format(formatter)
        
        # Style adapté au mode sombre
        styler = styler.set_table_styles([
            {'selector': 'thead th', 'props': [('background-color', '#1e3a8a'), ('color', 'white'), ('font-weight', 'bold')]},
        ])
        
        # Définir les couleurs de fond pour les catégories principales
        category_rows = df[df["ELEMENTS"].str.strip() == df["ELEMENTS"]].index
        subcategory_rows = df[df["ELEMENTS"].str.startswith("  ")].index
        
        # Appliquer un style pour les en-têtes de catégorie
        for row in category_rows:
            styler = styler.set_properties(subset=pd.IndexSlice[row, :], 
                                         **{'background-color': '#2d3748', 'color': 'white', 'font-weight': 'bold'})
        
        # Appliquer un style pour les sous-catégories
        for row in subcategory_rows:
            styler = styler.set_properties(subset=pd.IndexSlice[row, :], 
                                         **{'background-color': '#1f2937', 'color': 'white', 'font-style': 'italic'})
        
        # Mettre en évidence les totaux et soldes
        total_rows = df[df["ELEMENTS"].isin(["Total encaissement", "Total décaissement", "Solde de trésorerie"])].index
        for row in total_rows:
            styler = styler.set_properties(subset=pd.IndexSlice[row, :], 
                                         **{'background-color': '#3b82f6', 'color': 'white', 'font-weight': 'bold'})
        
        # Colorer les valeurs négatives
        def color_negative(val):
            if isinstance(val, (int, float)) and val < 0:
                return 'color: #f87171'  # Rouge clair pour les valeurs négatives
            return ''
        
        styler = styler.applymap(color_negative)
        
        return styler
    
    # Afficher le tableau avec style
    st.dataframe(style_cashflow_table(df), use_container_width=True, height=600)
    
    # Visualisation des soldes de trésorerie
    st.subheader("Évolution du Solde de Trésorerie")
    
    chart_data = pd.DataFrame({
        'Mois': range(1, num_months+1),
        'Solde': soldes[1:num_months+1]  # Utiliser seulement les soldes nécessaires
    })
    
    fig = px.line(chart_data, x='Mois', y='Solde', markers=True)
    fig.update_layout(
        title="Évolution du solde de trésorerie sur la période",
        xaxis_title="Mois",
        yaxis_title="Solde (DHS)",
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',  # Fond transparent
        plot_bgcolor='rgba(0,0,0,0)',   # Fond transparent
        font_color='white'              # Texte blanc pour meilleure lisibilité
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Résumé financier
    st.subheader("Indicateurs Clés")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Solde final", 
            f"{soldes[-1]:,.2f} DHS",
            f"{soldes[-1] - soldes[0]:+,.2f} DHS"
        )
    
    with col2:
        monthly_change = sum(soldes) / len(soldes) - soldes[0]
        st.metric(
            "Variation mensuelle moyenne", 
            f"{monthly_change:,.2f} DHS"
        )
    
    with col3:
        months_positive = sum(1 for solde in soldes if solde > 0)
        st.metric(
            "Mois avec solde positif",
            f"{months_positive}/{len(soldes)}"
        )
    
    # Export des données
    st.download_button(
        "💾 Exporter ce tableau",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name="tableau_tresorerie_mensuel.csv",
        mime="text/csv",
        help="Télécharger le tableau au format CSV"
    )

# ========== BUDGET TVA ==========
def show_vat_budget():
    st.header("💵 Budget des Achats, Ventes et TVA")
    
    # Configuration du tableau
    with st.expander("⚙️ Configuration", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            num_months = st.slider("Nombre de mois à afficher", 
                                min_value=3, 
                                max_value=12, 
                                value=12)
        
        with col2:
            tva_rate = st.slider("Taux de TVA (%)", 
                                min_value=0, 
                                max_value=30, 
                                value=20)
            
        # Option pour synchroniser les données
        sync_data = st.checkbox("Synchroniser avec les données des autres onglets", value=True)
        
        if sync_data and 'income_statement' in st.session_state:
            if 'Chiffre d\'affaires' in st.session_state.income_statement and len(st.session_state.income_statement['Chiffre d\'affaires']) > 0:
                ca_mensuel = st.session_state.income_statement['Chiffre d\'affaires'][0] / 12
                st.session_state.vat_budget_data['ventes']['Vente en HT'] = ca_mensuel
                st.session_state.vat_budget_data['ventes']['TVA collecte sur vente'] = ca_mensuel * (tva_rate / 100)
    
    # Édition des valeurs du budget
    with st.expander("🛠️ Édition des données", expanded=False):
        st.subheader("Budget des achats")
        achats_df = pd.DataFrame({
            'Élément': list(st.session_state.vat_budget_data['achats'].keys()),
            'Valeur': list(st.session_state.vat_budget_data['achats'].values())
        })
        
        edited_achats = st.data_editor(
            achats_df,
            column_config={
                "Élément": st.column_config.TextColumn("Élément"),
                "Valeur": st.column_config.NumberColumn("Valeur mensuelle (DHS)", format="%.2f")
            },
            num_rows="dynamic",
            hide_index=True,
            key="achats_editor"
        )
        
        # Mettre à jour les achats
        st.session_state.vat_budget_data['achats'] = {row['Élément']: row['Valeur'] for _, row in edited_achats.iterrows()}
        
        st.subheader("Budget des ventes")
        ventes_df = pd.DataFrame({
            'Élément': list(st.session_state.vat_budget_data['ventes'].keys()),
            'Valeur': list(st.session_state.vat_budget_data['ventes'].values())
        })
        
        edited_ventes = st.data_editor(
            ventes_df,
            column_config={
                "Élément": st.column_config.TextColumn("Élément"),
                "Valeur": st.column_config.NumberColumn("Valeur mensuelle (DHS)", format="%.2f")
            },
            num_rows="dynamic",
            hide_index=True,
            key="ventes_editor"
        )
        
        # Mettre à jour les ventes
        st.session_state.vat_budget_data['ventes'] = {row['Élément']: row['Valeur'] for _, row in edited_ventes.iterrows()}
        
        st.subheader("TVA sur immobilisations")
        
        # Vérification que le dictionnaire existe bien
        if 'tva_immobilisations' not in st.session_state.vat_budget_data or st.session_state.vat_budget_data['tva_immobilisations'] is None:
            st.session_state.vat_budget_data['tva_immobilisations'] = {"TVA dedustible sur immobilisation": 36628.00}
        
        tva_immo_df = pd.DataFrame({
            'Élément': list(st.session_state.vat_budget_data['tva_immobilisations'].keys()),
            'Valeur': list(st.session_state.vat_budget_data['tva_immobilisations'].values())
        })
        
        edited_tva_immo = st.data_editor(
            tva_immo_df,
            column_config={
                "Élément": st.column_config.TextColumn("Élément"),
                "Valeur": st.column_config.NumberColumn("Valeur (DHS)", format="%.2f")
            },
            num_rows="dynamic",
            hide_index=True,
            key="tva_immo_editor"
        )
        
        # Mettre à jour la TVA sur immobilisations
        st.session_state.vat_budget_data['tva_immobilisations'] = {row['Élément']: row['Valeur'] for _, row in edited_tva_immo.iterrows()}
    
        # Option pour calculer automatiquement la TVA
        auto_calculate = st.checkbox("Calculer automatiquement la TVA", value=True)
        
        if auto_calculate:
            # Mettre à jour les valeurs de TVA basées sur le taux
            for key, value in st.session_state.vat_budget_data['achats'].items():
                if key == 'TVA déductible sur achat':
                    ht_value = st.session_state.vat_budget_data['achats'].get('Achat HT', 0)
                    st.session_state.vat_budget_data['achats'][key] = ht_value * (tva_rate / 100)
            
            for key, value in st.session_state.vat_budget_data['ventes'].items():
                if key == 'TVA collecte sur vente':
                    ht_value = st.session_state.vat_budget_data['ventes'].get('Vente en HT', 0)
                    st.session_state.vat_budget_data['ventes'][key] = ht_value * (tva_rate / 100)
    
    # Construction du tableau
    st.subheader("Tableau Budget TVA")
    
    # Créer les colonnes du tableau
    columns = ["ELEMENTS"] + [str(i) for i in range(1, num_months+1)]
    
    # Préparer les données
    data = []
    
    # Budget des achats
    data.append(["Budget des achats"] + [""] * num_months)
    for key, value in st.session_state.vat_budget_data['achats'].items():
        data.append(["  " + key, value] + [value] * (num_months-1))
    
    # Budget des ventes
    data.append(["Budget des vente"] + [""] * num_months)
    for key, value in st.session_state.vat_budget_data['ventes'].items():
        data.append(["  " + key, value] + [value] * (num_months-1))
    
    # Budget de la TVA
    data.append(["Budget de la TVA"] + [""] * num_months)
    
    # TVA collectée
    tva_collectee = st.session_state.vat_budget_data['ventes'].get('TVA collecte sur vente', 0)
    data.append(["  TVA collecte", tva_collectee] + [tva_collectee] * (num_months-1))
    
    # TVA déductible sur achat
    tva_deductible = st.session_state.vat_budget_data['achats'].get('TVA déductible sur achat', 0)
    data.append(["  TVA déductible sur Achat", tva_deductible] + [tva_deductible] * (num_months-1))
    
    # TVA sur immobilisations (uniquement pour le premier mois) avec vérification
    tva_immo = 0.0
    if 'tva_immobilisations' in st.session_state.vat_budget_data and st.session_state.vat_budget_data['tva_immobilisations']:
        values_list = list(st.session_state.vat_budget_data['tva_immobilisations'].values())
        if values_list:
            tva_immo = values_list[0]
    
    data.append(["  TVA dedustible sur immobilisation", tva_immo] + [0] * (num_months-1))
    
    # Calcul de la TVA nette due
    tva_nette_first_month = tva_collectee - tva_deductible - tva_immo
    tva_nette_other_months = tva_collectee - tva_deductible
    
    data.append(["TVA NETTE DUE", tva_nette_first_month] + [tva_nette_other_months] * (num_months-1))
    
    # Uniformiser la longueur des lignes
    for i, row in enumerate(data):
        if len(row) > len(columns):
            data[i] = row[:len(columns)]
        elif len(row) < len(columns):
            data[i] = row + [""] * (len(columns) - len(row))
    
    # Créer le DataFrame
    df = pd.DataFrame(data, columns=columns)
    
    # Styliser le tableau - AMÉLIORÉ pour meilleure lisibilité sur fond sombre
    def style_vat_table(df):
        # Créer un style par défaut avec format de nombre sécurisé
        formatter = {}
        for col in df.columns:
            if col != "ELEMENTS":
                formatter[col] = lambda x: "{:,.2f}".format(x) if isinstance(x, (int, float)) else str(x)
        
        styler = df.style.format(formatter)
        
        # Couleurs améliorées pour meilleure lisibilité sur fond sombre
        header_color = '#1e3a8a'  # Bleu marine foncé pour en-têtes
        section_color = '#3b4a72'  # Bleu plus clair pour sections
        row_color_1 = '#2d3748'    # Gris foncé pour lignes paires
        row_color_2 = '#1f2937'    # Gris très foncé pour lignes impaires
        highlight_color = '#3b82f6'  # Bleu vif pour ligne TVA NETTE
        
        # Style de base pour tout le tableau - texte blanc
        styler = styler.set_properties(**{'color': 'white'})
        
        # Appliquer style pour en-tête de colonnes
        styler = styler.set_table_styles([
            {'selector': 'thead th', 'props': [('background-color', header_color), ('color', 'white'), ('font-weight', 'bold')]},
        ])
        
        # Définir les couleurs de fond pour les catégories principales
        header_rows = [0, 3, 6]  # Lignes des en-têtes de section
        
        # Appliquer un style pour les en-têtes de section
        for row in header_rows:
            if row < len(df):
                styler = styler.set_properties(subset=pd.IndexSlice[row, :], 
                                            **{'background-color': section_color, 'font-weight': 'bold'})
        
        # Appliquer un style pour les sous-catégories avec alternance de couleurs
        for i, row in enumerate(df.index):
            if i not in header_rows and df.iloc[i]["ELEMENTS"] != "TVA NETTE DUE":
                if df.iloc[i]["ELEMENTS"].startswith("  "):  # Sous-catégorie
                    styler = styler.set_properties(subset=pd.IndexSlice[row, :], 
                                                **{'background-color': row_color_1 if i % 2 == 0 else row_color_2})
        
        # Mettre en évidence la TVA nette due
        tva_nette_rows = df[df["ELEMENTS"] == "TVA NETTE DUE"].index
        if len(tva_nette_rows) > 0:
            tva_nette_row = tva_nette_rows[0]
            styler = styler.set_properties(subset=pd.IndexSlice[tva_nette_row, :], 
                                        **{'background-color': highlight_color, 'font-weight': 'bold'})
        
        # Colorer les valeurs négatives en rouge clair (lisible sur fond sombre)
        def color_negative(val):
            if isinstance(val, (int, float)) and val < 0:
                return 'color: #f87171'  # Rouge clair
            return ''
        
        styler = styler.applymap(color_negative)
        
        return styler
    
    # Afficher le tableau avec style amélioré
    st.dataframe(style_vat_table(df), use_container_width=True, height=400)
    
    # Visualisations
    st.subheader("Analyse de la TVA")
    
    tab1, tab2 = st.tabs(["Evolution de la TVA", "Répartition par mois"])
    
    with tab1:
        # Préparer les données pour le graphique d'évolution
        chart_data = {
            'Mois': list(range(1, num_months+1)),
            'TVA collectée': [tva_collectee] * num_months,
            'TVA déductible': [tva_deductible] * num_months,
            'TVA nette': [tva_nette_first_month] + [tva_nette_other_months] * (num_months-1)
        }
        
        chart_df = pd.DataFrame(chart_data)
        
        fig = px.line(chart_df, x='Mois', y=['TVA collectée', 'TVA déductible', 'TVA nette'], markers=True)
        fig.update_layout(
            title="Évolution de la TVA sur la période",
            xaxis_title="Mois",
            yaxis_title="Montant (DHS)",
            hovermode="x unified",
            legend_title="Composants TVA",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='white'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # Répartition de la TVA pour un mois spécifique
        selected_month = st.slider("Sélectionnez un mois", 1, num_months, 1)
        
        # Données pour le camembert - CORRECTION COMPLÈTE
        tva_components = {}
        
        # S'assurer que toutes les valeurs sont des nombres valides
        tva_collectee = tva_collectee if isinstance(tva_collectee, (int, float)) else 0
        tva_deductible = tva_deductible if isinstance(tva_deductible, (int, float)) else 0
        tva_immo = tva_immo if isinstance(tva_immo, (int, float)) else 0
        
        # Créer un dictionnaire avec les composants de TVA non nuls
        if tva_collectee != 0:
            tva_components['TVA collectée'] = tva_collectee
        
        if tva_deductible != 0:
            tva_components['TVA déductible sur achats'] = -tva_deductible
        
        if selected_month == 1 and tva_immo != 0:
            tva_components['TVA déductible sur immobilisations'] = -tva_immo
        
        # Vérifier qu'il y a des données à afficher
        if tva_components:
            # Créer des listes pour le graphique
            labels = list(tva_components.keys())
            values = [abs(v) for v in tva_components.values()]
            
            # Approche alternative utilisant px.pie dans un try-except
            try:
                fig = px.pie(
                    names=labels,
                    values=values,
                    title=f"Répartition des composants de la TVA - Mois {selected_month}",
                    color_discrete_sequence=px.colors.qualitative.Bold  # Couleurs plus vives
                )
                
                # Mise à jour des traces sans dépendre de fig.data[0].text
                fig.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    textfont_color='white',
                    hovertemplate='<b>%{label}</b><br>Montant: %{value:.2f} DHS<br>Pourcentage: %{percent}'
                )
                
                fig.update_layout(
                    legend=dict(orientation="h", yanchor="bottom", y=0),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            except Exception as e:
                # En cas d'erreur avec Plotly, utiliser une approche plus simple
                st.error(f"Impossible de générer le graphique: {str(e)}")
                
                # Afficher un tableau simple à la place
                st.write("Répartition des composants de la TVA - Mois", selected_month)
                
                component_df = pd.DataFrame({
                    'Composant': labels,
                    'Montant (DHS)': ["{:,.2f}".format(abs(v)) for v in tva_components.values()],
                    'Type': ['Collecté' if k == 'TVA collectée' else 'Déductible' for k in tva_components.keys()]
                })
                
                st.dataframe(component_df)
        else:
            st.info("Aucune donnée TVA à afficher pour ce mois.")
    
    # Résumé financier
    st.subheader("Synthèse TVA")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_tva_collected = tva_collectee * num_months
        st.metric(
            "Total TVA collectée", 
            f"{total_tva_collected:,.2f} DHS"
        )
    
    with col2:
        total_tva_deductible = (tva_deductible * num_months) + tva_immo
        st.metric(
            "Total TVA déductible", 
            f"{total_tva_deductible:,.2f} DHS"
        )
    
    with col3:
        total_tva_nette = total_tva_collected - total_tva_deductible
        st.metric(
            "Total TVA nette due",
            f"{total_tva_nette:,.2f} DHS",
            delta=None
        )
    
    # Export des données
    st.download_button(
        "💾 Exporter le budget TVA",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name="budget_tva.csv",
        mime="text/csv",
        help="Télécharger le tableau au format CSV"
    )



# Ignorer les avertissements de dépréciation
warnings.filterwarnings('ignore')
def calculate_financial_metrics(df):
    """
    Calcule des métriques financières avancées à partir du DataFrame d'importation
    avec une gestion robuste des erreurs
    """
    # Initialiser toutes les métriques avec des valeurs par défaut pour éviter KeyError
    metrics = {
        'total_immobilisations': 0,
        'total_financements': 0,
        'total_charges': 0,
        'total_ventes': 0,
        'cash_flow_mensuel': 0,
        'roi_mensuel': 0,
        'roi_annuel': 0,
        'payback_months': 0,
        'payback_years': 0,
        'van': 0,  # Clé 'van' initialisée explicitement
        'tri': None,
        'amortissement_annuel': 0,
        'tva_collectee': 0,
        'tva_deductible_achats': 0,
        'tva_deductible_immo': 0,
        'tva_nette': 0
    }
    
    try:
        # Calculer les montants totaux par catégorie avec sécurité contre les None/NaN
        if 'type' in df.columns and 'montant' in df.columns:
            # Filtrer les valeurs NaN/None
            valid_df = df.dropna(subset=['montant'])
            
            # Calculer les totaux par type
            total_immobilisations = valid_df[valid_df['type'] == 'immobilisation']['montant'].sum()
            total_financements = valid_df[valid_df['type'] == 'financement']['montant'].sum()
            total_charges_mensuelles = valid_df[valid_df['type'] == 'charges']['montant'].sum()
            total_ventes_mensuelles = valid_df[valid_df['type'] == 'ventes']['montant'].sum()
            
            # Remplacer NaN par 0
            metrics['total_immobilisations'] = float(total_immobilisations) if not pd.isna(total_immobilisations) else 0
            metrics['total_financements'] = float(total_financements) if not pd.isna(total_financements) else 0
            metrics['total_charges'] = float(total_charges_mensuelles) if not pd.isna(total_charges_mensuelles) else 0
            metrics['total_ventes'] = float(total_ventes_mensuelles) if not pd.isna(total_ventes_mensuelles) else 0
        
        # Calcul du flux de trésorerie mensuel
        metrics['cash_flow_mensuel'] = metrics['total_ventes'] - metrics['total_charges']
        
        # Calcul du ROI (Retour sur investissement) si les données sont disponibles
        if metrics['total_immobilisations'] > 0:
            roi_mensuel = metrics['cash_flow_mensuel'] / metrics['total_immobilisations']
            metrics['roi_mensuel'] = roi_mensuel
            metrics['roi_annuel'] = roi_mensuel * 12
            
            # Calcul du délai de récupération de l'investissement (Payback period)
            if metrics['cash_flow_mensuel'] > 0:
                metrics['payback_months'] = metrics['total_immobilisations'] / metrics['cash_flow_mensuel']
                metrics['payback_years'] = metrics['payback_months'] / 12
            else:
                metrics['payback_months'] = float('inf')
                metrics['payback_years'] = float('inf')
        else:
            metrics['roi_mensuel'] = 0
            metrics['roi_annuel'] = 0
            metrics['payback_months'] = 0
            metrics['payback_years'] = 0
        
        # Calcul de la VAN (Valeur Actuelle Nette) sur 5 ans avec un taux d'actualisation de 8%
        if PYFINANCE_AVAILABLE:
            try:
                if metrics['cash_flow_mensuel'] > 0:
                    # Créer un flux de trésorerie sur 60 mois (5 ans)
                    cash_flows = [-metrics['total_immobilisations']] + [metrics['cash_flow_mensuel']] * 60
                    
                    # Taux d'actualisation mensuel (8% annuel)
                    monthly_rate = 0.08 / 12
                    
                    # Calculer la VAN
                    metrics['van'] = pf.npv(rate=monthly_rate, values=cash_flows)
                    
                    # Calculer le TRI
                    try:
                        metrics['tri'] = pf.irr(values=cash_flows) * 12  # Convertir le TRI mensuel en annuel
                    except Exception as e:
                        metrics['tri'] = None
                else:
                    metrics['van'] = -metrics['total_immobilisations']
                    metrics['tri'] = None
            except Exception as e:
                # En cas d'erreur, définir la VAN et le TRI à des valeurs par défaut
                metrics['van'] = 0
                metrics['tri'] = None
        else:
            # Version simplifiée de calcul si PyFinance n'est pas disponible
            if metrics['cash_flow_mensuel'] > 0:
                # Calcul simplifié de la VAN sur 5 ans
                van = -metrics['total_immobilisations']
                monthly_rate = 0.08 / 12
                
                for i in range(60):
                    van += metrics['cash_flow_mensuel'] / ((1 + monthly_rate) ** (i + 1))
                
                metrics['van'] = van
                metrics['tri'] = None  # TRI indisponible sans PyFinance
            else:
                metrics['van'] = -metrics['total_immobilisations']
                metrics['tri'] = None
        
        # Calculer l'amortissement total annuel
        annual_amort = 0
        if 'type' in df.columns and all(col in df.columns for col in ['montant', 'taux_amort', 'duree_amort']):
            for _, row in df[df['type'] == 'immobilisation'].iterrows():
                # Utiliser 0 si les valeurs sont None ou NaN
                montant = row['montant'] if pd.notna(row['montant']) else 0
                taux_amort = row['taux_amort'] if pd.notna(row['taux_amort']) else 0
                duree_amort = row['duree_amort'] if pd.notna(row['duree_amort']) else 0
                
                if duree_amort > 0:
                    annual_amort += montant * (taux_amort / 100)
        
        metrics['amortissement_annuel'] = annual_amort
        
        # Calculer la TVA
        try:
            # TVA sur ventes
            tva_collectee = 0
            if 'type' in df.columns and 'taux_tva' in df.columns:
                ventes_df = df[df['type'] == 'ventes']
                for _, row in ventes_df.iterrows():
                    montant = row['montant'] if pd.notna(row['montant']) else 0
                    taux_tva = row['taux_tva'] if pd.notna(row['taux_tva']) else 0
                    tva_collectee += montant * (taux_tva / 100)
            
            # TVA sur achats
            tva_deductible_achats = 0
            if 'type' in df.columns and 'taux_tva' in df.columns:
                charges_df = df[df['type'] == 'charges']
                for _, row in charges_df.iterrows():
                    montant = row['montant'] if pd.notna(row['montant']) else 0
                    taux_tva = row['taux_tva'] if pd.notna(row['taux_tva']) else 0
                    tva_deductible_achats += montant * (taux_tva / 100)
            
            # TVA sur immobilisations
            tva_deductible_immo = 0
            if 'type' in df.columns and 'taux_tva' in df.columns:
                immo_df = df[df['type'] == 'immobilisation']
                for _, row in immo_df.iterrows():
                    montant = row['montant'] if pd.notna(row['montant']) else 0
                    taux_tva = row['taux_tva'] if pd.notna(row['taux_tva']) else 0
                    tva_deductible_immo += montant * (taux_tva / 100)
            
            metrics['tva_collectee'] = tva_collectee
            metrics['tva_deductible_achats'] = tva_deductible_achats
            metrics['tva_deductible_immo'] = tva_deductible_immo
            metrics['tva_nette'] = tva_collectee - tva_deductible_achats - tva_deductible_immo
        except Exception as e:
            # En cas d'erreur, définir les valeurs de TVA par défaut
            metrics['tva_collectee'] = 0
            metrics['tva_deductible_achats'] = 0
            metrics['tva_deductible_immo'] = 0
            metrics['tva_nette'] = 0
    
    except Exception as e:
        # En cas d'erreur majeure, conserver les valeurs par défaut
        print(f"Erreur dans le calcul des métriques: {str(e)}")
    
    return metrics


def process_with_ai(df):
    """
    Fonction d'analyse qui traite automatiquement les données importées
    et les structure dans le bon format, avec une gestion robuste des erreurs
    """
    # Vérifier si le dataframe est vide
    if df is None or df.empty:
        return None, "Le fichier CSV est vide ou n'a pas pu être lu correctement.", {}
    
    # Initialiser le message de traitement
    processing_log = []
    
    # Compter les lignes avant traitement
    initial_rows = len(df)
    processing_log.append(f"Fichier importé avec {initial_rows} entrées.")
    
    # Liste des colonnes attendues
    expected_columns = ['type', 'categorie', 'nom', 'montant', 'taux_tva', 'duree_amort', 'taux_amort', 'date']
    
    # Vérifier si toutes les colonnes attendues sont présentes
    missing_columns = [col for col in expected_columns if col not in df.columns]
    
    # Si des colonnes sont manquantes, tenter de déduire les colonnes à partir des données
    if missing_columns:
        processing_log.append(f"Colonnes manquantes détectées: {', '.join(missing_columns)}")
        processing_log.append("Tentative de déduction des colonnes à partir des données...")
        
        # Copier le dataframe pour le retraiter
        new_df = pd.DataFrame(columns=expected_columns)
        
        # Essayer de correspondre les colonnes existantes avec les attendues
        column_mapping = {}
        for col in df.columns:
            # Essayer de deviner la colonne en fonction du nom ou du contenu
            col_lower = str(col).lower()
            
            if any(x in col_lower for x in ['type', 'catégorie', 'élément']):
                column_mapping[col] = 'type'
            elif any(x in col_lower for x in ['catégorie', 'cat', 'groupe']):
                column_mapping[col] = 'categorie'
            elif any(x in col_lower for x in ['nom', 'designation', 'libellé', 'description']):
                column_mapping[col] = 'nom'
            elif any(x in col_lower for x in ['montant', 'valeur', 'prix', 'somme', 'coût', 'cout']):
                column_mapping[col] = 'montant'
            elif any(x in col_lower for x in ['tva', 'taxe']):
                column_mapping[col] = 'taux_tva'
            elif any(x in col_lower for x in ['durée', 'duree', 'période', 'periode', 'années']):
                column_mapping[col] = 'duree_amort'
            elif any(x in col_lower for x in ['amort', 'pourcentage', 'taux']):
                column_mapping[col] = 'taux_amort'
            elif any(x in col_lower for x in ['date', 'jour']):
                column_mapping[col] = 'date'
        
        # Appliquer la correspondance
        for old_col, new_col in column_mapping.items():
            new_df[new_col] = df[old_col]
        
        # Si certaines colonnes sont toujours manquantes, les créer avec des valeurs par défaut
        for col in expected_columns:
            if col not in new_df.columns:
                if col == 'type':
                    # Essayer de déduire le type à partir des autres colonnes
                    new_df[col] = 'autre'
                    if 'categorie' in new_df.columns:
                        cat_to_type = {
                            'equipement': 'immobilisation',
                            'transport': 'immobilisation',
                            'terrain': 'immobilisation',
                            'bureau': 'immobilisation',
                            'informatique': 'immobilisation',
                            'apport': 'financement',
                            'emprunt': 'financement',
                            'subvention': 'financement',
                            'loyer': 'charges',
                            'personnel': 'charges',
                            'services': 'charges',
                            'produit': 'ventes',
                            'service': 'ventes'
                        }
                        new_df[col] = new_df['categorie'].apply(
                            lambda x: next((v for k, v in cat_to_type.items() 
                                          if k in str(x).lower() if pd.notna(x)), 'autre')
                        )
                elif col == 'categorie':
                    new_df[col] = 'autre'
                elif col == 'nom':
                    new_df[col] = 'non spécifié'
                elif col == 'taux_tva':
                    new_df[col] = 20.0
                elif col in ['duree_amort', 'taux_amort']:
                    new_df[col] = 0.0
                    if 'type' in new_df.columns:
                        # Si c'est une immobilisation, mettre des valeurs par défaut d'amortissement
                        is_immo = new_df['type'] == 'immobilisation'
                        new_df.loc[is_immo, 'duree_amort'] = 5.0
                        new_df.loc[is_immo, 'taux_amort'] = 20.0
                elif col == 'montant':
                    new_df[col] = 0.0
                elif col == 'date':
                    new_df[col] = datetime.now().strftime('%Y-%m-%d')
        
        df = new_df
        processing_log.append("Colonnes déduites et valeurs par défaut appliquées.")
    
    # Convertir les colonnes numériques
    for col in ['montant', 'taux_tva', 'duree_amort', 'taux_amort']:
        if col in df.columns:
            try:
                # Détection des valeurs problématiques
                problematic_values = []
                for idx, val in df[col].items():
                    if not pd.isna(val):
                        try:
                            # Tenter de convertir en nombre
                            float(val)
                        except (ValueError, TypeError):
                            problematic_values.append((idx, val))
                
                if problematic_values:
                    problem_info = ", ".join([f"{idx}: {val}" for idx, val in problematic_values[:5]])
                    problem_count = len(problematic_values)
                    if problem_count > 5:
                        problem_info += f" et {problem_count-5} autres"
                    processing_log.append(f"Valeurs problématiques détectées dans la colonne {col}: {problem_info}")
                
                # Convertir en numérique en remplaçant les valeurs problématiques par NaN
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Remplacer les NaN par 0
                na_count = df[col].isna().sum()
                if na_count > 0:
                    processing_log.append(f"{na_count} valeurs manquantes ou non numériques dans {col} remplacées par 0")
                
                df[col] = df[col].fillna(0)
                
                processing_log.append(f"Colonne {col} convertie en format numérique.")
            except Exception as e:
                processing_log.append(f"Erreur lors de la conversion de la colonne {col}: {str(e)}")
                # Créer une colonne de valeurs par défaut
                df[col] = 0
    
    # Convertir la colonne date en format date
    if 'date' in df.columns:
        try:
            # Convertir en datetime
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            # Compter les valeurs NaT (Not a Time) créées
            nat_count = df['date'].isna().sum()
            if nat_count > 0:
                processing_log.append(f"{nat_count} valeurs de date non valides remplacées par la date actuelle")
            
            # Remplacer les NaT par la date actuelle
            df['date'] = df['date'].fillna(pd.Timestamp.now())
            
            processing_log.append("Colonne date convertie en format date.")
        except Exception as e:
            processing_log.append(f"Erreur lors de la conversion de la colonne date: {str(e)}")
            # Créer une colonne de valeurs par défaut
            df['date'] = pd.Timestamp.now()
    
    # S'assurer que les colonnes de texte ne contiennent pas de None/NaN
    for col in ['type', 'categorie', 'nom']:
        if col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                processing_log.append(f"{null_count} valeurs manquantes dans {col} remplacées par valeur par défaut")
            
            # Remplacer les valeurs manquantes par une chaîne par défaut
            if col == 'type':
                df[col] = df[col].fillna('autre')
            elif col == 'categorie':
                df[col] = df[col].fillna('non spécifiée')
            else:
                df[col] = df[col].fillna('non spécifié')
    
    # Dernières vérifications et nettoyages
    df = df.drop_duplicates()
    
    # Calcul des métriques financières avec gestion robuste des erreurs
    try:
        # Calcul des métriques financières
        metrics = calculate_financial_metrics(df)
        processing_log.append("Métriques financières calculées avec succès.")
    except Exception as e:
        processing_log.append(f"Erreur lors du calcul des métriques financières: {str(e)}")
        # Créer des métriques vides en cas d'erreur
        metrics = {
            'total_immobilisations': 0,
            'total_financements': 0,
            'total_charges': 0,
            'total_ventes': 0,
            'cash_flow_mensuel': 0,
            'roi_mensuel': 0,
            'roi_annuel': 0,
            'payback_months': 0,
            'payback_years': 0,
            'van': 0,  # Garantir que cette clé existe toujours
            'tri': None,
            'amortissement_annuel': 0,
            'tva_collectee': 0,
            'tva_deductible_achats': 0,
            'tva_deductible_immo': 0,
            'tva_nette': 0
        }
    
    # Calculer le nombre de lignes après traitement
    final_rows = len(df)
    processing_log.append(f"Traitement terminé: {final_rows} entrées valides.")
    
    return df, "\n".join(processing_log), metrics

def show_csv_import():
    st.header("📤 Importation et analyse des données financières")
    
    with st.expander("ℹ️ Guide d'importation", expanded=True):
        st.markdown("""
        ### Format du fichier CSV
        
        Le fichier CSV doit contenir les colonnes suivantes:
        - `type`: Type d'élément (immobilisation, financement, charges, ventes)
        - `categorie`: Sous-catégorie (equipement, transport, apport, etc.)
        - `nom`: Nom ou description de l'élément
        - `montant`: Montant en DHS
        - `taux_tva`: Taux de TVA applicable (%)
        - `duree_amort`: Durée d'amortissement (années) - pour les immobilisations
        - `taux_amort`: Taux d'amortissement (%) - pour les immobilisations
        - `date`: Date d'acquisition ou de transaction
        
        ### Comment importer
        
        1. Préparez votre fichier CSV selon le format ci-dessus
        2. Glissez-déposez le fichier dans la zone prévue ci-dessous ou cliquez pour sélectionner
        3. Notre système avec IA analysera automatiquement vos données
        4. Vérifiez les résultats et ajustez si nécessaire
        5. Appliquez les données à votre projet
        """)
        
        # Lien de téléchargement du modèle CSV
        csv_template = """type,categorie,nom,montant,taux_tva,duree_amort,taux_amort,date
immobilisation,equipement,Matériel d'équipement,78400.00,20,5,20,2023-01-15
immobilisation,transport,Matériel de transport,45000.00,20,5,20,2023-02-10
immobilisation,terrain,Terrain / Local,120000.00,20,10,10,2023-01-01
financement,apport,Apport personnel,50000.00,0,0,0,2023-01-01
financement,emprunt,Crédit bancaire,150000.00,0,0,0,2023-01-15
financement,subvention,Subvention,30000.00,0,0,0,2023-02-01
charges,loyer,Loyer mensuel,3500.00,20,0,0,2023-01-01
charges,personnel,Salaire employé 1,5000.00,0,0,0,2023-01-01
charges,personnel,Salaire employé 2,6000.00,0,0,0,2023-01-01
charges,services,Téléphone et Internet,500.00,20,0,0,2023-01-01
charges,services,Électricité,800.00,14,0,0,2023-01-01
ventes,produit,Produit A,12000.00,20,0,0,2023-01-15
ventes,produit,Produit B,8000.00,20,0,0,2023-01-20
ventes,service,Service conseil,15000.00,20,0,0,2023-02-01"""
        
        st.download_button(
            label="📥 Télécharger le modèle CSV",
            data=csv_template,
            file_name="modele_donnees_financieres.csv",
            mime="text/csv"
        )
    
    # Uploader de fichier CSV
    uploaded_file = st.file_uploader("Glissez-déposez votre fichier CSV ici", type=["csv"])
    
    if uploaded_file is not None:
        try:
            # Indicateur de chargement
            with st.spinner("Analyse du fichier CSV avec notre IA..."):
                # Lire le fichier CSV
                df = pd.read_csv(uploaded_file, sep=None, engine='python')
                
                # Traiter avec l'IA et pyfinance
                processed_df, log_message, metrics = process_with_ai(df)
                
                if processed_df is not None:
                    st.success("Fichier importé et traité avec succès!")
                    
                    # Afficher le rapport de traitement
                    with st.expander("📋 Rapport de traitement", expanded=False):
                        st.code(log_message)
                    
                    # Dashboard de résultats financiers
                    st.subheader("📊 Tableau de bord financier")
                    
                    # Onglets pour afficher les différentes analyses
                    tab1, tab2, tab3, tab4 = st.tabs(["Synthèse", "Rentabilité", "TVA", "Données importées"])
                    
                    with tab1:
                        # Métriques de base en 4 colonnes
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric(
                                "Total Immobilisations", 
                                f"{metrics['total_immobilisations']:,.2f} DHS"
                            )
                        
                        with col2:
                            st.metric(
                                "Total Financements", 
                                f"{metrics['total_financements']:,.2f} DHS"
                            )
                        
                        with col3:
                            st.metric(
                                "Charges Mensuelles", 
                                f"{metrics['total_charges']:,.2f} DHS"
                            )
                        
                        with col4:
                            st.metric(
                                "Ventes Mensuelles", 
                                f"{metrics['total_ventes']:,.2f} DHS",
                                f"{metrics['cash_flow_mensuel']:+,.2f} DHS"
                            )
                        
                        # Graphiques de répartition
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Graphique de répartition des montants par type
                            pie_data = processed_df.groupby('type')['montant'].sum().reset_index()
                            fig = px.pie(
                                pie_data,
                                values='montant',
                                names='type',
                                title="Répartition par type de données",
                                color_discrete_sequence=px.colors.qualitative.Bold
                            )
                            fig.update_layout(
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font_color='white'
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            # Graphique des immobilisations par catégorie
                            if len(processed_df[processed_df['type'] == 'immobilisation']) > 0:
                                immo_data = processed_df[processed_df['type'] == 'immobilisation'].groupby('categorie')['montant'].sum().reset_index()
                                fig = px.bar(
                                    immo_data,
                                    x='categorie',
                                    y='montant',
                                    title="Immobilisations par catégorie",
                                    color='categorie',
                                    color_discrete_sequence=px.colors.qualitative.Pastel
                                )
                                fig.update_layout(
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    font_color='white',
                                    xaxis_title="Catégorie",
                                    yaxis_title="Montant (DHS)"
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("Aucune immobilisation trouvée dans les données importées.")
                    
                    with tab2:
                        # Métriques de rentabilité
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric(
                                "Cash-Flow Mensuel",
                                f"{metrics['cash_flow_mensuel']:,.2f} DHS",
                                f"{metrics['cash_flow_mensuel']*12:+,.2f} DHS (annuel)"
                            )
                            
                            if metrics['payback_months'] != float('inf'):
                                st.metric(
                                    "Délai de récupération",
                                    f"{metrics['payback_months']:.1f} mois",
                                    f"{metrics['payback_years']:.2f} ans"
                                )
                            else:
                                st.metric(
                                    "Délai de récupération",
                                    "N/A",
                                    "Cash-flow négatif ou nul"
                                )
                        
                        with col2:
                            if metrics['roi_annuel'] > 0:
                                st.metric(
                                    "ROI (Retour sur investissement)",
                                    f"{metrics['roi_annuel']*100:.2f}% par an",
                                    f"{metrics['roi_mensuel']*100:.2f}% par mois"
                                )
                            else:
                                st.metric(
                                    "ROI (Retour sur investissement)",
                                    f"{metrics['roi_annuel']*100:.2f}%",
                                    "Investissement non rentable"
                                )
                            
                            if metrics['van'] is not None:
                                st.metric(
                                    "VAN (Valeur Actuelle Nette)",
                                    f"{metrics['van']:,.2f} DHS",
                                    f"TRI: {metrics['tri']*100:.2f}%" if metrics['tri'] is not None else "TRI: N/A"
                                )
                            else:
                                st.metric("VAN (Valeur Actuelle Nette)", "N/A", "")
                        
                        # Graphique de projection des flux de trésorerie sur 24 mois
                        if metrics['cash_flow_mensuel'] != 0:
                            # Créer les données pour le graphique
                            months = list(range(0, 25))
                            cumulative_cash_flow = [-metrics['total_immobilisations']]
                            
                            for i in range(1, 25):
                                cumulative_cash_flow.append(cumulative_cash_flow[-1] + metrics['cash_flow_mensuel'])
                            
                            cash_flow_df = pd.DataFrame({
                                'Mois': months,
                                'Flux de trésorerie cumulé': cumulative_cash_flow
                            })
                            
                            # Créer le graphique
                            fig = px.line(
                                cash_flow_df, 
                                x='Mois', 
                                y='Flux de trésorerie cumulé',
                                markers=True,
                                title="Projection du flux de trésorerie cumulé sur 24 mois"
                            )
                            
                            # Ajouter une ligne horizontale à y=0
                            fig.add_shape(
                                type='line',
                                x0=0,
                                y0=0,
                                x1=24,
                                y1=0,
                                line=dict(color='gray', dash='dash')
                            )
                            
                            # Mettre à jour la mise en page
                            fig.update_layout(
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font_color='white',
                                xaxis_title="Mois",
                                yaxis_title="Flux de trésorerie cumulé (DHS)"
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Afficher les détails de l'analyse de rentabilité
                            with st.expander("🔍 Détails de l'analyse de rentabilité"):
                                st.markdown("""
                                ### Analyse de la rentabilité
                                
                                L'analyse est basée sur les hypothèses suivantes:
                                - Les charges et revenus mensuels sont constants
                                - Le taux d'actualisation utilisé pour la VAN est de 8% annuel
                                - L'horizon d'investissement est de 5 ans
                                
                                **Interprétation des résultats:**
                                """)
                                
                                if metrics['van'] > 0:
                                    st.success("✅ La VAN est positive, ce qui indique que le projet est rentable sur 5 ans.")
                                else:
                                    st.warning("⚠️ La VAN est négative, ce qui indique que le projet n'est pas rentable sur 5 ans.")
                                
                                if metrics['payback_months'] < 24:
                                    st.success(f"✅ Le délai de récupération est de {metrics['payback_months']:.1f} mois, ce qui est inférieur à 2 ans.")
                                elif metrics['payback_months'] < 60:
                                    st.info(f"ℹ️ Le délai de récupération est de {metrics['payback_months']:.1f} mois, ce qui est acceptable mais pourrait être amélioré.")
                                else:
                                    st.warning(f"⚠️ Le délai de récupération est de {metrics['payback_months']:.1f} mois, ce qui est relativement long.")
                        else:
                            st.info("Impossible de générer une projection de trésorerie: cash-flow mensuel nul ou négatif.")
                    
                    with tab3:
                        # Analyse de la TVA
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric(
                                "TVA Collectée", 
                                f"{metrics['tva_collectee']:,.2f} DHS"
                            )
                        
                        with col2:
                            st.metric(
                                "TVA Déductible", 
                                f"{metrics['tva_deductible_achats'] + metrics['tva_deductible_immo']:,.2f} DHS",
                                f"Achats: {metrics['tva_deductible_achats']:,.2f} DHS, Immos: {metrics['tva_deductible_immo']:,.2f} DHS"
                            )
                        
                        with col3:
                            st.metric(
                                "TVA Nette Due", 
                                f"{metrics['tva_nette']:,.2f} DHS",
                                f"{metrics['tva_nette']*12:,.2f} DHS (annuel)"
                            )
                        
                        # Graphique de répartition de la TVA
                        tva_data = {
                            'Composant': ['TVA Collectée', 'TVA Déductible Achats', 'TVA Déductible Immos'],
                            'Montant': [metrics['tva_collectee'], metrics['tva_deductible_achats'], metrics['tva_deductible_immo']]
                        }
                        
                        tva_df = pd.DataFrame(tva_data)
                        
                        fig = px.bar(
                            tva_df,
                            x='Composant',
                            y='Montant',
                            title="Répartition des composants de la TVA",
                            color='Composant',
                            color_discrete_sequence=px.colors.qualitative.Pastel
                        )
                        
                        fig.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font_color='white',
                            xaxis_title="",
                            yaxis_title="Montant (DHS)"
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Tableau détaillé de la TVA par catégorie
                        st.subheader("Détail de la TVA par catégorie")
                        
                        tva_detail = []
                        
                        # TVA sur ventes par catégorie
                        ventes_by_cat = processed_df[processed_df['type'] == 'ventes'].groupby('categorie').agg({
                            'montant': 'sum',
                            'taux_tva': 'mean'
                        }).reset_index()
                        
                        for _, row in ventes_by_cat.iterrows():
                            tva_detail.append({
                                'Type': 'Ventes',
                                'Catégorie': row['categorie'],
                                'Montant HT': row['montant'],
                                'Taux TVA': row['taux_tva'],
                                'TVA': row['montant'] * (row['taux_tva'] / 100),
                                'Type TVA': 'Collectée'
                            })
                        
                        # TVA sur charges par catégorie
                        charges_by_cat = processed_df[processed_df['type'] == 'charges'].groupby('categorie').agg({
                            'montant': 'sum',
                            'taux_tva': 'mean'
                        }).reset_index()
                        
                        for _, row in charges_by_cat.iterrows():
                            tva_detail.append({
                                'Type': 'Charges',
                                'Catégorie': row['categorie'],
                                'Montant HT': row['montant'],
                                'Taux TVA': row['taux_tva'],
                                'TVA': row['montant'] * (row['taux_tva'] / 100),
                                'Type TVA': 'Déductible'
                            })
                        
                        # TVA sur immobilisations par catégorie
                        immo_by_cat = processed_df[processed_df['type'] == 'immobilisation'].groupby('categorie').agg({
                            'montant': 'sum',
                            'taux_tva': 'mean'
                        }).reset_index()
                        
                        for _, row in immo_by_cat.iterrows():
                            tva_detail.append({
                                'Type': 'Immobilisation',
                                'Catégorie': row['categorie'],
                                'Montant HT': row['montant'],
                                'Taux TVA': row['taux_tva'],
                                'TVA': row['montant'] * (row['taux_tva'] / 100),
                                'Type TVA': 'Déductible'
                            })
                        
                        # Créer le DataFrame du détail TVA
                        tva_detail_df = pd.DataFrame(tva_detail)
                        
                        if not tva_detail_df.empty:
                            # Formatter les colonnes
                            formatted_tva_detail = tva_detail_df.copy()
                            formatted_tva_detail['Montant HT'] = formatted_tva_detail['Montant HT'].apply(lambda x: f"{x:,.2f}")
                            formatted_tva_detail['Taux TVA'] = formatted_tva_detail['Taux TVA'].apply(lambda x: f"{x:.1f}%")
                            formatted_tva_detail['TVA'] = formatted_tva_detail['TVA'].apply(lambda x: f"{x:,.2f}")
                            
                            st.dataframe(formatted_tva_detail, use_container_width=True)
                        else:
                            st.info("Aucune donnée TVA détaillée disponible.")
                    
                    with tab4:
                        # Afficher les données traitées
                        st.subheader("Données importées et traitées")
                        
                        # Option pour filtrer par type
                        type_filter = st.multiselect(
                            "Filtrer par type",
                            options=processed_df['type'].unique(),
                            default=processed_df['type'].unique()
                        )
                        
                        filtered_df = processed_df[processed_df['type'].isin(type_filter)]
                        
                        # Formatter les colonnes numériques
                        formatted_df = filtered_df.copy()
                        formatted_df['montant'] = formatted_df['montant'].apply(lambda x: f"{x:,.2f}")
                        formatted_df['taux_tva'] = formatted_df['taux_tva'].apply(lambda x: f"{x:.1f}%")
                        formatted_df['duree_amort'] = formatted_df['duree_amort'].apply(lambda x: f"{x:.0f}" if x > 0 else "-")
                        formatted_df['taux_amort'] = formatted_df['taux_amort'].apply(lambda x: f"{x:.1f}%" if x > 0 else "-")
                        
                        st.dataframe(formatted_df, use_container_width=True)
                    
                    # Option pour appliquer les données importées
                    st.subheader("Application des données")
                    
                    apply_col1, apply_col2 = st.columns(2)
                    
                    with apply_col1:
                        apply_all = st.checkbox("Appliquer toutes les données", value=True)
                    
                    with apply_col2:
                        apply_options = []
                        
                        if not apply_all:
                            apply_options = st.multiselect(
                                "Sélectionner les sections à appliquer",
                                options=["Immobilisations", "Financements", "Charges", "Ventes", "Amortissements", "TVA"],
                                default=["Immobilisations", "Financements", "Charges", "Ventes"]
                            )
                    
                    if st.button("Appliquer ces données à mon projet", type="primary"):
                        sections_to_apply = ["Immobilisations", "Financements", "Charges", "Ventes", "Amortissements", "TVA"] if apply_all else apply_options
                        
                        # Filtrer par type et mettre à jour les données du projet
                        immos = processed_df[processed_df['type'] == 'immobilisation']
                        finances = processed_df[processed_df['type'] == 'financement']
                        charges = processed_df[processed_df['type'] == 'charges']
                        ventes = processed_df[processed_df['type'] == 'ventes']
                        
                        # Mettre à jour les immobilisations
                        if "Immobilisations" in sections_to_apply and not immos.empty:
                            st.session_state.immos = []
                            for _, row in immos.iterrows():
                                st.session_state.immos.append({
                                    "Nom": row['nom'],
                                    "Montant": row['montant'],
                                    "Catégorie": row['categorie'],
                                    "Date": row['date']
                                })
                            st.success("✅ Immobilisations mises à jour!")
                        
                        # Mettre à jour les financements
                        if "Financements" in sections_to_apply and not finances.empty:
                            apports = finances[finances['categorie'] == 'apport']['montant'].sum()
                            emprunts = finances[finances['categorie'] == 'emprunt']['montant'].sum()
                            subventions = finances[finances['categorie'] == 'subvention']['montant'].sum()
                            
                            if 'investment_data' not in st.session_state:
                                st.session_state.investment_data = {}
                            
                            if apports > 0:
                                st.session_state.investment_data['cash_contribution'] = apports
                            
                            if 'calculated_data' not in st.session_state:
                                st.session_state.calculated_data = {}
                            
                            if emprunts > 0:
                                st.session_state.calculated_data['total_credits'] = emprunts
                            
                            if subventions > 0:
                                st.session_state.calculated_data['total_subsidies'] = subventions
                                
                            st.success("✅ Financements mis à jour!")
                        
                        # Mettre à jour les charges et ventes
                        if ("Charges" in sections_to_apply or "Ventes" in sections_to_apply) and (not charges.empty or not ventes.empty):
                            if 'monthly_cashflow_data' not in st.session_state:
                                st.session_state.monthly_cashflow_data = {
                                    'ressources': {},
                                    'chiffre_affaires': {},
                                    'immobilisations': {},
                                    'charges_exploitation': {}
                                }
                            
                            # Mettre à jour les charges
                            if "Charges" in sections_to_apply and not charges.empty:
                                # Regrouper les charges par catégorie
                                charges_by_cat = charges.groupby('categorie')['montant'].sum().to_dict()
                                for cat, amount in charges_by_cat.items():
                                    st.session_state.monthly_cashflow_data['charges_exploitation'][cat.capitalize()] = amount
                                st.success("✅ Charges mises à jour!")
                            
                            # Mettre à jour les ventes
                            if "Ventes" in sections_to_apply and not ventes.empty:
                                # Regrouper les ventes par catégorie
                                ventes_by_cat = ventes.groupby('categorie')['montant'].sum().to_dict()
                                for cat, amount in ventes_by_cat.items():
                                    st.session_state.monthly_cashflow_data['chiffre_affaires'][cat.capitalize()] = amount
                                st.success("✅ Ventes mises à jour!")
                        
                        # Mise à jour pour le tableau d'amortissement
                        if "Amortissements" in sections_to_apply and not immos.empty:
                            if 'detailed_amortization' not in st.session_state:
                                st.session_state.detailed_amortization = []
                            
                            for _, row in immos.iterrows():
                                # Vérifier si l'item existe déjà
                                item_exists = False
                                for i, item in enumerate(st.session_state.detailed_amortization):
                                    if item["name"] == row['nom']:
                                        item_exists = True
                                        # Mise à jour
                                        st.session_state.detailed_amortization[i]["amount"] = row['montant']
                                        st.session_state.detailed_amortization[i]["duration"] = row['duree_amort']
                                        st.session_state.detailed_amortization[i]["rate"] = row['taux_amort']
                                        annual_amort = row['montant'] * (row['taux_amort'] / 100)
                                        st.session_state.detailed_amortization[i]["amortization_n"] = annual_amort
                                        st.session_state.detailed_amortization[i]["amortization_n1"] = annual_amort
                                        st.session_state.detailed_amortization[i]["amortization_n2"] = annual_amort
                                
                                # Ajouter si n'existe pas
                                if not item_exists:
                                    annual_amort = row['montant'] * (row['taux_amort'] / 100)
                                    st.session_state.detailed_amortization.append({
                                        "name": row['nom'],
                                        "amount": row['montant'],
                                        "duration": row['duree_amort'],
                                        "rate": row['taux_amort'],
                                        "amortization_n": annual_amort,
                                        "amortization_n1": annual_amort,
                                        "amortization_n2": annual_amort
                                    })
                            st.success("✅ Tableau d'amortissement mis à jour!")
                        
                        # Mise à jour pour la TVA
                        if "TVA" in sections_to_apply and (not charges.empty or not ventes.empty or not immos.empty):
                            if 'vat_budget_data' not in st.session_state:
                                st.session_state.vat_budget_data = {
                                    'achats': {},
                                    'ventes': {},
                                    'tva_immobilisations': {}
                                }
                            
                            # Achats (charges)
                            if not charges.empty:
                                charges_ht = charges['montant'].sum()
                                tva_charges = charges.apply(lambda x: x['montant'] * (x['taux_tva']/100), axis=1).sum()
                                st.session_state.vat_budget_data['achats']['Achat HT'] = charges_ht
                                st.session_state.vat_budget_data['achats']['TVA déductible sur achat'] = tva_charges
                            
                            # Ventes
                            if not ventes.empty:
                                ventes_ht = ventes['montant'].sum()
                                tva_ventes = ventes.apply(lambda x: x['montant'] * (x['taux_tva']/100), axis=1).sum()
                                st.session_state.vat_budget_data['ventes']['Vente en HT'] = ventes_ht
                                st.session_state.vat_budget_data['ventes']['TVA collecte sur vente'] = tva_ventes
                            
                            # TVA sur immobilisations
                            if not immos.empty:
                                tva_immo = immos.apply(lambda x: x['montant'] * (x['taux_tva']/100), axis=1).sum()
                                st.session_state.vat_budget_data['tva_immobilisations']["TVA dedustible sur immobilisation"] = tva_immo
                            
                            st.success("✅ Budget TVA mis à jour!")
                        
                        st.balloons()
                        st.success("🎉 Toutes les données sélectionnées ont été appliquées avec succès à votre projet!")
        
        except Exception as e:
            st.error(f"Une erreur s'est produite lors de l'importation ou du traitement du fichier: {str(e)}")
            st.info("Assurez-vous que votre fichier CSV est correctement formaté et réessayez.")
# ========== EXÉCUTION DE L'APPLICATION ==========
if __name__ == "__main__":
    main()