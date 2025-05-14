# PRD – HomolCraft

## 1. Objectif

Développer un outil open-source, en Python, permettant de générer des points homologues (tie points) pour la suite logicielle Micmac, en s’appuyant sur des détecteurs modernes (SIFT, LoFTR, etc.), avec une interface flexible et des options avancées (multirésolution, gestion des paires, patterns de fichiers, etc.). L’outil doit pouvoir être packagé en binaire autonome (type PyInstaller) pour une utilisation sans environnement Python dédié.

---

## 2. Fonctionnalités principales

### 2.1 Modes de fonctionnement

- **All** : Calcul de points homologues pour toutes les paires possibles d’un jeu d’images (pattern de nom de fichier).
- **Line** : Calcul restreint aux paires d’images voisines (structure linéaire, paramètre delta).
- **MulScale** : Approche multirésolution, calcul rapide à basse résolution puis raffinement sur les paires prometteuses.
- **File** : Calcul sur des paires explicitement listées dans un fichier (XML ou texte).
- **Pattern** : Sélection d’images par expression régulière ou pattern de nom.
- **Custom** : Possibilité d’intégrer d’autres stratégies de sélection de paires (ex : grille, clusters, etc.).

### 2.2 Détecteurs et descripteurs

- **SIFT** (OpenCV, Kornia, etc.)
- **LoFTR** (PyTorch, Kornia)
- **Possibilité d’ajouter d’autres méthodes à terme (SuperGlue, LightGlue, etc.)**

### 2.3 Options avancées

- **Multirésolution** : Paramètres de taille d’image pour chaque passe.
- **Gestion fine des paires** : Par pattern, par fichier, par voisinage, etc.
- **Export** : Format texte (compatible Micmac) ou binaire.
- **Parallélisation** : Utilisation de plusieurs cœurs CPU.
- **Seuils et ratios** : Ratio Lowe, nombre minimal de points, etc.
- **Logs détaillés** et gestion des erreurs.
- **Dry-run** : Simulation sans écriture.
- **Compatibilité Micmac** : Structure de sortie dans le dossier `Homol/` ou configurable.

### 2.4 Interface utilisateur

- **CLI** (Command Line Interface) inspirée de Tapioca, mais modernisée (aide, complétion, validation des arguments).
- **Documentation intégrée** (`--help`, `--mode-help`, etc.).
- **Possibilité d’intégrer une interface graphique à terme.**

---

## 3. Exemples d’utilisation

Par défaut le détecteur sera LoFTR. Les paramètrs 'size, detect, nb-min-pt' etc sont tous facultatifs. 

```bash
homolcraft all "data/IMG_*.tif" --size 2000 --detect sift
homolcraft line "data/IMG_*.tif" --size 1500 --delta 3
homolcraft mulscale "data/IMG_*.tif" --size-low 500 --size 2000 --nb-min-pt 5
homolcraft file "data/pairs.xml" --size 2000
homolcraft all "data/IMG_*.tif" --detect loftr --size 2000
```

Voilà à quoi ressemble le résultat de Tapioca :
```bash
mm3d Tapioca All ".*JPG" 1000 @SFS ExpTxt=1
tree .
.
├── 2017_ortho_couloir_N_2_067.JPG
├── 2017_ortho_couloir_N_2_068.JPG
├── 2017_ortho_couloir_N_2_069.JPG
├── 2025_04_ELT_0349.JPG
├── 2025_04_ELT_0350.JPG
├── 2025_04_ELT_0353.JPG
├── Homol
│   ├── Pastis2017_ortho_couloir_N_2_067.JPG
│   │   ├── 2017_ortho_couloir_N_2_068.JPG.txt
│   │   ├── 2017_ortho_couloir_N_2_069.JPG.txt
│   │   ├── 2025_04_ELT_0349.JPG.txt
│   │   ├── 2025_04_ELT_0350.JPG.txt
│   │   └── 2025_04_ELT_0353.JPG.txt
│   ├── Pastis2017_ortho_couloir_N_2_068.JPG
│   │   ├── 2017_ortho_couloir_N_2_067.JPG.txt
│   │   ├── 2017_ortho_couloir_N_2_069.JPG.txt
│   │   ├── 2025_04_ELT_0349.JPG.txt
│   │   ├── 2025_04_ELT_0350.JPG.txt
│   │   └── 2025_04_ELT_0353.JPG.txt
│   ├── Pastis2017_ortho_couloir_N_2_069.JPG
│   │   ├── 2017_ortho_couloir_N_2_067.JPG.txt
│   │   ├── 2017_ortho_couloir_N_2_068.JPG.txt
│   │   ├── 2025_04_ELT_0349.JPG.txt
│   │   ├── 2025_04_ELT_0350.JPG.txt
│   │   └── 2025_04_ELT_0353.JPG.txt
│   ├── Pastis2025_04_ELT_0349.JPG
│   │   ├── 2017_ortho_couloir_N_2_067.JPG.txt
│   │   ├── 2017_ortho_couloir_N_2_068.JPG.txt
│   │   ├── 2017_ortho_couloir_N_2_069.JPG.txt
│   │   ├── 2025_04_ELT_0350.JPG.txt
│   │   └── 2025_04_ELT_0353.JPG.txt
│   ├── Pastis2025_04_ELT_0350.JPG
│   │   ├── 2017_ortho_couloir_N_2_067.JPG.txt
│   │   ├── 2017_ortho_couloir_N_2_068.JPG.txt
│   │   ├── 2017_ortho_couloir_N_2_069.JPG.txt
│   │   ├── 2025_04_ELT_0349.JPG.txt
│   │   └── 2025_04_ELT_0353.JPG.txt
│   └── Pastis2025_04_ELT_0353.JPG
│       ├── 2017_ortho_couloir_N_2_067.JPG.txt
│       ├── 2017_ortho_couloir_N_2_068.JPG.txt
│       ├── 2017_ortho_couloir_N_2_069.JPG.txt
│       ├── 2025_04_ELT_0349.JPG.txt
│       └── 2025_04_ELT_0350.JPG.txt
```


