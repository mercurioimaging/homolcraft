import numpy as np
from homolcraft.core.matchers import match_sift

def test_match_sift():
    # Deux descripteurs identiques, un bruité
    desc1 = np.array([[1,2,3],[4,5,6]], dtype=np.float32)
    desc2 = np.array([[1,2,3],[4,5,6],[7,8,9]], dtype=np.float32)
    matches = match_sift(desc1, desc2, ratio=0.8)
    assert len(matches) >= 2 