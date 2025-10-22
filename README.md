# HomolCraft

Outil open-source pour la génération de points homologues (tie points) compatibles Micmac, basé sur des détecteurs modernes (SIFT, LoFTR, etc.), avec une interface flexible et des options avancées.

## Objectif

Fournir un outil Python permettant de générer des points homologues pour la photogrammétrie, avec export direct au format Micmac, supportant différents modes de sélection de paires et détecteurs.

## Fonctionnalités principales
- Modes : All, Line, MulScale, File, Pattern, Custom
    - **All** : Calcul pour toutes les paires possibles d'images.
    - **Line** : Calcul restreint aux paires d'images voisines selon l'ordre des fichiers (structure linéaire, paramètre delta). Pour chaque image, seules les paires avec les `delta` images suivantes (ou précédentes) dans la liste sont traitées. Permet d'accélérer le calcul sur des séquences ou des acquisitions linéaires (ex : drone, scanner, etc.).
    - **MulScale** : Approche multirésolution.
    - **File** : Calcul sur des paires listées dans un fichier.
    - **Pattern/Custom** : Modes avancés ou personnalisés.
    - **Pattern2** : Matching croisé entre deux patterns distincts (option `--pattern2`). Crée uniquement des paires entre les images des deux groupes, sans paires intra-groupe.
    - **Résolutions différentes** : Support de `--size-pattern2` pour détecter les points SIFT à des résolutions différentes pour chaque pattern (ex: détails RTI à 500px, images d'orientation à 2000px).
- Détecteurs : SIFT (OpenCV/Kornia), LoFTR (PyTorch/Kornia), extensible
- Multirésolution, gestion fine des paires, export texte Micmac
- Parallélisation, logs détaillés, dry-run, CLI moderne

## Installation

Prérequis : Python 3.8+

```bash
pip install -r requirements.txt
```

## Installation et premier test

```bash
./install.sh
source .venv/bin/activate
python -m homolcraft all 'tests/*.JPG' --size 1000 --detect sift
```

- Le dossier de sortie sera `Homol/` à la racine du projet.
- Vous pouvez remplacer `sift` par `loftr` si torch/kornia sont bien installés.

## Exemple d'utilisation

```bash
homolcraft all "data/IMG_*.tif" --size 2000 --detect sift
homolcraft line "data/IMG_*.tif" --size 1500 --delta 3
homolcraft mulscale "data/IMG_*.tif" --size-low 500 --size 2000 --nb-min-pt 5
homolcraft file "data/pairs.xml" --size 2000
homolcraft all "data/IMG_*.tif" --detect loftr --size 2000
homolcraft all "mur_*" --pattern2 "toit_*" --size 1500
homolcraft mulscale "ortho_*" --pattern2 "sud*ori*" --size 2000
# Matching avec résolutions différentes (RTI détails + images d'orientation)
homolcraft mulscale "nord_trav*_ori*.JPG" --pattern2 "rti_nord*.jpg" \
    --size 2000 --size-pattern2 500 --sift-nfeat 4000 --sift-nfeat-low 2000
```

## Structure du projet

```
homolcraft/
  __main__.py
  core/
    detectors.py
    matchers.py
    io.py
    multiscale.py
    pairs.py
    export.py
  cli.py
  utils.py
  requirements.txt
  README.md
  tests/
  doc/
```

## Licence

MIT 

## Roadmap

- [x] Prototype CLI minimal (SIFT, mode All)
- [x] Export Micmac (structure Homol/Pastis...)
- [ ] Intégration LoFTR
- [x] Mode Line (paires voisines, delta, circ)
- [ ] Modes MulScale/File
- [ ] Parallélisation
- [ ] Packaging binaire
- [ ] Optimisations, tests, documentation 