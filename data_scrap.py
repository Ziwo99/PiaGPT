from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time
import json
import os
import re
import unicodedata

# Configuration
BASE_URL = "https://oeuvres.unige.ch"
START_URL = "https://oeuvres.unige.ch/piaget/chrono?hashtag=%23ed1"
OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "piaget_data.json")
DELAY_BETWEEN_REQUESTS = 0.5 # secondes, pour être poli avec le serveur mais plus rapide

# Créer le dossier de sortie s'il n'existe pas
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def get_page(url):
    """Charge une page avec Selenium et retourne un objet BeautifulSoup."""
    try:
        # Configuration de Chrome en mode headless (sans interface graphique)
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Pour éviter la détection
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--dns-prefetch-disable")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Créer le service avec ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        
        # Créer le driver
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Charger la page
        print(f"Chargement de la page : {url}")
        driver.get(url)
        
        # Attendre que la page soit chargée - temps d'attente réduit
        try:
            wait = WebDriverWait(driver, 5)  # Réduit de 15 à 5 secondes
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(0.5)  # Réduit de 2 à 0.5 secondes
        except Exception as e:
            print(f"Avertissement : Problème de chargement : {e}")
        
        # Affichage minimal pour le suivi
        print(f"Page chargée: {driver.title}")
        
        # Récupérer le contenu de la page
        page_content = driver.page_source
        
        # Fermer le driver
        driver.quit()
        
        # Créer et retourner l'objet BeautifulSoup
        return BeautifulSoup(page_content, 'html.parser')
    except Exception as e:
        print(f"Erreur lors du chargement de la page {url}: {e}")
        return None

def get_soup(url):
    """Télécharge une page et retourne un objet BeautifulSoup."""
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)  # Timeout réduit
        response.raise_for_status() # Lève une exception pour les codes d'erreur HTTP
        return BeautifulSoup(response.content, 'html.parser')
    except requests.RequestException as e:
        print(f"Erreur lors de la requête vers {url}: {e}")
        return None

def extract_title_and_date(title_text):
    """Extrait la date et le titre propre d'une chaîne de format "Piaget (1911) Titre de l'œuvre"."""
    # Supprimer les balises HTML
    title_text = re.sub(r'<.*?>', '', title_text)
    
    # Extraire la date entre parenthèses
    date_match = re.search(r'\((\d{4})\)', title_text)
    if date_match:
        date = date_match.group(1)
        # Supprimer le numéro (ex: "1.") au début
        title_text = re.sub(r'^\d+\.\s*', '', title_text)
        # Supprimer le nom de l'auteur et la date
        title_text = re.sub(r'^Piaget\s+\(\d{4}\)\s*', '', title_text)
        title = title_text.strip()
    else:
        date = None
        title = title_text.strip()
    
    # Nettoyer le titre
    title = re.sub(r'\s+', ' ', title).strip()
    
    return title, date

# Garder la fonction clean_title existante pour le nettoyage des accents

def clean_text(text, title=None):
    """Nettoye le texte en enlevant les balises HTML, les caractères spéciaux et en normalisant les accents.
    Si un titre est fourni, il sera également retiré du début du texte."""
    # Supprimer les balises HTML
    text = re.sub(r'<.*?>', '', text)
    
    # Normaliser les accents pour préserver les caractères français
    text = unicodedata.normalize('NFKC', text)
    
    # Supprimer les caractères spéciaux de contrôle
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    
    # Retirer le titre du texte s'il est présent au début
    if title:
        # Échapper les caractères spéciaux dans le titre pour l'utiliser dans une regex
        escaped_title = re.escape(title)
        # Retirer le titre avec ou sans la date et autres caractères
        text = re.sub(r'^' + escaped_title + r'\s*\(\d{4}\)[a-z]*\s*', '', text)
        text = re.sub(r'^' + escaped_title + r'\s*', '', text)
    
    # Supprimer les dates en début de texte (ex: "(1907)a") et les caractères spéciaux
    text = re.sub(r'^\(\d{4}\)[a-z]*\s*', '', text)
    
    # Nettoyer les caractères spéciaux isolés qui pourraient rester
    text = re.sub(r'\s+[a-z]\s*\.\s*', ' ', text)  # Supprime les lettres isolées suivies d'un point
    
    # Supprimer les références bibliographiques à la fin
    text = re.sub(r'\.[a-z]+\.\s*\d{4}\..*$', '', text)
    
    # Nettoyer les espaces et la ponctuation
    text = text.replace('\n', ' ').replace('\r', '')
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Nettoyer les espaces avant la ponctuation
    text = re.sub(r'\s+\.', '.', text)
    text = re.sub(r'\s+,', ',', text)
    text = re.sub(r'\s+;', ';', text)
    text = re.sub(r'\s+:', ':', text)
    
    # Nettoyer les espaces doubles après ponctuation
    text = re.sub(r'([.,:;!?])\s+', r'\1 ', text)
    
    # Préserver les accents français au lieu de les remplacer
    # Supprimé: text = text.replace('É', 'E').replace('È', 'E')...
    
    return text

