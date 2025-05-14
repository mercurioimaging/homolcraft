import numpy as np
from homolcraft.core.detectors import SIFTDetector

def test_sift_detector():
    img = np.zeros((100,100,3), dtype=np.uint8)
    detector = SIFTDetector()
    kps, desc = detector.detect_and_compute(img)
    assert isinstance(kps, list)
    assert desc is not None or len(kps) == 0 