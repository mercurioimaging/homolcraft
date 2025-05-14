import cv2
import torch
import kornia

class SIFTDetector:
    def __init__(self, nfeatures=0):
        self.detector = cv2.SIFT_create(nfeatures=nfeatures)

    def detect_and_compute(self, image):
        keypoints, descriptors = self.detector.detectAndCompute(image, None)
        return keypoints, descriptors

class LoFTRDetector:
    def __init__(self, device='cpu'):
        from kornia.feature import LoFTR
        self.matcher = LoFTR(pretrained='outdoor').to(device)
        self.device = device

    def detect_and_compute(self, image0, image1):
        # image0, image1: torch.Tensor [1,1,H,W] ou [1,3,H,W]
        input_dict = {"image0": image0.to(self.device), "image1": image1.to(self.device)}
        with torch.no_grad():
            correspondences = self.matcher(input_dict)
        return correspondences 