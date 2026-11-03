from __future__ import annotations
"""
homolcraft.core.dust3r
----------------------
Matcher DUSt3R (poids vismatch/duster, ViT-L 512) : nuage 3D par image, puis
correspondances réciproques dans l'espace 3D (find_reciprocal_matches).

Différences avec le wrapper vismatch d'origine :
  - seuil de confiance réglable (vismatch fixe min_conf_thr=3, au-dessus de la
    confiance maximale de DUSt3R sur des vues très différentes -> 0 point) ;
  - pas de RANSAC par homographie (faux pour une scène 3D) : le filtrage est fait
    par homolcraft (matrice fondamentale MAGSAC) dans core/matchers.py.
"""

import numpy as np

from vismatch.im_models.duster import (
    Dust3rMatcher, inference, make_pairs, global_aligner, GlobalAlignerMode,
    find_reciprocal_matches, xy_grid,
)


class HomolDust3rMatcher(Dust3rMatcher):
    def __init__(self, device="cpu", conf_thr: float = 1.5, **kwargs):
        super().__init__(device, **kwargs)
        self.conf_thr = conf_thr
        self.skip_ransac = True

    def _forward(self, img0, img1):
        img0, shape0 = self.preprocess(img0)
        img1, shape1 = self.preprocess(img1)
        images = [{"img": img0, "idx": 0, "instance": 0}, {"img": img1, "idx": 1, "instance": 1}]
        pairs = make_pairs(images, scene_graph="complete", prefilter=None, symmetrize=True)
        output = inference(pairs, self.model, self.device, batch_size=1, verbose=False)
        scene = global_aligner(output, device=self.device, mode=GlobalAlignerMode.PairViewer, verbose=False)

        pts3d = scene.get_pts3d()
        pts2d_list, pts3d_list = [], []
        for i in range(2):
            m = (scene.im_conf[i] > self.conf_thr).cpu().numpy()
            pts2d_list.append(xy_grid(*scene.imgs[i].shape[:2][::-1])[m])
            pts3d_list.append(pts3d[i].detach().cpu().numpy()[m])
        if len(pts3d_list[0]) == 0 or len(pts3d_list[1]) == 0:
            return np.empty((0, 2)), np.empty((0, 2)), None, None, None, None

        recip, nn2_in_1, _ = find_reciprocal_matches(*pts3d_list)
        mk1 = pts2d_list[1][recip]
        mk0 = pts2d_list[0][nn2_in_1][recip]
        mk0 = self.rescale_coords(mk0, *shape0, *img0.shape[-2:])
        mk1 = self.rescale_coords(mk1, *shape1, *img1.shape[-2:])
        return mk0, mk1, None, None, None, None
