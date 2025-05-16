import os
import pickle
from typing import List, Dict, Any
from dotenv import load_dotenv
import faiss
import numpy as np
# Remplacer SentenceTransformer par une solution plus stable
# from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain.schema import Document

# Charger les variables d'environnement (pour la compatibilité avec l'ancienne version)
load_dotenv()

# Vérifier que les fichiers prétraités existent
PROCESSED_DIR = "data/processed"
INDEX_PATH = os.path.join(PROCESSED_DIR, "piaget_index.faiss")
DOCUMENTS_PATH = os.path.join(PROCESSED_DIR, "piaget_documents.pkl")

if not os.path.exists(INDEX_PATH) or not os.path.exists(DOCUMENTS_PATH):
    print("Erreur: Fichiers prétraités non trouvés.")
    print("Veuillez d'abord exécuter le script preprocess.py pour générer les embeddings.")
    exit(1)

class PiagetRAG:
    def __init__(self, model_name="gpt-4.1-nano", api_key=None):
        """
        Initialise le système RAG pour Jean Piaget en chargeant les données prétraitées.
        """
        # Chargement de l'index FAISS et des documents
        self._load_preprocessed_data()
        
        # Vérifier si une clé API a été fournie
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        # Vérifier que la clé API est définie
        if not self.api_key:
            print("Avertissement: Aucune clé API OpenAI n'a été fournie.")
            print("Certaines fonctionnalités peuvent ne pas fonctionner correctement.")
        else:
            # Définir la clé API pour OpenAI
            os.environ["OPENAI_API_KEY"] = self.api_key
        
        # Initialisation du modèle d'embedding (uniquement pour les requêtes)
        print("Initialisation du système d'embedding...")
        
        # Utiliser OpenAI Embeddings au lieu de SentenceTransformer pour éviter les erreurs de segmentation
        try:
            # Utiliser OpenAI pour les embeddings (plus stable que SentenceTransformer)
            self.embedding_model = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=self.api_key)
            print("Modèle d'embedding OpenAI initialisé avec succès")
            
            # Créer un wrapper pour rendre l'interface compatible avec notre code existant
            class OpenAIEmbeddingWrapper:
                def __init__(self, openai_embeddings):
                    self.openai_embeddings = openai_embeddings
                
                def encode(self, texts, **kwargs):
                    # Convertir les embeddings OpenAI en format compatible avec FAISS
                    try:
                        # Obtenir les embeddings un par un pour éviter les erreurs
                        vectors = []
                        for text in texts:
                            embedding = self.openai_embeddings.embed_query(text)
                            vectors.append(embedding)
                        return np.array(vectors, dtype=np.float32)
                    except Exception as e:
                        print(f"Erreur lors de la création des embeddings OpenAI: {e}")
                        # Fallback en cas d'erreur
                        return self._fallback_encode(texts)
                
                def _fallback_encode(self, texts):
                    # Méthode de secours si OpenAI échoue
                    import numpy as np
                    vectors = []
                    for text in texts:
                        np.random.seed(hash(text) % 2**32)
                        vec = np.random.randn(1536)  # Dimension pour OpenAI embeddings
                        vec = vec / np.linalg.norm(vec)
                        vectors.append(vec)
                    return np.array(vectors, dtype=np.float32)
            
            # Wrapper pour l'interface compatible
            self.embedding_model = OpenAIEmbeddingWrapper(self.embedding_model)
            
        except Exception as e:
            print(f"Erreur lors de l'initialisation d'OpenAI Embeddings: {e}")
            print("Utilisation d'un modèle d'embedding de secours simple")
            
            # Créer une classe d'embedding simplifiée comme solution de dernier recours
            class SimpleEmbedder:
                def encode(self, texts, **kwargs):
                    # Retourner des vecteurs aléatoires mais cohérents (basés sur le hash du texte)
                    import numpy as np
                    vectors = []
                    for text in texts:
                        # Générer un vecteur basé sur le hash du texte pour la cohérence
                        np.random.seed(hash(text) % 2**32)
                        vec = np.random.randn(384)  # Dimension standard pour ce modèle
                        # Normaliser
                        vec = vec / np.linalg.norm(vec)
                        vectors.append(vec)
                    return np.array(vectors, dtype=np.float32)
            
            self.embedding_model = SimpleEmbedder()
        
        # Initialisation du LLM avec le modèle spécifié
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=0.3,
            openai_api_key=self.api_key
        )
        
        # Stocker le nom du modèle pour référence
        self.model_name = model_name
        
        # Création du template de prompt
        self.prompt_template = self._create_prompt_template()
    
    def _load_preprocessed_data(self):
        """Charge l'index FAISS et les documents prétraités."""
        # Chargement de l'index FAISS
        self.index = faiss.read_index(INDEX_PATH)
        print(f"Index FAISS chargé avec {self.index.ntotal} vecteurs")
        
        # Chargement des documents
        with open(DOCUMENTS_PATH, 'rb') as f:
            self.documents = pickle.load(f)
        print(f"Documents chargés: {len(self.documents)} chunks")
        
        # Vérifier que les documents ont bien l'URL dans leurs métadonnées
        for doc in self.documents:
            if 'url' not in doc.metadata:
                doc.metadata['url'] = ""  # Ajouter une URL vide si elle n'existe pas
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Crée le template de prompt pour le LLM."""
        template = """
        Tu es Jean Piaget, célèbre psychologue, biologiste et épistémologue suisse. 
        Tu réponds aux questions en te basant sur tes propres écrits et ta pensée.
        Tu parles toujours à la première personne (je, me, mon, etc.) comme si tu étais Jean Piaget lui-même.
        
        Voici des extraits de tes textes pertinents pour répondre à la question :
        
        {context}
        
        INSTRUCTIONS IMPORTANTES:
        1. Ta réponse DOIT contenir EXACTEMENT deux sections séparées par une ligne vide: "RÉPONSE" et "SOURCES". 
        2. La section SOURCES doit contenir au moins 3 citations différentes (si possible).
        3. Utilise UNIQUEMENT les informations fournies dans les extraits ci-dessus.
        4. Pour chaque source citée, inclus un passage COMPLET et SIGNIFICATIF qui apporte une information pertinente.
        5. Les citations doivent être des extraits compréhensibles et cohérents, pas des fragments incomplets.
        
        Format obligatoire de ta réponse:
        
        RÉPONSE
        [Ta réponse détaillée à la première personne, sans citer directement les sources]
        
        SOURCES
        1. "[Citation exacte et complète - au moins une phrase entière]" - [Titre exact] ([Date]) - [URL]
        2. "[Citation exacte et complète - au moins une phrase entière]" - [Titre exact] ([Date]) - [URL]
        3. "[Citation exacte et complète - au moins une phrase entière]" - [Titre exact] ([Date]) - [URL]
        [etc. si plus de citations]
        
        Pour les citations, utilise les extraits précédés de ### SOURCE: dans le texte fourni. Tu peux utiliser soit le texte de la section TEXTE: pour des citations courtes, soit des extraits pertinents de la section CONTEXTE COMPLET: pour des citations plus complètes et significatives. Indique toujours le titre et la date exactement comme indiqués après ### SOURCE:.
        
        Question: {question}
        
        Réponse (en tant que Jean Piaget):
        """
        
        return ChatPromptTemplate.from_template(template)
    
    def search(self, query: str, k: int = 8, similarity_threshold: float = 0.6) -> List[Document]:
        """
        Recherche les documents les plus pertinents pour une requête donnée.
        
        Args:
            query: La requête de recherche
            k: Nombre maximum de documents à retourner
            similarity_threshold: Seuil de similarité minimum pour filtrer les résultats
            
        Returns:
            Liste de tuples (document, score de similarité)
        """
        print(f"\n[DEBUG] Recherche pour la requête: '{query}'")
        print(f"[DEBUG] Paramètres: k={k}, seuil={similarity_threshold}")
        
        try:
            # Méthode sécurisée pour créer l'embedding de la requête
            try:
                # Utiliser notre modèle d'embedding (OpenAI ou fallback)
                print(f"[DEBUG] Création de l'embedding pour la requête: '{query}'")
                query_embedding = self.embedding_model.encode([query])
                
                # Vérifier que l'embedding est valide
                if isinstance(query_embedding, np.ndarray):
                    print(f"[DEBUG] Embedding créé avec succès, dimensions: {query_embedding.shape}")
                else:
                    # Convertir en numpy array si ce n'est pas déjà le cas
                    query_embedding = np.array(query_embedding, dtype=np.float32)
                    print(f"[DEBUG] Embedding converti en numpy array, dimensions: {query_embedding.shape}")
            except Exception as e:
                print(f"[DEBUG] Erreur lors de la création de l'embedding: {e}")
                # Fallback: utiliser une méthode alternative
                import numpy as np
                # Créer un vecteur aléatoire mais déterministe basé sur le hash de la requête
                np.random.seed(hash(query) % 2**32)
                query_embedding = np.random.randn(1, 1536)  # Dimension pour OpenAI embeddings
                # Normaliser
                query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
                print(f"[DEBUG] Embedding de secours créé, dimensions: {query_embedding.shape}")
            
            # Normalisation (s'assurer que c'est un tableau numpy)
            query_embedding = np.array(query_embedding, dtype=np.float32)
            faiss.normalize_L2(query_embedding)
            
            # Recherche d'un nombre plus élevé de documents pour pouvoir filtrer ensuite
            # Nous cherchons k*3 documents pour avoir une large marge de filtrage
            search_k = min(k * 3, self.index.ntotal)  # Éviter de demander plus que le nombre total de documents
            print(f"[DEBUG] Recherche des {search_k} documents les plus proches")
            scores, indices = self.index.search(query_embedding, search_k)
        except Exception as e:
            print(f"[DEBUG] Erreur critique lors de la recherche: {e}")
            # Récupération d'urgence: sélectionner des documents aléatoires
            import numpy as np
            import random
            print("[DEBUG] Sélection de documents aléatoires comme solution de secours")
            
            # Sélectionner k documents aléatoires
            random_indices = random.sample(range(len(self.documents)), min(k, len(self.documents)))
            indices = np.array([random_indices])
            scores = np.array([[0.5] * len(random_indices)])  # Scores fictifs
        
        # Récupération des documents avec filtrage par score de similarité
        results = []
        print(f"[DEBUG] Scores et similarités des documents trouvés:")
        
        # Ensemble pour suivre les titres uniques (pour éviter la redondance)
        unique_titles = set()
        
        for i, idx in enumerate(indices[0]):
            if idx != -1:  # FAISS peut retourner -1 si moins de résultats sont trouvés
                score = scores[0][i]
                # Convertir le score FAISS (distance L2 normalisée) en similarité cosinus
                # Pour FAISS normalisé, similarité = 1 - distance^2/2
                similarity = 1 - (score ** 2) / 2
                
                doc = self.documents[idx]
                title = doc.metadata['title']
                
                # Afficher les informations de débogage
                if i < 15:  # Afficher plus de résultats pour le débogage
                    print(f"[DEBUG] Doc {i+1}: score={score:.4f}, similarité={similarity:.4f}, titre='{title}', date={doc.metadata['date']}")
                
                # Ne garder que les documents avec une similarité suffisante
                # et éviter trop de documents avec le même titre (max 2 par titre)
                if similarity >= similarity_threshold:
                    # Vérifier si nous avons déjà 2 documents avec ce titre
                    if title in unique_titles and sum(1 for d, _ in results if d.metadata['title'] == title) >= 2:
                        continue
                    
                    # Ajouter le document uniquement basé sur sa similarité
                    results.append((doc, similarity))
                    unique_titles.add(title)
                    
                    # Limiter le nombre total de documents à k
                    if len(results) >= k:
                        break
        
        # Trier les résultats par score de similarité décroissant
        results.sort(key=lambda x: x[1], reverse=True)
        
        print(f"[DEBUG] Nombre de documents retenus après filtrage: {len(results)}")
        
        # Afficher les titres des documents retenus
        print("[DEBUG] Documents retenus:")
        for i, (doc, similarity) in enumerate(results):
            print(f"[DEBUG] {i+1}. '{doc.metadata['title']}' ({doc.metadata['date']}) - Similarité: {similarity:.4f}")
        
        return results
    
    def answer_question(self, question: str, k: int = 8) -> str:
        """
        Répond à une question en utilisant le RAG.
        
        Args:
            question: La question posée
            k: Nombre maximum de documents à utiliser (par défaut: 8)
            
        Returns:
            Réponse à la question
        """
        print(f"\n[DEBUG] Traitement de la question: '{question}'")
        
        # Abaisser le seuil de similarité pour obtenir plus de documents
        similarity_threshold = 0.5  # Réduit de 0.6 à 0.5 pour être moins sélectif
        print(f"[DEBUG] Seuil de similarité ajusté à {similarity_threshold}")
        
        # Recherche des documents pertinents avec un seuil de similarité
        results = self.search(question, k=k, similarity_threshold=similarity_threshold)
        
        if not results:
            return "Je ne trouve pas d'information pertinente dans mes écrits pour répondre à cette question."
        
        # Préparation du contexte avec une structure claire pour faciliter l'extraction des citations
        context_parts = []
        
        print(f"[DEBUG] Préparation du contexte avec {len(results)} documents")
        for i, (doc, similarity) in enumerate(results):
            title = doc.metadata['title']
            date = doc.metadata['date']
            url = doc.metadata.get('url', '')
            content = doc.page_content.strip()
            
            # Afficher un extrait du contenu pour débogage
            content_preview = content[:100] + "..." if len(content) > 100 else content
            print(f"[DEBUG] Document {i+1}: '{title}' - Extrait: '{content_preview}'")
            
            # Formater chaque source avec des balises claires et un format plus lisible
            # Extraire un passage significatif du contenu (max 200 caractères)
            if len(content) > 200:
                # Essayer de couper à la fin d'une phrase
                cutoff = content[:200].rfind('.')
                if cutoff > 100:  # S'assurer qu'on a un extrait suffisamment long
                    content_extract = content[:cutoff+1]
                else:
                    content_extract = content[:200] + "..."
            else:
                content_extract = content
                
            source_block = f"""### SOURCE: \"{title}\" ({date})