def scrape_piaget_oeuvres():
    """Scrape les œuvres de Piaget depuis la page principale."""
    print(f"Accès à la page principale : {START_URL}")
    main_soup = get_page(START_URL)
    if not main_soup:
        print("Erreur : Impossible de charger la page principale")
        return []
    
    # Récupération directe des liens (plus efficace)
    links = main_soup.find_all('a', class_='bibl')
    print(f"Trouvé {len(links)} liens avec classe bibl")
    
    # Filtrer les liens valides
    valid_links = [link for link in links if link.get('href') and link.get('href').startswith('piaget')]
    print(f"\nTrouvé {len(valid_links)} liens vers des œuvres.")
    
    # Initialiser la liste des œuvres
    oeuvres = []
    
    # Traiter chaque œuvre
    for i, link in enumerate(valid_links):  # Traiter toutes les œuvres
        # Construire l'URL complète correctement
        work_url = f"{BASE_URL}/piaget/{link.get('href')}"
        print(f"Traitement: {i+1}/{len(valid_links)} - {link.get('href')}")
        work_soup = get_page(work_url)
        if not work_soup:
            print(f"Erreur : Impossible de charger la page {work_url}")
            continue
        
        # Récupérer l'article
        article = work_soup.find('article')
        if article:
            # Extraire le titre complet de la page et le traiter directement
            raw_title = work_soup.title.text if work_soup.title else link.text
            title, date = extract_title_and_date(raw_title)
            
            # Extraire le texte brut
            raw_text = article.get_text(strip=True)
            
            # Nettoyer le texte en retirant le titre et en appliquant les autres nettoyages
            cleaned_text = clean_text(raw_text, title)
            
            # Affichage minimal pour le suivi
            print(f"Œuvre traitée: {title} ({date}) - {len(cleaned_text)} caractères")
            
            # Ajouter l'œuvre à la liste avec le titre nettoyé et la date
            oeuvres.append({
                'title': title,
                'date': date,
                'text': cleaned_text,
                'url': work_url
            })
        else:
            print("Article non trouvé sur la page")
    
    # Sauvegarder les données
    os.makedirs('data', exist_ok=True)
    with open('data/piaget_data.json', 'w', encoding='utf-8') as f:
        json.dump(oeuvres, f, indent=2, ensure_ascii=False)
    
    print(f"\n{len(oeuvres)} œuvres scrapées et sauvegardées dans data/piaget_data.json")
    
    # Affichage minimal des résultats
    if oeuvres:
        print(f"Premier document: {oeuvres[0]['title']} ({oeuvres[0]['date']})")
    
    return oeuvres

if __name__ == '__main__':
    import time
    start_time = time.time()
    scraped_data = scrape_piaget_oeuvres()
    end_time = time.time()
    if scraped_data:
        print(f"\nScraping terminé en {end_time - start_time:.2f} secondes")
        print(f"Nombre total d'œuvres récupérées: {len(scraped_data)}")
        print(f"Exemple: {scraped_data[0]['title']} ({scraped_data[0]['date']})")
        print(f"Taille moyenne des textes: {sum(len(item['text']) for item in scraped_data) / len(scraped_data):.0f} caractères")