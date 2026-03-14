# Changelog HomolCraft

## [3.2.4] - 2025-03-14
### Corrections
- **[mulscale]** Ajout de l'option `--size-low` (taille max en px pour la passe rapide) ; auparavant documentée dans le README mais absente de la CLI

## [3.2.3] - 2025-01-06
### Améliorations majeures
- **Normalisation automatique des images** : Vérification et normalisation automatique de l'orientation et de la résolution des images avant traitement
- **Intégration fix_orientation** : Appel automatique du script `fix_orientation.py` si les images ont des orientations ou résolutions différentes
- **Prévention des problèmes** : Évite les erreurs de points hors limites en normalisant les images dès le départ
- **Pipeline robuste** : Le pipeline vérifie maintenant automatiquement la cohérence des images avant traitement

## [3.2.2] - 2025-01-06
### Corrections critiques
- **Validation des coordonnées** : Correction majeure pour éviter les points homologues hors limites des images
- **Filtrage automatique** : Les points avec des coordonnées négatives ou dépassant les dimensions des images sont automatiquement supprimés
- **Validation dans le matcher** : Ajout d'une validation des coordonnées dans `core/matchers.py` pour éviter de générer des points problématiques dès le départ
- **Validation dans l'export** : Amélioration de la validation dans `core/export.py` avec une validation par défaut même si les dimensions ne sont pas connues
- **Compatibilité Micmac** : Cette correction résout l'erreur "POINT HOM OUT OF IMAGE" dans Micmac
- **Format standard** : Correction du format des fichiers Homol pour respecter le standard Micmac (4 colonnes au lieu de 5)
- **Gestion multi-résolutions** : Support correct des images avec différentes résolutions (3000x2250 et 2250x3000)

## [3.2.1] - 2025-07-10
### Corrections
- Le dossier Homol est maintenant créé dans le même répertoire que les images source pour tous les modes (all, line, file et mulscale)
- Cette correction uniformise le comportement d'écriture des fichiers entre tous les modes et suit le principe DRY

## [3.2.0] - 2025-07-10
### Améliorations
- **[mulscale]** Le mode mulscale effectue maintenant automatiquement les deux passes (basse puis haute résolution)
- **[mulscale]** La deuxième passe utilise désormais automatiquement les paires sélectionnées lors de la première passe
- **[mulscale]** Amélioration de la journalisation avec une section dédiée pour chaque passe dans le run_log
- **[mulscale]** Meilleure documentation de l'usage des paramètres sift_nfeat et sift_nfeat_low

## [3.1.0] - 2025-07-09
### Améliorations
- **[mulscale]** Ajout du paramètre `--sift-nfeat-low` (défaut: 500) pour contrôler le nombre de points SIFT détectés lors de la passe rapide
- **[mulscale]** Le fichier XML est maintenant placé dans le dossier des images analysées plutôt qu'à la racine du projet
- **[mulscale]** Affichage de la commande à exécuter pour la deuxième passe (mode `file`) dans les statistiques
- **[mulscale]** Amélioration de la journalisation des paramètres spécifiques au mode mulscale

## [3.0.1] - 2025-07-08
### Corrections
- Correction d'une erreur dans le mode mulscale qui provoquait un "TypeError: write_run_log() got an unexpected keyword argument 'xml_path'"
- Amélioration de la gestion des paramètres spécifiques au mode mulscale dans les logs (thresh_strategy, thresh_factor, thresh_fixed)
- Conversion correcte du paramètre xml_path en objet Path

## [3.0.0] - 2025-07-01
### Améliorations majeures
- Refactorisation complète du pipeline pour une meilleure maintenabilité et extensibilité
- Introduction du nouveau mode `mulscale` pour un traitement optimisé des images en deux passes
- Implémentation d'un système de journalisation amélioré avec statistiques détaillées
- Uniformisation des paramètres entre les différents modes (all, line, file, mulscale)
- Compatibilité complète avec le format Micmac pour tous les modes