URL: {url}
TEXTE:
\"{content_extract}\"

CONTEXTE COMPLET:
{content}"""
            
            context_parts.append(source_block)
        
        # Joindre toutes les sources avec une séparation claire
        context = "\n\n" + "\n\n".join(context_parts)
        
        # Afficher la taille du contexte
        print(f"[DEBUG] Taille du contexte: {len(context)} caractères")
        
        # Préparation du prompt
        prompt = self.prompt_template.format(context=context, question=question)
        
        print("[DEBUG] Envoi du prompt au modèle LLM...")
        
        # Génération de la réponse
        response = self.llm.invoke(prompt)
        
        # Analyser la réponse pour voir combien de citations elle contient
        response_text = response.content
        print("\n[DEBUG] Réponse reçue du modèle")
        
        # Compter le nombre de citations (texte entre guillemets)
        import re
        citations = re.findall(r'"(.*?)"', response_text)
        print(f"[DEBUG] Nombre de citations détectées: {len(citations)}")
        
        # Vérifier si la section SOURCES est présente
        if "SOURCES" in response_text:
            print("[DEBUG] Section SOURCES détectée dans la réponse")
            # Extraire la section SOURCES
            sources_section = response_text.split("SOURCES")[1].strip()
            print(f"[DEBUG] Longueur de la section SOURCES: {len(sources_section)} caractères")
            print(f"[DEBUG] Début de la section SOURCES: '{sources_section[:200]}...'")
        else:
            print("[DEBUG] Aucune section SOURCES détectée dans la réponse!")
        
        return response_text

def format_response(response_text):
    """Formate la réponse pour séparer la réponse principale des sources."""
    print(f"[DEBUG] Formatage de la réponse: {len(response_text)} caractères")
    
    # Vérifier si la réponse contient les sections RÉPONSE et SOURCES
    has_reponse = "RÉPONSE" in response_text
    has_sources = "SOURCES" in response_text
    
    print(f"[DEBUG] Détection des sections: RÉPONSE={has_reponse}, SOURCES={has_sources}")
    
    if has_reponse and has_sources:
        # Extraire les sections RÉPONSE et SOURCES
        try:
            # Diviser la réponse en sections
            parts = response_text.split("SOURCES", 1)
            main_response = parts[0].strip()
            sources = "SOURCES" + parts[1].strip()
            
            # Nettoyer la section RÉPONSE
            if "RÉPONSE" in main_response:
                main_response = main_response.split("RÉPONSE", 1)[1].strip()
            
            # Compter le nombre de citations
            import re
            citations = re.findall(r'"(.*?)"', sources)
            print(f"[DEBUG] Nombre de citations dans la section SOURCES: {len(citations)}")
            
            # Formate la sortie avec une séparation claire
            formatted_response = f"{main_response}\n\n{'='*50}\n\n{sources}"
            return formatted_response
        except Exception as e:
            print(f"[DEBUG] Erreur lors du formatage de la réponse: {e}")
            # En cas d'erreur, essayer un formatage alternatif
            try:
                # Chercher les sections avec une expression régulière
                reponse_match = re.search(r'R[ÉE]PONSE\s*:?\s*(.+?)(?=\s*SOURCES|$)', response_text, re.DOTALL)
                sources_match = re.search(r'SOURCES\s*:?\s*(.+)', response_text, re.DOTALL)
                
                if reponse_match:
                    main_response = reponse_match.group(1).strip()
                else:
                    main_response = response_text.strip()
                
                if sources_match:
                    sources = "SOURCES\n" + sources_match.group(1).strip()
                else:
                    # Extraire les citations si possible
                    citations = re.findall(r'"(.+?)"\s*-\s*([^\(]+)\s*\(([^\)]+)\)', response_text)
                    if citations:
                        sources = "SOURCES\n" + "\n\n".join([f'"{c[0]}" - {c[1]} ({c[2]})' for c in citations])
                    else:
                        sources = "SOURCES\nAucune source disponible."
                
                formatted_response = f"{main_response}\n\n{'='*50}\n\n{sources}"
                return formatted_response
            except Exception as e2:
                print(f"[DEBUG] Erreur lors du formatage alternatif: {e2}")
                return response_text
    else:
        # Si le format n'est pas comme attendu, essayer d'extraire les parties importantes
        print("[DEBUG] Format non standard détecté, tentative d'extraction des parties importantes")
        
        # Extraire les citations si possible
        import re
        citations = re.findall(r'"(.+?)"', response_text)
        print(f"[DEBUG] Citations détectées dans la réponse: {len(citations)}")
        
        if citations:
            # Essayer de séparer la réponse des citations
            first_citation_pos = response_text.find('"' + citations[0] + '"')
            if first_citation_pos > 0:
                main_response = response_text[:first_citation_pos].strip()
                sources_text = response_text[first_citation_pos:].strip()
                formatted_response = f"{main_response}\n\n{'='*50}\n\nSOURCES\n{sources_text}"
                return formatted_response
        
        # Si aucune extraction n'est possible, retourner la réponse telle quelle
        return response_text

def main():
    # Initialisation du RAG
    print("Initialisation du système RAG pour Jean Piaget...")
    piaget_rag = PiagetRAG()
    
    print("\nBienvenue dans l'avatar de Jean Piaget!")
    print("Posez vos questions à Jean Piaget, et il vous répondra en se basant sur ses écrits.")
    print("Tapez 'exit' pour quitter.")
    
    while True:
        question = input("\nVotre question: ")
        
        if question.lower() in ['exit', 'quit', 'q']:
            print("Au revoir!")
            break
        
        if not question.strip():
            continue
        
        print("\nJean Piaget réfléchit...")
        raw_answer = piaget_rag.answer_question(question)
        formatted_answer = format_response(raw_answer)
        print(f"\n{formatted_answer}")

if __name__ == "__main__":
    main()
