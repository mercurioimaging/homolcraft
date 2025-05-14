#!/bin/bash

# Script d'installation pour HomolCraft
# Usage : ./install.sh

set -e

# Vérification de la version de Python
PYTHON_VERSION=$(python3 -c 'import sys; print("{}.{}".format(sys.version_info[0], sys.version_info[1]))')
REQUIRED_VERSION="3.8"

if [[ $(echo -e "$PYTHON_VERSION\n$REQUIRED_VERSION" | sort -V | head -n1) != "$REQUIRED_VERSION" ]]; then
  echo "Python >= 3.8 requis. Version détectée : $PYTHON_VERSION"
  exit 1
fi

# Création de l'environnement virtuel
if [ ! -d ".venv" ]; then
  echo "Création de l'environnement virtuel (.venv)..."
  python3 -m venv .venv
fi

# Activation de l'environnement virtuel
source .venv/bin/activate

echo "Installation des dépendances Python dans .venv..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Installation terminée."
echo "Activez l'environnement avec : source .venv/bin/activate"
echo "Lancez l'outil avec : python -m homolcraft all 'tests/*.JPG' --size 1000 --detect sift" 