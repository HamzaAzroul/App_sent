
Cette application permet d'analyser les sentiments exprimés dans des tweets. Elle offre des fonctionnalités pour explorer les données, prétraiter le texte des tweets, effectuer une analyse des sentiments et visualiser les résultats.

## ✨ Fonctionnalités Principales

*   **Exploration des Données :**
    *   Chargement des tweets à partir d'un fichier CSV (`chatgpt1.csv` par défaut).
    *   Filtrage dynamique des tweets basé sur des mots-clés sélectionnés par l'utilisateur.
    *   Affichage des tweets filtrés sous forme de tableau.
*   **Analyse des Sentiments :**
    *   **Pré-traitement du Texte :** Nettoyage complet des tweets incluant :
        *   Suppression des doublons.
        *   Conversion en minuscules.
        *   Suppression des URLs, des mentions (@utilisateur), des hashtags (#motclé) et des tickers ($ticker).
        *   Suppression de la ponctuation, des chiffres et des caractères spéciaux.
        *   Tokénisation et suppression des mots courts.
    *   **Analyse de Polarité :** Utilisation de l'analyseur de sentiments VADER (Valence Aware Dictionary and sEntiment Reasoner) de NLTK pour classifier les tweets en `Positif`, `Négatif` ou `Neutre`.
    *   **Visualisation des Résultats :**
        *   Affichage des pourcentages de tweets positifs, négatifs et neutres.
        *   Histogramme et diagramme circulaire (camembert) de la distribution des sentiments.
        *   Graphique de dispersion illustrant la relation entre le nombre de "Likes" et le score de polarité (si disponible).
        *   Graphique linéaire montrant la tendance des sentiments au fil du temps (si les données de date/heure sont disponibles et correctement formatées).
    *   **Téléchargement :** Option pour télécharger les tweets nettoyés avec leurs sentiments analysés au format CSV.

## 🛠️ Technologies Utilisées

*   **Python**
*   **Streamlit:** Framework pour la création d'applications web de data science.
*   **Pandas:** Pour la manipulation et l'analyse des données.
*   **NLTK (Natural Language Toolkit):** Pour le traitement du langage naturel, spécifiquement l'analyseur de sentiments VADER.
*   **Plotly Express:** Pour la création de graphiques interactifs.
*   **Hydralit Components:** Pour la barre de navigation (si utilisée dans la version actuelle).


## 🚀 Démarrage Rapide

### Prérequis

*   Python 3.7+
*   pip (gestionnaire de paquets Python)

### Installation

1.  **Clonez le dépôt (ou téléchargez les fichiers) :**
    ```bash
    git clone https://github.com/elmehdi-elfedini/Sentiment-Analysis-of-Tweets.git
    cd Sentiment-Analysis-of-Tweets
    ```
    Ou placez simplement les fichiers `app.py`, `processing.py`, et `chatgpt1.csv` dans un même dossier.

2.  **Créez un environnement virtuel (recommandé) :**
    ```bash
    python -m venv venv
    ```
    Activation :
    *   Sur Windows : `.\venv\Scripts\activate`
    *   Sur macOS/Linux : `source venv/bin/activate`

3.  **Installez les dépendances :**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Préparez vos données :**
    *   Assurez-vous d'avoir un fichier `chatgpt1.csv` dans le même dossier que `app.py`. 

### Exécution de l'Application

1.  Ouvrez votre terminal ou invite de commandes dans le dossier du projet.
2.  Lancez l'application Streamlit :
    ```bash
    streamlit run app.py
    ```
3.  L'application devrait s'ouvrir automatiquement dans votre navigateur web par défaut.
