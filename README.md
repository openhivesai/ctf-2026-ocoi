Ce dépôt contient un challenge CTF à exécuter localement.

## Prérequis
- Connexion Internet : l'API télécharge le modèle d'embeddings au premier lancement.
- Ollama installé et lancé localement (modèle configuré dans `docker-compose.yaml`).

## Lancement
docker-compose up --build

## Objectif
Interagir avec le système afin d’identifier une information interne précise.

Le flag n’est pas affiché directement par le système.

## Note
Le challenge n’est pas basé sur un secret : l’environnement local est contrôlé par le joueur. L’évaluation porte sur l’interaction et la conformité (CAS A / CAS B).
