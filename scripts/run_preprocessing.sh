#!/bin/bash
# Script de lancement pour le préprocessing d'images
# Utilise l'environnement virtuel dédié

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOMOLCRAFT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$HOMOLCRAFT_DIR/venv_preprocessing"

# Vérifier que l'environnement virtuel existe
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Environnement virtuel non trouvé: $VENV_DIR"
    echo "🔄 Création de l'environnement virtuel..."
    cd "$HOMOLCRAFT_DIR"
    python3 -m venv venv_preprocessing
    source venv_preprocessing/bin/activate
    pip install Pillow
    echo "✅ Environnement virtuel créé et configuré"
fi

# Activer l'environnement et lancer le script
cd "$HOMOLCRAFT_DIR"
source venv_preprocessing/bin/activate
python scripts/image_preprocessing.py "$@"
