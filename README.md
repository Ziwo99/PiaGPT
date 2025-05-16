# PiaGPT - L'avatar virtuel de Jean Piaget

PiaGPT est un système avancé de Retrieval-Augmented Generation (RAG) qui vous permet d'interagir avec un avatar virtuel de Jean Piaget. L'avatar répond aux questions en se basant sur les textes authentiques de Piaget, parle à la première personne et cite précisément les sources pertinentes.

![Interface PiaGPT](static/piaget.jpg)

## Fonctionnalités

- **Interface web intuitive** : Interface utilisateur moderne et responsive développée avec Streamlit
- **Recherche sémantique avancée** : Utilise OpenAI Embeddings pour une recherche précise dans les textes de Piaget
- **Génération de réponses personnalisées** : Utilise les modèles OpenAI (GPT-4.1, GPT-4.1-mini, GPT-4.1-nano, GPT-4o, GPT-4.5, o3) pour générer des réponses à la première personne
- **Citations précises** : Inclut des citations pertinentes avec titre, date et extrait des œuvres originales
- **Suggestions de questions** : Propose des questions thématiques pour explorer la pensée de Piaget
- **Sélection de modèle** : Permet de choisir entre différents modèles OpenAI selon vos besoins
- **Mécanismes de secours robustes** : Gestion des erreurs et alternatives en cas de problème avec l'API

## Corpus des œuvres de Jean Piaget

Le système s'appuie sur une vaste collection de **1081 œuvres** de Jean Piaget, couvrant l'ensemble de sa carrière. Ces textes ont été collectés à partir du site officiel des œuvres de Jean Piaget (oeuvres.unige.ch) et incluent :

- Ses premiers écrits scientifiques sur la malacologie (étude des mollusques)
- Ses travaux fondamentaux sur le développement cognitif de l'enfant
- Ses études sur l'épistémologie génétique
- Ses publications sur la psychologie et la pédagogie
- Ses réflexions philosophiques et théoriques

Chaque document dans la base de données contient le titre de l'œuvre, sa date de publication, le texte intégral et l'URL source, permettant une attribution précise des citations.

## Architecture du système

PiaGPT est structuré en trois composants principaux :

### 1. Collecte des données (`data_scrap.py`)

- Utilise Selenium et BeautifulSoup pour extraire les textes depuis oeuvres.unige.ch
- Nettoie et normalise les textes (suppression des balises HTML, normalisation des espaces)
- Extrait les métadonnées (titre, date) de chaque œuvre
- Sauvegarde les données dans un fichier JSON structuré (`piaget_data.json`)

### 2. Prétraitement des données (`data_preprocess.py`)

- Charge les données JSON contenant les textes de Piaget
- Divise les textes en chunks pour une recherche efficace (1000 caractères par défaut)
- Génère les embeddings avec Sentence-Transformers (`paraphrase-multilingual-MiniLM-L12-v2`)
- Crée un index FAISS pour la recherche vectorielle rapide
- Sauvegarde l'index et les métadonnées des documents dans le dossier `data/processed/`

### 3. Moteur RAG (`piaget_rag_engine.py`)

- Charge les données prétraitées (index FAISS et documents)
- Utilise OpenAI Embeddings pour encoder les requêtes utilisateur
- Recherche les passages les plus pertinents dans les textes de Piaget
- Génère des réponses contextuelles avec le modèle OpenAI sélectionné
- Formate les réponses avec citations et sources
- Inclut des mécanismes de secours en cas d'erreur avec l'API

### 4. Interface utilisateur (`web_interface.py`)

- Interface web moderne développée avec Streamlit
- Affichage des réponses avec mise en forme des citations
- Panneau latéral fixe (300px) avec informations sur Jean Piaget
- Contrôles pour la sélection du modèle et la configuration de l'API dans des volets dépliables
- Suggestions de questions thématiques organisées par catégories

## Installation

1. Clonez ce dépôt ou téléchargez les fichiers
2. Installez les dépendances :

```bash
pip install -r requirements.txt
```

## Utilisation

### Prétraitement des données (si nécessaire)

