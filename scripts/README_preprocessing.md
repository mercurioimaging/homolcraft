# Préprocessing d'Images - Normalisation d'Orientation

Ce script extrait la fonctionnalité de rotation d'images de HomolCraft pour permettre un préprocessing autonome des images.

## Fonctionnalités

- **Correction EXIF** : Applique automatiquement la rotation EXIF
- **Normalisation paysage** : Pivote les images portrait en paysage
- **Préservation EXIF** : Maintient les métadonnées EXIF importantes
- **Sauvegarde automatique** : Crée des sauvegardes avant modification
- **Traitement par lot** : Support des patterns glob

## Installation

```bash
# Les dépendances sont déjà installées avec HomolCraft
pip install Pillow
```

## Utilisation

### Script principal

```bash
# Traiter toutes les images JPG d'un dossier
python image_preprocessing.py "images/*.jpg"

# Traiter des images spécifiques
python image_preprocessing.py image1.jpg image2.jpg

# Sans sauvegarde
python image_preprocessing.py "images/*.JPG" --no-backup

# Mode silencieux
python image_preprocessing.py "images/*.jpg" --quiet
```

### Utilisation en Python

```python
from image_preprocessing import fix_image_orientation, process_images

# Traiter une image
success, message = fix_image_orientation("mon_image.jpg", backup=True)

# Traiter plusieurs images
image_paths = ["img1.jpg", "img2.jpg", "img3.jpg"]
success_count, error_count = process_images(image_paths, backup=True, verbose=True)
```

## Options

- `--no-backup` : Désactive la création de sauvegardes
- `--quiet` : Mode silencieux (pas de messages de progression)

## Comportement

1. **Lecture** : Ouvre l'image avec PIL
2. **Correction EXIF** : Applique `ImageOps.exif_transpose()`
3. **Vérification orientation** : Si portrait (h > w), rotation de 90°
4. **Mise à jour EXIF** : Met l'orientation à "Normal" (1)
5. **Sauvegarde** : Écrit l'image avec les nouveaux pixels et EXIF

## Fichiers de sauvegarde

Les sauvegardes sont créées avec l'extension `.backup` :
- `image.jpg` → `image.jpg.backup`
- `photo.JPG` → `photo.JPG.backup`

## Exemples

```bash
# Traiter toutes les images d'un dossier
python image_preprocessing.py "/path/to/images/*.jpg"

# Traiter sans sauvegarde (attention !)
python image_preprocessing.py "*.JPG" --no-backup

# Mode silencieux pour scripts
python image_preprocessing.py "images/*.jpg" --quiet
```

## Intégration avec HomolCraft

Ce script est automatiquement appelé par HomolCraft lors de la détection d'images avec des orientations différentes. Il peut aussi être utilisé indépendamment pour le préprocessing.