## [2.1.2] - 2025-07-07
### Corrections
- Correction d'une erreur "AttributeError: 'Settings' object has no attribute 'detector'" en remplaçant "detector" par "detect"
- Correction d'une erreur "list indices must be integers or slices, not str" dans le matcher SIFT
- Amélioration des paramètres de `write_run_log` pour rendre delta et circ optionnels afin de supporter tous les modes
- Refactorisation de `_par_map` pour retourner un dictionnaire clair {élément: résultat} et éviter les erreurs d'indexation

## [2.1.1] - 2025-07-06
### Améliorations
- **[mulscale]** Ajout d'une gestion spéciale des paires inter-jeux de données dans le mode mulscale
- **[mulscale]** Un seuil plus souple est maintenant appliqué aux paires d'images provenant de différents jeux (préfixes différents)
- **[mulscale]** Ajout d'un export des statistiques détaillées au format JSON pour faciliter l'analyse
- **[mulscale]** Amélioration du graphique de distribution avec différenciation visuelle des paires intra et inter-jeux

## [2.1.0] - 2025-07-05
### Nouvelles fonctionnalités
- Ajout de la stratégie multi-échelle (mulscale) pour optimiser le calcul des points homologues :
  - Nouvelle commande `mulscale` : passe préliminaire à basse résolution avec SIFT réduit (500 points)
  - Génération d'un fichier XML au format MicMac (`SauvegardeNamedRel`) contenant uniquement les paires pertinentes
  - Stratégies intelligentes de sélection des paires :
    - `fixed` : Seuil fixe défini par `--match-threshold`
    - `mean` : Seuil relatif à la moyenne (moyenne × facteur)
    - `median` : Seuil relatif à la médiane (médiane × facteur)
    - `auto` : Seuil automatique basé sur la distribution (par défaut)
  - Génération de graphiques de distribution des matches pour aider à visualiser et ajuster les seuils
  - Analyse statistique des matches (min, max, moyenne, médiane, écart-type)
  - Enchaînement automatique avec la passe haute définition utilisant les paramètres standards
- Ajout du mode `file` pour traiter uniquement les paires définies dans un fichier XML :
  - Lecture des couples d'images depuis un fichier au format `SauvegardeNamedRel`
  - Optimisation du traitement en se concentrant uniquement sur les paires ayant un fort potentiel de correspondance
- Amélioration de l'interface utilisateur avec des messages adaptés au mode utilisé et une documentation détaillée

## [2.0.5] - 2025-07-02
### Optimisations
- Optimisation majeure de la phase d'export : préchargement des dimensions des images pour éviter les relectures multiples
- Amélioration de l'écriture des fichiers Homol avec utilisation d'un buffer pour réduire les opérations d'accès disque
- Réduction significative du temps d'export, spécialement pour les datasets avec beaucoup d'images

## [2.0.4] - 2025-07-01
### Corrections
- Correction de la barre de progression lors de l'export des points homologues en mode parallèle
- Amélioration du retour visuel pendant la phase d'écriture des fichiers Homol pour mieux refléter l'avancement réel du processus
- Correction de la gestion du dossier Homol_bkp pour éviter l'erreur "Destination path already exists" lors d'exécutions successives
- Amélioration de la robustesse de la sauvegarde des résultats précédents
- Correction de l'erreur "Stats.__init__() got an unexpected keyword argument 'rejection_rate'" en ajoutant les champs manquants dans la classe Stats

## [2.0.3] - 2025-06-30
### Améliorations
- Ajout du paramètre `--nb-pts-mini` (par défaut à 25) pour définir un seuil minimum de points homologues en dessous duquel les fichiers ne sont pas créés
- Réduction de la précision des coordonnées des points homologues de 6 à 3 décimales pour alléger les fichiers
- Amélioration de la gestion des faux positifs en filtrant les paires avec trop peu de points correspondants
- Comptabilisation améliorée des points rejetés dans les statistiques

## [2.0.2] - 2025-06-15
### Améliorations
- Ajout du paramètre `--progress` pour contrôler l'affichage des barres de progression
- Passage de la variable `ALGO_VERSION` au logger dans `write_run_log`
- Gestion plus robuste des erreurs avec try/except lors de la génération des points homologues
- Les erreurs sont maintenant loggées dans le fichier `homolcraft_run_log.txt`

