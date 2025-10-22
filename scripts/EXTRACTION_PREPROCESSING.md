# Extraction du Préprocessing d'Images - HomolCraft

## Résumé

La fonctionnalité de rotation d'images de HomolCraft a été extraite pour permettre un préprocessing autonome des images, indépendamment du processus de matching.

## Fichiers créés

### Scripts principaux
- **`image_preprocessing.py`** : Script principal de préprocessing
- **`run_preprocessing.sh`** : Script de lancement avec environnement virtuel
- **`demo_preprocessing.py`** : Script de démonstration

### Documentation
- **`README_preprocessing.md`** : Documentation complète
- **`EXTRACTION_PREPROCESSING.md`** : Ce fichier de résumé

## Fonctionnalités extraites

### De `fix_orientation.py` (original)
- Correction automatique de l'orientation EXIF
- Rotation des images portrait en paysage
- Préservation des métadonnées EXIF
- Gestion des sauvegardes

### Améliorations ajoutées
- Interface en ligne de commande complète
- Support des patterns glob
- Options de sauvegarde et mode silencieux
- Gestion d'erreurs robuste
- Documentation intégrée

## Utilisation

### Méthode simple (recommandée)
```bash
# Depuis le dossier HomolCraft
./scripts/run_preprocessing.sh "images/*.jpg"
./scripts/run_preprocessing.sh "images/*.JPG" --no-backup
./scripts/run_preprocessing.sh image1.jpg image2.jpg --quiet
```

### Méthode directe
```bash
# Avec environnement virtuel
cd HomolCraft
source venv_preprocessing/bin/activate
python scripts/image_preprocessing.py "images/*.jpg"
```

### En Python
```python
from scripts.image_preprocessing import fix_image_orientation, process_images

# Traiter une image
success, message = fix_image_orientation("mon_image.jpg", backup=True)

# Traiter plusieurs images
image_paths = ["img1.jpg", "img2.jpg", "img3.jpg"]
success_count, error_count = process_images(image_paths, backup=True, verbose=True)
```

## Intégration avec HomolCraft

Le script original `fix_orientation.py` reste intact et continue d'être utilisé par HomolCraft. Le nouveau script `image_preprocessing.py` est une version autonome et améliorée.

## Environnement

- **Environnement virtuel** : `venv_preprocessing/` (créé automatiquement)
- **Dépendance** : Pillow (installé automatiquement)
- **Python** : Compatible avec Python 3.7+

## Avantages de l'extraction

1. **Autonomie** : Utilisable sans HomolCraft
2. **Flexibilité** : Options de ligne de commande complètes
3. **Robustesse** : Gestion d'erreurs améliorée
4. **Documentation** : Interface utilisateur claire
5. **Réutilisabilité** : Importable en Python