Si vous avez modifié les données source ou souhaitez recréer l'index :

```bash
python data_preprocess.py
```

### Interface en ligne de commande

Pour utiliser PiaGPT en mode console :

```bash
python piaget_rag_engine.py
```

### Interface web (recommandée)

Pour lancer l'interface web de PiaGPT :

```bash
streamlit run web_interface.py
```

L'interface web sera accessible à l'adresse http://localhost:8501 par défaut.

## Structure du projet

- `data/` : Répertoire contenant les données
  - `piaget_data.json` : Fichier JSON (45 Mo) contenant les 1081 textes de Jean Piaget
  - `processed/` : Données prétraitées
    - `piaget_index.faiss` : Index vectoriel pour la recherche sémantique
    - `piaget_documents.pkl` : Métadonnées des documents et chunks
- `static/` : Ressources statiques
  - `piaget.jpg` : Photo de Jean Piaget utilisée dans l'interface
- `piaget_rag_engine.py` : Moteur RAG principal avec la classe `PiagetRAG`
- `web_interface.py` : Interface web Streamlit avec toutes les fonctionnalités UI
- `data_preprocess.py` : Script de prétraitement pour générer l'index FAISS
- `data_scrap.py` : Script de scraping pour collecter les textes depuis oeuvres.unige.ch
- `requirements.txt` : Liste des dépendances Python

## Dépendances principales

- **langchain** : Framework pour construire des applications avec LLMs
- **langchain-openai** : Intégration OpenAI pour LangChain
- **sentence-transformers** : Modèles pour générer des embeddings multilingues
- **faiss-cpu** : Bibliothèque pour la recherche vectorielle efficace
- **openai** : API officielle OpenAI pour les modèles GPT
- **streamlit** : Framework pour créer l'interface web
- **selenium** et **beautifulsoup4** : Outils pour le scraping web

## Modèles disponibles

PiaGPT vous permet de choisir entre différents modèles OpenAI :

- **GPT-4.1** : Modèle phare d'OpenAI, excelle en programmation, suivi d'instructions complexes et compréhension de longs contextes
- **GPT-4.1-mini** : Version allégée de GPT-4.1, offrant un excellent équilibre entre performance et coût
- **GPT-4.1-nano** : Le modèle le plus rapide et économique d'OpenAI, adapté aux tâches simples ou aux applications à grande échelle
- **GPT-4o** : Modèle multimodal capable de traiter texte, images et audio, avec une performance supérieure en langues non anglaises
- **GPT-4.5** : Modèle avancé offrant une meilleure fluidité conversationnelle et une réduction des hallucinations
- **o3** : Modèle de raisonnement avancé, conçu pour des tâches complexes en sciences, mathématiques et programmation

## Configuration de l'API

Vous pouvez configurer votre clé API OpenAI directement dans l'interface web, dans le volet "Paramètres API". La clé est stockée uniquement dans la session Streamlit et n'est pas sauvegardée entre les sessions.

## Personnalisation

Vous pouvez ajuster plusieurs paramètres dans le système :

- **Paramètres de chunking** : Modifiez `chunk_size` et `chunk_overlap` dans `data_preprocess.py`
- **Nombre de documents** : Ajustez le paramètre `k` dans `piaget_rag_engine.py`
- **Seuil de similarité** : Modifiez `similarity_threshold` pour filtrer les résultats peu pertinents
- **Prompt système** : Personnalisez le template de prompt dans `_create_prompt_template()`
- **Interface utilisateur** : Modifiez les styles CSS dans `web_interface.py`

## Fonctionnement du RAG

1. **Indexation** : Les textes de Piaget sont divisés en chunks et transformés en vecteurs (embeddings)
2. **Recherche** : Lorsqu'une question est posée, elle est également transformée en vecteur
3. **Récupération** : Les chunks les plus similaires à la question sont récupérés via l'index FAISS
4. **Génération** : Les chunks pertinents sont intégrés dans un prompt envoyé au modèle OpenAI
5. **Formatage** : La réponse est formatée pour séparer clairement le texte principal des citations
