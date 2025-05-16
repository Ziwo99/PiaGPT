import streamlit as st
import os
import time
import re
from piaget_rag_engine import PiagetRAG, format_response

# Configuration de la page
st.set_page_config(
    page_title="PiaGPT - L'avatar virtuel de Jean Piaget",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styles CSS personnalisés
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
        color: white;
    }
    .sub-header {
        font-size: 1.2rem;
        font-weight: 400;
        margin-bottom: 2rem;
        color: #CACACA;
    }
    .response-container {
        background-color: #F9FAFB;
        border-radius: 10px;
        padding: 20px;
        margin-top: 20px;
        border-left: 5px solid #1E3A8A;
    }
    .sources-container {
        background-color: #F3F4F6;
        border-radius: 10px;
        padding: 20px;
        margin-top: 20px;
        border-left: 5px solid #4B5563;
    }
    .source-item {
        margin-bottom: 20px;
        padding: 15px;
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        border: 1px solid #E5E7EB;
    }
    .source-header {
        font-weight: 600;
        margin-bottom: 10px;
        color: #1E3A8A;
        font-size: 1.1rem;
    }
    .source-link {
        color: #2563EB;
        text-decoration: none;
        font-size: 0.9rem;
        display: inline-block;
        margin-bottom: 10px;
        background-color: #EFF6FF;
        padding: 4px 8px;
        border-radius: 4px;
    }
    .source-link:hover {
        text-decoration: underline;
        background-color: #DBEAFE;
    }
    .piaget-image {
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stTextInput>div>div>input {
        border-radius: 10px;
    }
    .stButton>button {
        border-radius: 10px;
        background-color: #1E3A8A;
        color: white;
        font-weight: 500;
    }
    .stButton>button:hover {
        background-color: #1E40AF;
    }
    .thinking {
        font-style: italic;
        color: #6B7280;
    }
    .sidebar-content {
        padding: 0px 10px;
        margin-top: -40px;
    }
    /* Supprimer les marges et paddings de la sidebar */
    .css-1d391kg, .css-12oz5g7 {
        padding-top: 0 !important;
    }
    .block-container {
        padding-top: 0 !important;
    }
    .citation {
        font-style: italic;
        background-color: #F8FAFC;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 3px solid #3B82F6;
        line-height: 1.6;
        color: #1F2937;
        font-weight: 400;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    .source-number {
        font-weight: 700;
        color: #1E3A8A;
        margin-right: 5px;
    }
    
    /* Styles pour les volets dépliables dans la page principale */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #1E3A8A;
        background-color: #F9FAFB;
        border-radius: 8px;
        padding: 5px 10px;
    }
    
    .streamlit-expanderContent {
        background-color: #F9FAFB;
        border-radius: 0 0 8px 8px;
        padding: 10px;
        margin-top: -10px;
        border: 1px solid #E5E7EB;
        border-top: none;
    }
    
    /* Espacement entre les colonnes de contrôles */
    .controls-container {
        margin-bottom: 20px;
    }
    
    /* Masquer le bouton de fermeture de la sidebar et empêcher qu'elle soit rétractable */
    button[kind="header"] {
        display: none !important;
    }
    
    /* Fixer la largeur de la sidebar pour qu'elle ne soit pas redimensionnable */
    section[data-testid="stSidebar"] {
        width: 300px !important;
        min-width: 300px !important;
        max-width: 300px !important;
        flex-shrink: 0 !important;
    }
    
    /* Assurer que la sidebar reste visible et ne peut pas être fermée */
    .css-1d391kg, .css-12oz5g7 {
        transform: none !important;
    }
    
    /* Supprimer les barres de défilement de la sidebar et empêcher le défilement */
    [data-testid="stSidebar"] > div:first-child {
        overflow: hidden !important;
    }
    
    /* Supprimer les barres de défilement du contenu de la sidebar */
    [data-testid="stSidebarContent"] {
        overflow: hidden !important;
    }
    
    /* Supprimer les barres de défilement de tous les conteneurs dans la sidebar */
    .sidebar .block-container {
        overflow: hidden !important;
    }
    
    /* Ajuster la hauteur du contenu pour éviter le débordement */
    [data-testid="stSidebarUserContent"] {
        height: auto !important;
        max-height: 100vh !important;
    }
</style>
""", unsafe_allow_html=True)

# Fonction pour analyser et formater les sources avec des liens cliquables
def format_sources_with_links(sources_text):
    """
    Analyse le texte des sources et le formate avec des liens cliquables et une meilleure présentation.
    """
    # Vérifier si le texte des sources est vide
    if not sources_text.strip():
        return "Aucune source disponible."
    
    # Supprimer le préfixe "SOURCES :" ou "SOURCES:" s'il existe
    if sources_text.startswith("SOURCES :") or sources_text.startswith("SOURCES:"):
        sources_text = sources_text[9:].strip()
    
    # Diviser le texte en sources individuelles (numérotées)
    sources_html = ""
    
    # Diviser le texte en sources individuelles
    source_blocks = []
    lines = sources_text.split('\n')
    current_block = ""
    
    for line in lines:
        if line.strip() and any(line.strip().startswith(str(i) + ".") for i in range(1, 20)):
            if current_block:
                source_blocks.append(current_block.strip())
            current_block = line
        else:
            current_block += "\n" + line if current_block else line
    
    if current_block:
        source_blocks.append(current_block.strip())
    
    print(f"[DEBUG] Nombre de blocs de sources détectés: {len(source_blocks)}")
    
    # Formater chaque source
    for i, source in enumerate(source_blocks):
        # Extraire le numéro de la source (mais ne pas l'afficher)
        source_num = i + 1
        
        # Nettoyer la source en supprimant le numéro au début et les préfixes "SOURCES"
        cleaned_source = re.sub(r'^\d+\.\s*', '', source).strip()
        # Supprimer également les préfixes comme "SOURCES1." ou "SOURCES:" qui pourraient se retrouver dans le titre
        cleaned_source = re.sub(r'^SOURCES\d*\.?\s*', '', cleaned_source).strip()
        cleaned_source = re.sub(r'^SOURCES\s*:\s*', '', cleaned_source).strip()
        
        # Extraire la citation (tout ce qui est entre guillemets)
        citation_match = re.search(r'"([^"]+)"', cleaned_source)
        citation = ""
        if citation_match:
            citation = citation_match.group(1).strip()
            # Supprimer la citation du texte restant pour l'analyse
            remaining_text = cleaned_source.replace(citation_match.group(0), "").strip()
        else:
            remaining_text = cleaned_source
        
        # Extraire le titre et la date
        # Chercher un pattern comme "Titre (1972)" ou "- Titre (1972)"
        title_date_match = re.search(r'[-–—]?\s*([^\(]+)\s*\((\d{4})\)', remaining_text)
        
        title = ""
        date = ""
        url = ""
        
        if title_date_match:
            title = title_date_match.group(1).strip()
            # Nettoyer le titre des préfixes indésirables
            title = re.sub(r'^SOURCES\d*\.?\s*', '', title).strip()
            title = re.sub(r'^[-–—]\s*', '', title).strip()
            date = title_date_match.group(2).strip()
            
            # Chercher l'URL après le titre et la date
            after_title_date = remaining_text[remaining_text.find(title_date_match.group(0)) + len(title_date_match.group(0)):]
            url_match = re.search(r'(https?://\S+)', after_title_date)
            if url_match:
                url = url_match.group(1).strip()
        else:
            # Essayer un pattern plus simple pour la date seule
            date_match = re.search(r'\((\d{4})\)', remaining_text)
            if date_match:
                date = date_match.group(1).strip()
                
                # Essayer de trouver le titre avant la date
                before_date = remaining_text[:remaining_text.find(date_match.group(0))].strip()
                if before_date:
                    # Supprimer les tirets, préfixes SOURCES, et autres séparateurs
                    title = before_date.strip('- ').strip()
                    title = re.sub(r'^SOURCES\d*\.?\s*', '', title).strip()
                    title = re.sub(r'^[-–—]\s*', '', title).strip()
            
            # Chercher l'URL
            url_match = re.search(r'(https?://\S+)', remaining_text)
            if url_match:
                url = url_match.group(1).strip()
        
        print(f"[DEBUG] Source {i+1}: titre='{title}', date='{date}', citation='{citation[:50]}...'")
        
        # Créer le HTML pour cette source
        sources_html += f"<div class='source-item'>\n"
        
        # Afficher le titre et la date
        if title and date:
            sources_html += f"<div class='source-header'>{title} ({date})</div>\n"
        elif title:
            sources_html += f"<div class='source-header'>{title}</div>\n"
        elif date:
            sources_html += f"<div class='source-header'>Ouvrage de {date}</div>\n"
        else:
            sources_html += f"<div class='source-header'>Source {source_num}</div>\n"
        
        # Afficher le lien vers la source si disponible
        if url:
            sources_html += f"<a href='{url}' target='_blank' class='source-link'>Lien vers la source</a>\n"
        
        # Afficher la citation
        if citation:
            # Nettoyer la citation (enlever les guillemets supplémentaires)
            clean_citation = citation.replace('"', '').replace('\"', '').strip('. ')
            sources_html += f"<div class='citation'>\"{clean_citation}\"</div>\n"
        else:
            # Si pas de citation extraite, utiliser le texte sans les métadonnées
            # Supprimer le titre, la date et l'URL
            clean_text = cleaned_source
            if title:
                clean_text = clean_text.replace(title, "").strip()
            if date:
                clean_text = clean_text.replace(f"({date})", "").strip()
            if url:
                clean_text = clean_text.replace(url, "").strip()
            # Nettoyer les séparateurs restants
            clean_text = re.sub(r'[-–—]\s*', '', clean_text).strip()
            if clean_text:
                sources_html += f"<div class='citation'>{clean_text}</div>\n"
        
        sources_html += "</div>\n"
    
    return sources_html

# Fonction pour initialiser l'état de session
def init_session_state():
    # Initialiser les variables d'état de session si elles n'existent pas déjà
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ""
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Historique temporaire pour l'affichage pendant la réflexion
    if 'temp_history' not in st.session_state:
        st.session_state.temp_history = []
    
    # Mode d'affichage ("temp" pour afficher uniquement la question actuelle, "history" pour l'historique complet)
    if 'display_mode' not in st.session_state:
        st.session_state.display_mode = "history"

# Fonction pour traiter la question et obtenir une réponse
def process_question(question):
    if not question.strip():
        return
    
    # Vider l'historique temporaire (pour n'afficher que la question actuelle)
    st.session_state.temp_history = []
    
    # Ajouter la question à l'historique temporaire
    st.session_state.temp_history.append({"role": "user", "content": question})
    
    # Ajouter la question à l'historique permanent
    st.session_state.chat_history.append({"role": "user", "content": question})
    
    # Vérifier si la clé API est fournie
    if not st.session_state.api_key:
        error_message = "Veuillez entrer votre clé API OpenAI dans l'onglet API des paramètres pour pouvoir utiliser PiaGPT."
        st.session_state.chat_history.append({"role": "assistant", "content": error_message})
        st.session_state.temp_history.append({"role": "assistant", "content": error_message})
        st.session_state.display_mode = "history"
        st.rerun()
        return
    
    # Initialiser le système RAG si nécessaire
    if 'piaget_rag' not in st.session_state or st.session_state.piaget_rag is None:
        try:
            st.session_state.piaget_rag = PiagetRAG(model_name=st.session_state.current_model, api_key=st.session_state.api_key)
        except Exception as e:
            error_message = f"Erreur lors de l'initialisation du système RAG: {str(e)}"
            st.session_state.chat_history.append({"role": "assistant", "content": error_message})
            st.session_state.temp_history.append({"role": "assistant", "content": error_message})
            st.session_state.display_mode = "history"
            st.rerun()
            return
    
    # Obtenir la réponse du système RAG
    try:
        raw_answer = st.session_state.piaget_rag.answer_question(question)
        formatted_answer = format_response(raw_answer)
    except Exception as e:
        formatted_answer = f"Erreur lors de la génération de la réponse: {str(e)}"
    
    # Ajouter la réponse à l'historique permanent
    st.session_state.chat_history.append({"role": "assistant", "content": formatted_answer})
    
    # Basculer vers l'affichage de l'historique complet
    st.session_state.display_mode = "history"
    
    # Forcer le rechargement de la page pour afficher la réponse dans l'historique
    st.rerun()

# CSS pour supprimer l'espace en haut de la sidebar
st.markdown("""
<style>
    div[data-testid="stSidebarUserContent"] > div:first-child {
        margin-top: -60px !important;
        padding-top: 10px !important;
    }
    /* Supprimer complètement l'espace entre l'image et le texte */
    .element-container:has(img) + .element-container {
        margin-top: -35px !important;
    }
    /* Réduire l'espace entre les éléments de la sidebar */
    .sidebar-content p {
        margin-bottom: 0.5em !important;
        margin-top: 0.5em !important;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar avec informations sur Jean Piaget
def render_sidebar():
    with st.sidebar:
        # Réduire légèrement la taille de l'image pour éviter le défilement
        st.image("static/piaget.jpg", 
                 caption="Jean Piaget", 
                 width=250)
        
        st.markdown("<div class='sidebar-content'>", unsafe_allow_html=True)
        
        st.markdown("""
        ## À propos de Jean Piaget
        
        Psychologue, biologiste et épistémologue suisse (1896-1980), pionnier du développement cognitif des enfants.
        
        ### Contributions:
        - Théorie du développement cognitif
        - Concept d'équilibration
        - Épistémologie génétique
        - Stades du développement
        
        Posez vos questions pour explorer sa pensée.
        """)
        
        st.markdown("</div>", unsafe_allow_html=True)

# Fonction pour afficher les paramètres du système
def render_model_controls():
    # Définir les modèles disponibles avec leurs descriptions
    models = {
    "gpt-4.1": "Modèle phare d'OpenAI, excelle en programmation, suivi d'instructions complexes et compréhension de longs contextes (jusqu'à 1 million de tokens). Idéal pour les systèmes RAG exigeants.",
    "gpt-4.1-mini": "Version allégée de GPT-4.1, offrant un excellent équilibre entre performance et coût. Parfait pour des applications nécessitant rapidité et efficacité.",
    "gpt-4.1-nano": "Le modèle le plus rapide et économique d'OpenAI, adapté aux tâches simples ou aux applications à grande échelle avec contraintes budgétaires.",
    "gpt-4o": "Modèle multimodal capable de traiter texte, images et audio. Idéal pour des interactions riches et variées, avec une performance supérieure en langues non anglaises.",
    "gpt-4.5": "Modèle avancé offrant une meilleure fluidité conversationnelle et une réduction significative des hallucinations. Convient aux applications nécessitant des interactions naturelles.",
    "o3": "Modèle de raisonnement avancé, conçu pour des tâches complexes en sciences, mathématiques et programmation. Utilise une approche de chaîne de pensée pour des réponses plus précises."
    }
    
    # Conteneur pour les contrôles avec classe CSS personnalisée
    st.markdown("<div class='controls-container'></div>", unsafe_allow_html=True)
    
    # Volet unique pour les paramètres
    with st.expander("⚙️   Paramètres", expanded=False):
        # Créer des onglets pour les différentes sections
        tab_api, tab_model, tab_info = st.tabs(["API", "Modèle", "Informations"])
        
        # Onglet API
        with tab_api:
            # Récupérer la clé API depuis l'état de session ou initialiser vide
            if 'api_key' not in st.session_state:
                st.session_state.api_key = ""
                
            # Fonction pour mettre à jour la clé API
            def on_api_key_change():
                # Mettre à jour la clé API dans l'état de session
                if 'piaget_rag' in st.session_state:
                    # Supprimer l'instance RAG existante pour forcer sa réinitialisation avec la nouvelle clé
                    st.session_state.pop('piaget_rag')
            
            # Champ de saisie pour la clé API
            api_key = st.text_input(
                "Clé API OpenAI :",
                value=st.session_state.api_key,
                type="password",
                key="api_key_input",
                on_change=on_api_key_change
            )
            
            # Mettre à jour la clé API dans l'état de session
            st.session_state.api_key = api_key
            
            # Afficher un message d'information
            st.info("Entrez votre clé API OpenAI pour utiliser le service. Vous pouvez obtenir une clé sur le site d'OpenAI : https://platform.openai.com/api-keys")
        
        # Onglet Modèle
        with tab_model:
            # Utiliser un callback pour gérer le changement de modèle
            def on_model_change():
                # Récupérer le modèle sélectionné depuis l'état de session
                selected = st.session_state.model_selection
                
                # Vérifier si le modèle a changé
                if 'current_model' in st.session_state and st.session_state.current_model != selected:
                    # Supprimer l'instance RAG existante pour forcer sa réinitialisation
                    if 'piaget_rag' in st.session_state:
                        st.session_state.pop('piaget_rag')
                    # Mettre à jour le modèle actuel
                    st.session_state.current_model = selected
                elif 'current_model' not in st.session_state:
                    st.session_state.current_model = selected
            
            # Sélection du modèle avec radio buttons et callback
            selected_model = st.radio(
                "Choisissez un modèle :",
                list(models.keys()),
                index=list(models.keys()).index(st.session_state.current_model) if 'current_model' in st.session_state else 0,
                key="model_selection",
                on_change=on_model_change
            )
            
            # Afficher la description du modèle sélectionné
            st.info(models[selected_model])
        
        # Onglet Informations
        with tab_info:
            st.write("Ce système utilise automatiquement le maximum de sources pertinentes pour répondre à vos questions sur la pensée de Jean Piaget.")
            st.write(f"**Modèle actuel** : {selected_model}")
            st.write("**Développé par** : Équipe PiaGPT")

# Fonction pour afficher des suggestions de questions structurées
def render_question_suggestions():
    # Structure des suggestions de questions par catégorie
    suggestions = {
        "🧠 Épistémologie génétique": [
            "Qu'est-ce que l'épistémologie génétique ?",
            "Pourquoi étudier le développement de la connaissance chez l'enfant ?",
            "Comment la connaissance scientifique évolue-t-elle selon vous ?",
            "Quelle est la différence entre épistémologie empirique et épistémologie génétique ?",
            "Comment vos recherches ont-elles influencé la théorie de la connaissance ?"
        ],
        "👶 Stades de développement cognitif": [
            "Pouvez-vous m'expliquer les différents stades du développement cognitif ?",
            "Pourquoi les enfants ne pensent-ils pas comme les adultes ?",
            "À quel âge un enfant développe-t-il la permanence de l'objet ?",
            "Pourquoi le stade opératoire concret est-il une étape clé ?",
            "Comment reconnaître si un enfant est à un stade préopératoire ou opératoire concret ?"
        ],
        "🧪 Méthodologie et observations": [
            "Comment meniez-vous vos expériences avec les enfants ?",
            "Quelle est l'importance du dialogue clinique dans vos recherches ?",
            "Quelles erreurs méthodologiques faut-il éviter en étudiant l'intelligence chez l'enfant ?",
            "Peut-on vraiment généraliser les résultats de vos observations ?"
        ],
        "🧠 Structures de la pensée et schèmes": [
            "Qu'est-ce qu'un schème selon vous ?",
            "Comment les schèmes se forment-ils et évoluent-ils ?",
            "Quelle est la différence entre assimilation et accommodation ?",
            "Comment les structures mentales influencent-elles le comportement de l'enfant ?"
        ],
        "🌍 Construction de la réalité chez l'enfant": [
            "Comment un enfant construit-il sa représentation du monde ?",
            "Qu'est-ce que la décentration ?",
            "En quoi l'égocentrisme de l'enfant diffère-t-il de l'égoïsme ?",
            "Comment un enfant passe-t-il de la perception à la logique ?"
        ],
        "📚 Éducation et pédagogie": [
            "Quelle pédagogie recommandez-vous pour respecter le développement cognitif ?",
            "Comment l'école peut-elle aider à construire l'intelligence ?",
            "Que pensez-vous de l'apprentissage par découverte ?",
            "Comment enseigner les mathématiques selon vos travaux ?"
        ],
        "🧩 Langage et pensée": [
            "Le langage précède-t-il la pensée ou l'inverse ?",
            "Comment les structures du langage reflètent-elles les structures de pensée ?",
            "Pourquoi pensez-vous que le langage ne crée pas l'intelligence mais l'accompagne ?"
        ],
        "📈 Comparaison avec d'autres penseurs": [
            "Quelle est votre opinion sur Lev Vygotsky ?",
            "En quoi votre théorie diffère-t-elle du behaviorisme ?",
            "Avez-vous été influencé par Freud ou par les empiristes ?",
            "Que pensez-vous de l'intelligence artificielle ?"
        ],
        "💬 Réflexions générales ou philosophiques": [
            "Qu'est-ce que la connaissance selon vous ?",
            "Pensez-vous qu'il existe une vérité absolue ?",
            "Quelle est votre définition de l'intelligence ?",
            "Quel a été votre objectif tout au long de votre carrière ?"
        ],
        "🔁 Interactions libres": [
            "Peux-tu m'aider à comprendre comment un enfant apprend ?",
            "Donne-moi un exemple d'assimilation et d'accommodation.",
            "Imagine une conversation entre toi et un enfant de 4 ans : que remarques-tu ?",
            "Selon toi, comment devrions-nous repenser l'éducation aujourd'hui ?"
        ]
    }
    
    # CSS personnalisé pour les suggestions
    st.markdown("""
    <style>
    .suggestion-category {
        margin-bottom: 10px;
    }
    .suggestion-question {
        cursor: pointer;
        padding: 5px 10px;
        margin: 5px 0;
        border-radius: 5px;
        background-color: #f0f2f6;
        transition: background-color 0.3s;
    }
    .suggestion-question:hover {
        background-color: #e0e2e6;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Afficher l'expandeur pour les suggestions
    with st.expander("💬 Suggestions de questions", expanded=False):
        # Créer des onglets pour les catégories
        tabs = st.tabs(list(suggestions.keys()))
        
        # Pour chaque catégorie, afficher les questions
        for i, (category, questions) in enumerate(suggestions.items()):
            with tabs[i]:
                for question in questions:
                    # Créer un bouton pour chaque question
                    if st.button(question, key=f"btn_{category}_{question}", use_container_width=True):
                        # Stocker la question sélectionnée dans l'état de session
                        st.session_state.selected_question = question
                        # Forcer le rechargement de la page pour traiter la question
                        st.rerun()

# Page principale
def main():
    # Initialiser l'état de session
    init_session_state()
    
    # Afficher la sidebar
    render_sidebar()
    
    # Créer une disposition avec deux colonnes: titre à gauche, contrôles à droite
    col_title, col_controls = st.columns([0.6, 0.4])
    
    # Colonne de gauche: En-tête
    with col_title:
        st.markdown("<h1 class='main-header'>PiaGPT - L'avatar virtuel de Jean Piaget</h1>", unsafe_allow_html=True)
        st.markdown("<p class='sub-header'>Posez vos questions à Jean Piaget et explorez sa pensée à travers ses écrits</p>", unsafe_allow_html=True)
    
    # Colonne de droite: Contrôles de modèle et informations système
    with col_controls:
        render_model_controls()
    
    # Conteneur pour le chat
    chat_container = st.container()
    
    # Afficher les suggestions de questions avant la zone de saisie
    render_question_suggestions()
    
    # Zone de saisie pour la question (placée en bas)
    user_question = st.chat_input("Posez votre question à Jean Piaget...")
    
    # Vérifier s'il y a une question sélectionnée depuis les suggestions
    if 'selected_question' in st.session_state:
        question_to_process = st.session_state.selected_question
        # Supprimer la question sélectionnée de l'état de session pour éviter de la retraiter
        del st.session_state.selected_question
    else:
        question_to_process = user_question
    
    # Afficher les messages dans le conteneur de chat
    with chat_container:
        # Déterminer quel historique afficher en fonction du mode
        display_history = st.session_state.temp_history if st.session_state.display_mode == "temp" else st.session_state.chat_history
        
        # Afficher l'historique approprié
        for message in display_history:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(message["content"])
            else:
                with st.chat_message("assistant", avatar="🧠"):
                    # Séparer la réponse et les sources
                    if "=" * 50 in message["content"]:
                        main_response, sources_text = message["content"].split("=" * 50)
                        st.markdown(main_response.strip())
                        
                        with st.expander("Sources et Citations", expanded=True):
                            formatted_sources = format_sources_with_links(sources_text.strip())
                            st.markdown(formatted_sources, unsafe_allow_html=True)
                    else:
                        st.markdown(message["content"])
    
    # Traiter la question si elle existe (soit depuis la saisie, soit depuis les suggestions)
    if question_to_process:
        # Afficher immédiatement la question et l'indicateur de réflexion
        with chat_container:
            # Afficher la question de l'utilisateur
            with st.chat_message("user"):
                st.markdown(question_to_process)
            
            # Vérifier si une clé API a été fournie
            if not st.session_state.api_key:
                with st.chat_message("assistant", avatar="🧠"):
                    st.error("Veuillez entrer votre clé API OpenAI dans l'onglet API des paramètres pour pouvoir utiliser PiaGPT.")
            else:
                # Afficher l'indicateur de réflexion
                with st.chat_message("assistant", avatar="🧠"):
                    st.markdown("<p class='thinking'>Jean Piaget réfléchit...</p>", unsafe_allow_html=True)
                
                # Basculer en mode temporaire pour n'afficher que la question en cours
                st.session_state.display_mode = "temp"
                process_question(question_to_process)

if __name__ == "__main__":
    main()
