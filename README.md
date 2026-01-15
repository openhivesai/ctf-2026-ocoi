# IA-RAG-CTF

Ce dépôt contient un challenge CTF à exécuter localement.

## Prérequis
- Connexion Internet (téléchargement du modèle d’embeddings au premier lancement).
- Ollama installé et lancé localement (modèle configuré dans `docker-compose.yaml`).

## Lancement
docker-compose up --build

## Objectif
Interagir avec un assistant afin d’identifier une information interne précise.

L’assistant peut refuser de répondre selon le contexte fourni :
ce comportement fait partie intégrante du challenge.

## Architecture
Le challenge repose sur un **LLM exécuté localement via Ollama**,
augmenté par un **moteur RAG conteneurisé** (Docker).

Le joueur n’a pas accès direct aux documents.
Toute la résolution passe par l’interaction avec l’API.

## Flag
Le flag **n’est pas affiché directement par le système**.

Une fois l’information correcte identifiée,
le joueur doit en déduire le flag et le soumettre à la plateforme CTF.

Format du flag :
CCOI26{…}

## Note
Ce challenge ne repose pas sur un secret caché,
mais sur la capacité à raisonner face à un système RAG réaliste.
