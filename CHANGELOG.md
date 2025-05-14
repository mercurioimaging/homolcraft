# Changelog HomolCraft

## [1.1.0] - 2025-05-14
### Ajouts
- Versionning majeur.mineur.révision ajouté (ALGO_VERSION)
- Logs détaillés par étape (détection, matching, sélection spatiale, écriture) dans le run_log
- Écriture systématique des deux fichiers Homol pour chaque paire (img1->img2 et img2->img1)
- Optimisation du matching : chaque paire n'est matchée qu'une seule fois (img1 < img2)

### Modifications
- Sélection spatiale améliorée pour garantir une bonne répartition des tie points
- Complétion automatique avec des doubles si pas assez de triples

### Corrections
- Correction du bug de shadowing de variable `images`
- Correction de l'accès aux dimensions originales pour le tri spatial

---

## [1.0.0] - 2025-05-10
- Première version stable du pipeline SIFT/LoFTR avec visualisation matplotlib 

## [1.2.0] - 2025-05-15
### Ajouts
- Mode "Line" : calcul restreint aux paires d'images voisines selon l'ordre des fichiers, avec paramètre `delta` et option `--circ` pour l'acquisition circulaire.
- Option CLI : `homolcraft line <pattern> --delta N [--circ]`.
- Documentation et exemples d'utilisation mis à jour (README).
- Export et logs détaillés identiques au mode all, compatible Micmac. 

## [1.2.1] - 2025-05-15
### Correctif
- Correction critique : en mode "line", seuls les fichiers Homol correspondant aux vrais voisins (selon delta et circ) sont écrits dans chaque dossier PastisXXX. Plus de propagation de fichiers non voisins (ex : IMG_0065.JPG.txt partout).
- Compatibilité stricte Micmac assurée pour la structure Homol. 

## [1.3.0] - 2025-05-15
### Refactorisation
- Factorisation de la génération des paires : fonctions utilitaires `all_pairs` (toutes paires) et `line_pairs` (voisins, delta, circ).
- Correction du mode `all` : il ne dépend plus de `delta`/`circ` et traite bien toutes les paires possibles.
- Préparation à la mutualisation du pipeline principal pour les futurs modes (ex : mulscale). 