## [1.1.0] - 2025-05-14
### Ajouts
- Versionning majeur.mineur.révision ajouté (ALGO_VERSION)
- Logs détaillés par étape (détection, matching, sélection spatiale, écriture) dans le run_log
- Écriture systématique des deux fichiers Homol pour chaque paire (img1->img2 et img2->img1)
- Optimisation du matching : chaque paire n'est matchée qu'une seule fois (img1 < img2)

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
- Factorisation de la génération des paires : fonctions utilitaires `all_pairs` (toutes paires) et `line_pairs` (voisins, delta, circ).
- Correction du mode `all` : il ne dépend plus de `delta`/`circ` et traite bien toutes les paires possibles.
- Préparation à la mutualisation du pipeline principal pour les futurs modes (ex : mulscale). 

## [1.3.1] - 2025-05-15
### Refactorisation & Améliorations
- Centralisation et DRY complet du logging (run_log et log.txt) : une seule fonction pour tous les modes.
- Ajout et correction des indicateurs dans les logs : nombre d'images, nombre de paires, nombre de paires exportées, RAM max (psutil ou resource), temps moyen par paire, paires/sec.
- Correction de l'affichage des stats (plus de '?').
- Décorateur commun pour les options CLI partagées (plus de duplication entre all/line).
- Refactorisation du calcul des stats (fonction compute_stats).
- Alternative à psutil pour la RAM max (module resource sur macOS/Linux). 

## [1.3.2] - 2025-05-14
### Correction de performance et robustesse
- Suppression de la double boucle de sélection spatiale par paire (phase post-matching) qui causait un ralentissement majeur.
- Optimisation de la structure de la sélection spatiale : un seul passage, plus de recalcul inutile.
- Progress bar explicite pour la phase de sélection spatiale et d'écriture Homol.
- Correction du compteur de paires exportées (stats) : le nombre affiché reflète désormais la réalité.
- Maintien de la compatibilité Micmac (symétrie d'écriture). 

## [1.4.0] - YYYY-MM-DD
### Added
- Integration of a major refactoring of the core pipeline (`homolcraft/refactor.py`).
- The `run_pipeline` function is now the central orchestrator for all processing modes (`all`, `line`).
- Clear 5-stage pipeline: pair generation, feature detection, matching, spatial selection, and MicMac Homol export.
- Each stage is a pure function, facilitating unit testing and maintenance.
- Improved progress display with `tqdm` for each significant step.
- Stricter `_in_bounds()` filter for homologous points, and reporting of rejected points in statistics.

### Changed
- CLI commands `all` and `line` in `__main__.py` now delegate their core logic to `run_pipeline`.
- Simplified logic in `__main__.py` by removing duplicated code for detection, matching, selection, and export, now handled by the refactored pipeline.
- Updated logging to reflect the new pipeline structure and include statistics on rejected points.
- `ALGO_VERSION` updated to `

## [3.3.0] - YYYY-MM-DD
### Améliorations
- **Matching robuste** : Intégration d'un filtre RANSAC (homographie) après le test de ratio de Lowe pour éliminer les faux positifs (`core/matchers.py`). Conserve un minimum de 4 inliers.
- **Popularité des points** : Prise en compte de l'occurrence des points d'intérêt à travers de multiples paires d'images. Le score de Lowe est pondéré par cette "popularité", favorisant les points fréquemment observés (`pipeline.py`).
- **Échantillonnage spatial** : Application d'un échantillonnage spatial dans une grille 4x4 lors de l'export des points homologues pour assurer une meilleure répartition et éviter la concentration des points (`core/export.py`).
- **Pipeline de filtrage affiné** : Le processus de filtrage final des correspondances inclut désormais le tri par score Lowe/popularité, un buffer, l'échantillonnage spatial, et des seuils min/max de points (`core/export.py`).
- **[mulscale]** Clarification : la première passe (coarse) du mode `mulscale` reste une évaluation brute du nombre de correspondances par paire, sans RANSAC, popularité ou échantillonnage spatial, avant l'application des stratégies de seuillage (`pipeline.py`).

### Corrections
- **[mulscale]** Correction d'un `TypeError` dans la fonction `_export` lors de la deuxième passe du mode `mulscale` (mode `file`). L'erreur se produisait lors de la détermination du répertoire des images sources.