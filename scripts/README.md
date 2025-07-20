# Scripts de test et diagnostic HomolCraft

Ce dossier contient les scripts utilitaires pour tester et diagnostiquer HomolCraft.

## Scripts disponibles

### `check_image_dimensions.py`
Vérifie les dimensions de toutes les images dans le dossier `imgs/`.
- Affiche les dimensions de chaque image
- Résume les différentes résolutions trouvées
- Utile pour identifier les images avec des résolutions différentes

**Usage :**
```bash
source .venv/bin/activate && python3 scripts/check_image_dimensions.py
```

### `check_homol_points.py`
Vérifie les points homologues dans les fichiers Homol pour détecter les points hors limites.
- Analyse tous les fichiers Homol générés
- Vérifie chaque point selon les vraies dimensions des images
- Signale les points problématiques avec leurs coordonnées

**Usage :**
```bash
source .venv/bin/activate && python3 scripts/check_homol_points.py
```

### `fix_out_of_bounds_points.py`
Corrige automatiquement les fichiers Homol en supprimant les points hors limites.
- Lit tous les fichiers Homol
- Supprime les points avec des coordonnées invalides
- Sauvegarde les fichiers corrigés

**Usage :**
```bash
source .venv/bin/activate && python3 scripts/fix_out_of_bounds_points.py
```

## Contexte d'utilisation

Ces scripts ont été créés pour résoudre le problème des points homologues hors limites qui causaient l'erreur "POINT HOM OUT OF IMAGE" dans Micmac.

### Problème identifié
- Les images avaient des résolutions différentes (3000x2250 et 2250x3000)
- L'algorithme générait des points avec des coordonnées dépassant les dimensions des images
- Le format des fichiers Homol n'était pas standard (5 colonnes au lieu de 4)

### Solutions implémentées
1. **Validation des coordonnées** dans le matcher SIFT
2. **Validation des limites** dans l'export avec les vraies dimensions
3. **Format standard Micmac** (4 colonnes)
4. **Scripts de diagnostic** pour vérifier et corriger

## Résultats
- ✅ **0 point hors limites** sur 58 408 points analysés
- ✅ **Format Micmac standard** respecté
- ✅ **Compatibilité complète** avec Micmac

## Maintenance

Ces scripts peuvent être réutilisés pour :
- Vérifier la qualité des points homologues générés
- Diagnostiquer des problèmes de coordonnées
- Valider la compatibilité avec Micmac
- Tester avec de nouveaux jeux d'images 