
import numpy as np
from scipy.ndimage import map_coordinates, rotate, shift, gaussian_filter
from scipy.optimize import minimize
from scipy.fft import fft2, ifft2, fftshift
import cv2

from phase_correlation import PhaseCorrelationRegistrator
from quality_metrics import RegistrationQualityEvaluator


class CrossModalRegistrator:
    def __init__(self):
        self.phase_registrator = PhaseCorrelationRegistrator()
        self.evaluator = RegistrationQualityEvaluator()
    
    def preprocess_for_cross_modal(self, img):
        if len(img.shape) == 3:
            img = np.mean(img, axis=2)
        
        img = img.astype(np.float32)
        
        img_eq = self._histogram_equalization(img)
        
        edge_img = self._edge_enhancement(img_eq)
        
        return img_eq, edge_img
    
    def _histogram_equalization(self, img):
        img_flat = img.flatten()
        hist, bins = np.histogram(img_flat, bins=256, range=(img.min(), img.max()))
        cdf = hist.cumsum()
        cdf_normalized = cdf / cdf[-1]
        
        img_equalized = np.interp(img_flat, bins[:-1], cdf_normalized * 255)
        return img_equalized.reshape(img.shape).astype(np.float32)
    
    def _edge_enhancement(self, img):
        grad_y, grad_x = np.gradient(img)
        magnitude = np.sqrt(grad_x**2 + grad_y**2)
        magnitude = (magnitude - magnitude.min()) / (magnitude.max() - magnitude.min() + 1e-12)
        return magnitude.astype(np.float32)
    
    def detect_and_match_features(self, img1, img2):
        img1_uint8 = np.clip(img1, 0, 255).astype(np.uint8)
        img2_uint8 = np.clip(img2, 0, 255).astype(np.uint8)
        
        orb = cv2.ORB_create(nfeatures=500, scaleFactor=1.2, nlevels=8)
        
        kp1, des1 = orb.detectAndCompute(img1_uint8, None)
        kp2, des2 = orb.detectAndCompute(img2_uint8, None)
        
        if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
            return None, None, None
        
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        
        matches = sorted(matches, key=lambda x: x.distance)
        good_matches = matches[:min(100, len(matches))]
        
        if len(good_matches) < 8:
            return None, None, None
        
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches])
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches])
        
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        
        if M is None:
            return None, None, None
        
        inliers = mask.ravel() == 1
        if np.sum(inliers) < 6:
            return None, None, None
        
        src_inliers = src_pts[inliers]
        dst_inliers = dst_pts[inliers]
        
        dx = np.mean(dst_inliers[:, 0] - src_inliers[:, 0])
        dy = np.mean(dst_inliers[:, 1] - src_inliers[:, 1])
        
        angle = self._estimate_rotation_from_homography(M)
        
        return dx, dy, angle
    
    def _estimate_rotation_from_homography(self, H):
        if H is None:
            return 0.0
        cos_theta = (H[0, 0] + H[1, 1]) / 2.0
        sin_theta = (H[1, 0] - H[0, 1]) / 2.0
        angle_rad = np.arctan2(sin_theta, cos_theta)
        return np.degrees(angle_rad)
    
    def _mutual_information_cost(self, params, ref_img, target_img):
        dx, dy, angle = params
        
        transformed = self._apply_transform(target_img, dx, dy, angle)
        
        mask = (transformed > 0) & (ref_img > 0)
        if np.sum(mask) < 100:
            return 1e6
        
        mi = self.evaluator.compute_mutual_information(ref_img[mask], transformed[mask])
        grad_sim = self.evaluator.compute_gradient_similarity(ref_img, transformed)
        
        return -(mi + 0.5 * grad_sim)
    
    def _apply_transform(self, img, dx, dy, angle, output_shape=None):
        if output_shape is None:
            rows, cols = img.shape
        else:
            rows, cols = output_shape
        
        src_rows, src_cols = img.shape
        
        angle_rad = np.deg2rad(angle)
        cos_theta = np.cos(angle_rad)
        sin_theta = np.sin(angle_rad)
        
        center_y = rows // 2
        center_x = cols // 2
        src_center_y = src_rows // 2
        src_center_x = src_cols // 2
        
        y_grid, x_grid = np.mgrid[0:rows, 0:cols]
        
        y_centered = y_grid - center_y - dy
        x_centered = x_grid - center_x - dx
        
        src_y = cos_theta * y_centered + sin_theta * x_centered + src_center_y
        src_x = -sin_theta * y_centered + cos_theta * x_centered + src_center_x
        
        coords = np.vstack([src_y.ravel(), src_x.ravel()])
        transformed = map_coordinates(img, coords, order=3, mode='constant', cval=0)
        transformed = transformed.reshape(rows, cols)
        
        return transformed
    
    def register(self, ref_img, target_img, method='hybrid'):
        if len(ref_img.shape) == 3:
            ref_gray = np.mean(ref_img, axis=2)
        else:
            ref_gray = ref_img.copy()
        
        if len(target_img.shape) == 3:
            target_gray = np.mean(target_img, axis=2)
        else:
            target_gray = target_img.copy()
        
        ref_gray = ref_gray.astype(np.float32)
        target_gray = target_gray.astype(np.float32)
        
        ref_preprocessed, ref_edge = self.preprocess_for_cross_modal(ref_gray)
        target_preprocessed, target_edge = self.preprocess_for_cross_modal(target_gray)
        
        dx = 0.0
        dy = 0.0
        angle = 0.0
        feature_success = False
        
        if method in ['feature', 'hybrid']:
            feat_dx, feat_dy, feat_angle = self.detect_and_match_features(
                ref_preprocessed, target_preprocessed
            )
            if feat_dx is not None:
                dx, dy, angle = feat_dx, feat_dy, feat_angle
                feature_success = True
        
        if method in ['phase', 'hybrid']:
            if not feature_success:
                try:
                    search_angles = np.arange(-20, 21, 2.0)
                    best_mi = -1e10
                    best_angle = 0.0
                    
                    for test_angle in search_angles:
                        target_rotated = rotate(target_edge, -test_angle, reshape=False, order=3, mode='constant', cval=0)
                        mi = self.evaluator.compute_mutual_information(ref_edge, target_rotated)
                        if mi > best_mi:
                            best_mi = mi
                            best_angle = test_angle
                    
                    angle = best_angle
                    
                    target_rotated = rotate(target_edge, -angle, reshape=False, order=3, mode='constant', cval=0)
                    phase_dx, phase_dy, corr = self.phase_registrator.estimate_translation(
                        ref_edge, target_rotated
                    )
                    
                    peak_val = np.max(corr)
                    if peak_val > 0.1 and abs(phase_dx) < 50 and abs(phase_dy) < 50:
                        dx = phase_dx
                        dy = phase_dy
                    else:
                        best_tmi = -1e10
                        for tx in np.arange(-20, 21, 2.0):
                            for ty in np.arange(-20, 21, 2.0):
                                target_shifted = shift(target_rotated, (ty, tx), order=3, mode='constant', cval=0)
                                tmi = self.evaluator.compute_mutual_information(ref_edge, target_shifted)
                                if tmi > best_tmi:
                                    best_tmi = tmi
                                    dx, dy = tx, ty
                except:
                    pass
            else:
                try:
                    target_rotated = rotate(target_edge, -angle, reshape=False, order=3, mode='constant', cval=0)
                    phase_dx, phase_dy, corr = self.phase_registrator.estimate_translation(
                        ref_edge, target_rotated
                    )
                    peak_val = np.max(corr)
                    if peak_val > 0.1 and abs(phase_dx) < 10 and abs(phase_dy) < 10:
                        dx = 0.6 * dx + 0.4 * phase_dx
                        dy = 0.6 * dy + 0.4 * phase_dy
                except:
                    pass
        
        if method in ['mi', 'hybrid']:
            initial_params = [dx, dy, angle]
            
            bounds = [
                (dx - 20, dx + 20),
                (dy - 20, dy + 20),
                (angle - 15, angle + 15)
            ]
            
            try:
                result = minimize(
                    self._mutual_information_cost,
                    initial_params,
                    args=(ref_edge, target_edge),
                    method='L-BFGS-B',
                    bounds=bounds,
                    options={'maxiter': 50, 'ftol': 1e-6}
                )
                
                if result.success:
                    dx, dy, angle = result.x
            except:
                pass
        
        transformed = self._apply_transform(target_gray, dx, dy, angle, ref_gray.shape)
        
        quality = self.evaluator.evaluate_all(ref_gray, transformed)
        
        return {
            'translation': (dx, dy),
            'rotation': angle,
            'scale': 1.0,
            'transformed': transformed,
            'quality': quality,
            'method': method
        }
    
    def register_multimodal(self, optical_img, infrared_img):
        return self.register(optical_img, infrared_img, method='hybrid')
