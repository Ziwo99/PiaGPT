import json
import os
import pickle
import faiss
import numpy as np
import time
from typing import List, Dict, Any
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

def load_data(json_path: str) -> List[Dict[str, Any]]:
    """Charge les données JSON."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def prepare_documents(raw_data: List[Dict[str, Any]], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    """Prépare les documents en les divisant en chunks."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    documents = []
    print(f"Traitement de {len(raw_data)} documents...")
    for item in tqdm(raw_data, desc="Création des chunks"):
        chunks = text_splitter.split_text(item['text'])
        for chunk in chunks:
            doc = Document(
                page_content=chunk,
                metadata={
                    'title': item['title'],
                    'date': item['date'],
                    'url': item['url']
                }
            )
            documents.append(doc)
    
    print(f"Nombre total de chunks créés: {len(documents)}")
    return documents

def create_embeddings_and_index(documents: List[Document], output_dir: str):
    """Crée les embeddings, l'index FAISS et sauvegarde les données."""
    # Création du répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    # Extraction des textes
    print("Extraction des textes pour les embeddings...")
    texts = [doc.page_content for doc in documents]
    
    # Création des embeddings
    print(f"Création des embeddings pour {len(texts)} chunks...")
    start_time = time.time()
    embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    # Utilisation de tqdm pour montrer la progression
    batch_size = 32  # Ajustez selon votre mémoire disponible
    embeddings = []
    
    for i in tqdm(range(0, len(texts), batch_size), desc="Génération des embeddings"):
        batch = texts[i:i+batch_size]
        batch_embeddings = embedding_model.encode(batch)
        embeddings.extend(batch_embeddings)
    
    embeddings = np.array(embeddings)
    elapsed_time = time.time() - start_time
    print(f"Embeddings créés en {elapsed_time:.2f} secondes")
    
    # Normalisation des embeddings
    print("Normalisation des embeddings...")
    faiss.normalize_L2(embeddings)
    
    # Création de l'index
    print("Création de l'index FAISS...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    
    print(f"Index créé avec {len(embeddings)} vecteurs de dimension {dimension}")
    
    # Sauvegarde de l'index FAISS
    print("Sauvegarde de l'index FAISS...")
    faiss.write_index(index, os.path.join(output_dir, "piaget_index.faiss"))
    print(f"Index FAISS sauvegardé dans {output_dir}/piaget_index.faiss")
    
    # Sauvegarde des documents (métadonnées)
    print("Sauvegarde des métadonnées des documents...")
    with open(os.path.join(output_dir, "piaget_documents.pkl"), 'wb') as f:
        pickle.dump(documents, f)
    print(f"Documents sauvegardés dans {output_dir}/piaget_documents.pkl")

def main():
    # Chemin vers le fichier JSON
    json_path = "data/piaget_data.json"
    output_dir = "data/processed"
    
    start_time = time.time()
    print("=== DÉBUT DU PRÉTRAITEMENT ===\n")
    
    print("Chargement des données...")
    raw_data = load_data(json_path)
    print(f"{len(raw_data)} documents chargés depuis {json_path}\n")
    
    print("Préparation des documents...")
    documents = prepare_documents(raw_data)
    print(f"Préparation des documents terminée.\n")
    
    print("Création des embeddings et de l'index...")
    create_embeddings_and_index(documents, output_dir)
    
    total_time = time.time() - start_time
    print(f"\n=== PRÉTRAITEMENT TERMINÉ EN {total_time:.2f} SECONDES ===\n")
    print(f"Vous pouvez maintenant exécuter piaget_rag_engine.py pour interagir avec l'avatar de Jean Piaget.")
    print(f"Les données prétraitées sont stockées dans: {output_dir}")
    print(f"- Index FAISS: {len(documents)} vecteurs")
    print(f"- Documents: {len(documents)} chunks")

if __name__ == "__main__":
    main()