Voilà un extrait du fichier Homol/img1.JPG/img2.JPG.txt
```
731.959200 4509.478400 29.669192 4565.540000 1.000000
733.219200 4091.416000 35.286384 4146.788800 1.000000
709.996000 409.320240 40.323080 476.026880 1.000000
712.667200 690.547200 41.037136 754.079200 1.000000
711.911200 113.099840 44.928072 180.867120 1.000000
755.137600 5124.767200 44.956072 5184.922400 1.000000
746.905600 4494.784000 45.052840 4550.851200 1.000000
722.769600 1326.472000 46.722984 1386.078400 1.000000
736.668800 3123.657600 46.903920 3177.378400 1.000000
720.059200 1071.280000 47.089000 1132.213600 1.000000
723.055200 1169.526400 50.343776 1230.342400 1.000000
754.482400 4667.135200 51.111592 4724.132000 1.000000
753.950400 4515.291200 51.573424 4572.030400 1.000000
757.870400 4848.698400 52.061632 4907.089600 1.000000
745.259200 3408.680800 53.412968 3462.720800 1.000000
739.032000 2048.754400 53.700584 2104.642400 1.000000
740.824000 2550.900800 53.862704 2605.232000 1.000000
757.142400 4630.136000 53.899832 4686.511200 1.000000
740.605600 2155.316800 55.057744 2210.992000 1.000000
741.266400 1711.158400 56.194320 1768.267200 1.000000
753.502400 3874.847200 57.137920 3929.525600 1.000000
728.968800 457.485280 57.685600 522.799760 1.000000
766.936800 5053.792800 57.746640 5113.477600 1.000000
730.564800 876.898400 57.955520 939.612800 1.000000
757.517600 4135.947200 58.976400 4191.017600 1.000000
765.346400 4956.750400 59.503920 5015.701600 1.000000
746.306400 1787.693600 60.727520 1844.880800 1.000000
749.896000 2946.300000 61.398400 2999.841600 1.000000
```
Il contient les coordonnées X Y de chaque tie point :
x_img1 y_img1 x_img2 y_img2 1


---

## 4. Architecture technique

### 4.1 Dépendances Python

- **numpy**
- **opencv-python**
- **kornia** (pour LoFTR, SIFT, etc.)
- **torch** (pour LoFTR)
- **tqdm** (progress bar)
- **lxml** (lecture/écriture XML)
- **click** ou **argparse** (CLI)
- **pyinstaller** (pour le binaire autonome)
- **logging**

### 4.2 Structure du projet

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

### 4.3 Optimisations futures

- **Support GPU/CPU automatique**
- **Gestion mémoire optimisée pour gros jeux d’images**
- **Support d’autres détecteurs/descripteurs**
- **Interface graphique (PyQt, etc.)**
- **Intégration cloud/cluster**
- **Benchmarks et profils de performance**
- **Tests unitaires et d’intégration**
- **CI/CD pour releases binaires multiplateformes**

---

## 5. Livrables

- **Code source Python**
- **Binaire autonome (PyInstaller, etc.)**
- **Documentation utilisateur et développeur**
- **Jeux de tests et exemples**
- **Fichiers requirements.txt et setup.py**

---

## 6. Contraintes

- **Compatibilité Linux/Mac/Windows**
- **Sorties strictement compatibles avec Micmac**
- **Facilité d’installation et d’utilisation**
- **Extensibilité (ajout facile de nouveaux détecteurs ou modes)**

---

## 7. Nom du projet

**HomolCraft**

---

## 8. Inspirations et références

- **Tapioca (Micmac)**
- **Pastis (Micmac)**
- **Kornia, OpenCV, PyTorch**
- **LoFTR, SIFT, SuperGlue, LightGlue**

---

## 9. Roadmap (exemple)

## Avancement (mai 2025)

- [x] Prototype CLI minimal (SIFT, mode All)
- [x] Export Micmac (structure Homol/Pastis...)
- [ ] Intégration LoFTR
- [ ] Modes Line/MulScale/File
- [ ] Parallélisation
- [ ] Packaging binaire
- [ ] Optimisations, tests, documentation
