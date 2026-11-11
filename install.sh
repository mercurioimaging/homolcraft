#!/bin/bash

# Script d'installation pour HomolCraft
# Usage : ./install.sh

set -e

PYTHON_BIN=""
for candidate in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    ver=$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "")
    major=${ver%.*}
    minor=${ver#*.}
    if [ "$major" = "3" ] && [ -n "$minor" ] && [ "$minor" -ge 10 ]; then
      PYTHON_BIN="$candidate"
      break
    fi
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "Aucun Python >= 3.10 trouvé. Installe-en un (ex: brew install python@3.11)."
  exit 1
fi

if [ -d ".venv" ]; then
  current=$(.venv/bin/python -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "")
  cur_major=${current%.*}
  cur_minor=${current#*.}
  if [ "$cur_major" != "3" ] || [ -z "$cur_minor" ] || [ "$cur_minor" -lt 10 ]; then
    echo "Venv existant en Python $current : suppression et recréation..."
    rm -rf .venv
  fi
fi

if [ ! -d ".venv" ]; then
  echo "Création de l'environnement virtuel (.venv) avec $PYTHON_BIN ($("$PYTHON_BIN" --version))..."
  "$PYTHON_BIN" -m venv .venv
fi

# Activation de l'environnement virtuel
source .venv/bin/activate

echo "Installation des dépendances Python dans .venv..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Installation terminée."
echo "Activez l'environnement avec : source .venv/bin/activate"
echo "Lancez l'outil avec : python -m homolcraft all 'tests/*.JPG' --size 1000 --detect sift" 