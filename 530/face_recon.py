import os
import cv2
import numpy as np
import torch
from torchvision import transforms
import config
from bfm_model import BFMModel
from face_detection import FaceDetector, LandmarkDetector, draw_landmarks, draw_face_box
from pose_estimation import PoseEstimator, LightEstimator
from param_regression import build_model, load_checkpoint
from renderer import FaceRenderer, Visualizer, save_obj, save_ply
from face_details import FaceDetailEnhancer, save_normal_map, save_displacement_map
from makeup_transfer import MakeupApplier, MakeupTransfer, apply_makeup_to_3d_model


class FaceReconstructor:
    def __init__(self, device='cpu', checkpoint_path=None):
        self.device = device
        
        self.bfm_model = BFMModel(device=device)
        self.face_detector = FaceDetector()
        self.landmark_detector = LandmarkDetector()
        self.pose_estimator = PoseEstimator()
        self.light_estimator = LightEstimator()
        
        self.model = build_model(backbone='resnet50', pretrained=True, device=device)
        
        if checkpoint_path and os.path.exists(checkpoint_path):
            self.model, _, _, _ = load_checkpoint(self.model, None, checkpoint_path, device)
            print(f"Loaded checkpoint from {checkpoint_path}")
        
        self.model.eval()
        
        self.renderer = FaceRenderer(image_size=config.IMG_SIZE, device=device)
        self.visualizer = Visualizer()
        
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((config.IMG_SIZE, config.IMG_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        self.detail_enhancer = FaceDetailEnhancer(device=device)
        self.makeup_applier = MakeupApplier()
        self.makeup_transfer = MakeupTransfer()
    
    def reconstruct(self, image_path, output_dir=None, save_results=True):
        if output_dir is None:
            output_dir = config.OUTPUT_DIR
        
        os.makedirs(output_dir, exist_ok=True)
        
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Cannot read image from {image_path}")
        
        original_image = image.copy()
        
        faces = self.face_detector.detect(image)
        if len(faces) == 0:
            print("No face detected!")
            return None
        
        face_box = faces[0]
        
        face_aligned, crop_box = self.face_detector.align_face(image, face_box, output_size=config.IMG_SIZE)
        
        landmarks = self.landmark_detector.detect_landmarks(face_aligned, (0, 0, config.IMG_SIZE, config.IMG_SIZE))
        
        input_tensor = self.transform(cv2.cvtColor(face_aligned, cv2.COLOR_BGR2RGB))
        input_tensor = input_tensor.unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            params = self.model(input_tensor)
        
        shape_param = params['shape']
        exp_param = params['exp']
        tex_param = params['tex']
        pose_param = params['pose']
        light_param = params['light']
        
        vertices = self.bfm_model.compute_shape(shape_param, exp_param)
        texture = self.bfm_model.compute_texture(tex_param)
        
        vertices_transformed = self.bfm_model.transform_vertices(vertices, pose_param)
        
        lit_texture, shading = self.bfm_model.apply_lighting(vertices_transformed, texture, light_param)
        
        landmarks_3d = self.bfm_model.get_landmarks(vertices_transformed)
        
        landmarks_2d = self.bfm_model.project_vertices(landmarks_3d)
        landmarks_2d = landmarks_2d.squeeze(0).cpu().numpy()
        
        rendered_image = self.renderer.render_texture(
            vertices_transformed.squeeze(0),
            self.bfm_model.tri,
            lit_texture.squeeze(0)
        )
        
        depth_map = self.renderer.render_depth(
            vertices_transformed.squeeze(0),
            self.bfm_model.tri
        )
        
        detail_results = self.detail_enhancer.enhance_face(
            face_aligned, landmarks, vertices_transformed.squeeze(0).cpu().numpy()
        )
        
        results = {
            'original_image': original_image,
            'aligned_face': face_aligned,
            'face_box': face_box,
            'landmarks': landmarks,
            'landmarks_3d': landmarks_3d,
            'landmarks_2d': landmarks_2d,
            'vertices': vertices_transformed,
            'texture': texture,
            'lit_texture': lit_texture,
            'rendered_image': rendered_image,
            'depth_map': depth_map,
            'params': params,
            'triangles': self.bfm_model.tri,
            'wrinkle_map': detail_results['wrinkle_map'],
            'pore_map': detail_results['pore_map'],
            'normal_map': detail_results['normal_map'],
            'displacement_map': detail_results['displacement_map'],
            'detailed_image': detail_results['detailed_image']
        }
        
        if save_results:
            self._save_results(results, output_dir)
        
        return results
    
    def _save_results(self, results, output_dir):
        cv2.imwrite(os.path.join(output_dir, 'original_image.jpg'), results['original_image'])
        cv2.imwrite(os.path.join(output_dir, 'aligned_face.jpg'), results['aligned_face'])
        
        img_with_box = draw_face_box(results['original_image'], results['face_box'])
        cv2.imwrite(os.path.join(output_dir, 'face_detection.jpg'), img_with_box)
        
        img_with_landmarks = draw_landmarks(results['aligned_face'], results['landmarks'])
        cv2.imwrite(os.path.join(output_dir, 'landmarks.jpg'), img_with_landmarks)
        
        cv2.imwrite(os.path.join(output_dir, 'rendered_face.jpg'), results['rendered_image'])
        
        depth_normalized = cv2.normalize(results['depth_map'], None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        cv2.imwrite(os.path.join(output_dir, 'depth_map.jpg'), depth_normalized)
        
        save_obj(
            results['vertices'].squeeze(0),
            results['triangles'],
            results['lit_texture'].squeeze(0),
            os.path.join(output_dir, 'face_mesh.obj')
        )
        
        save_ply(
            results['vertices'].squeeze(0),
            results['triangles'],
            results['lit_texture'].squeeze(0),
            os.path.join(output_dir, 'face_mesh.ply')
        )
        
        self.visualizer.plot_3d_face(
            results['vertices'].squeeze(0),
            results['triangles'],
            save_path=os.path.join(output_dir, '3d_face_plot.png')
        )
        
        self.visualizer.plot_results_comparison(
            results['aligned_face'],
            results['landmarks_2d'],
            results['rendered_image'],
            results['depth_map'],
            save_path=os.path.join(output_dir, 'results_comparison.png')
        )
        
        self.visualizer.plot_params(
            results['params'],
            save_path=os.path.join(output_dir, 'parameters.png')
        )
        
        np.savez(os.path.join(output_dir, 'params.npz'), **{k: v.cpu().numpy() for k, v in results['params'].items()})
        
        cv2.imwrite(os.path.join(output_dir, 'wrinkle_map.jpg'), 
                    (results['wrinkle_map'] * 255).astype(np.uint8))
        cv2.imwrite(os.path.join(output_dir, 'pore_map.jpg'), 
                    (results['pore_map'] * 255).astype(np.uint8))
        save_normal_map(results['normal_map'], os.path.join(output_dir, 'normal_map.jpg'))
        save_displacement_map(results['displacement_map'], os.path.join(output_dir, 'displacement_map.jpg'))
        cv2.imwrite(os.path.join(output_dir, 'detailed_image.jpg'), results['detailed_image'])
        
        print(f"Results saved to {output_dir}")
    
    def reconstruct_from_image(self, image, output_dir=None, save_results=True):
        temp_path = os.path.join(config.DATA_DIR, 'temp_input.jpg')
        cv2.imwrite(temp_path, image)
        return self.reconstruct(temp_path, output_dir, save_results)
    
    def apply_makeup(self, image, landmarks, style='natural', output_dir=None):
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        makeup_result = self.makeup_applier.apply_makeup(image, landmarks, style=style)
        
        if output_dir:
            cv2.imwrite(os.path.join(output_dir, f'makeup_{style}.jpg'), makeup_result)
        
        return makeup_result
    
    def transfer_makeup(self, source_image, source_landmarks, 
                        target_image, target_landmarks, output_dir=None):
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        transferred = self.makeup_transfer.transfer_makeup(
            source_image, source_landmarks, target_image, target_landmarks
        )
        
        if output_dir:
            cv2.imwrite(os.path.join(output_dir, 'makeup_transferred.jpg'), transferred)
        
        return transferred
    
    def apply_makeup_to_3d(self, vertices, texture, landmarks, style='natural'):
        textured_result = apply_makeup_to_3d_model(
            vertices, texture, landmarks, style
        )
        return textured_result
    
    def get_available_makeup_styles(self):
        return list(self.makeup_applier.makeup_styles.keys())


def create_demo_image(output_path='demo_face.jpg'):
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    img[:] = (200, 200, 200)
    
    center = (200, 200)
    face_radius = 150
    cv2.ellipse(img, center, (face_radius, int(face_radius * 1.2)), 0, 0, 360, (240, 200, 160), -1)
    
    left_eye = (140, 160)
    right_eye = (260, 160)
    cv2.circle(img, left_eye, 20, (255, 255, 255), -1)
    cv2.circle(img, right_eye, 20, (255, 255, 255), -1)
    cv2.circle(img, left_eye, 10, (50, 50, 50), -1)
    cv2.circle(img, right_eye, 10, (50, 50, 50), -1)
    
    cv2.ellipse(img, (200, 220), (15, 20), 0, 0, 360, (200, 150, 120), -1)
    
    cv2.ellipse(img, (200, 280), (50, 20), 0, 0, 180, (150, 80, 80), -1)
    
    cv2.ellipse(img, (120, 250), (20, 15), 0, 0, 360, (220, 150, 130), -1)
    cv2.ellipse(img, (280, 250), (20, 15), 0, 0, 360, (220, 150, 130), -1)
    
    cv2.ellipse(img, (200, 90), (140, 50), 0, 0, 360, (50, 40, 30), -1)
    
    cv2.imwrite(output_path, img)
    print(f"Demo image saved to {output_path}")
    return output_path


def main():
    print("=" * 70)
    print("3D Face Reconstruction System with Advanced Features")
    print("=" * 70)
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Using device: {device}")
    
    reconstructor = FaceReconstructor(device=device)
    
    demo_image_path = create_demo_image(os.path.join(config.DATA_DIR, 'demo_face.jpg'))
    
    print("\n[Phase 1] Starting 3D face reconstruction with detail enhancement...")
    results = reconstructor.reconstruct(demo_image_path)
    
    if results is not None:
        print("\nReconstruction completed successfully!")
        print(f"  - Shape parameter dimension: {results['params']['shape'].shape[1]}")
        print(f"  - Expression parameter dimension: {results['params']['exp'].shape[1]}")
        print(f"  - Texture parameter dimension: {results['params']['tex'].shape[1]}")
        print(f"  - Pose parameter dimension: {results['params']['pose'].shape[1]}")
        print(f"  - Light parameter dimension: {results['params']['light'].shape[1]}")
        print(f"\n  Detail maps generated:")
        print(f"  - Wrinkle map: {results['wrinkle_map'].shape}")
        print(f"  - Pore map: {results['pore_map'].shape}")
        print(f"  - Normal map: {results['normal_map'].shape}")
        print(f"  - Displacement map: {results['displacement_map'].shape}")
        
        print("\n[Phase 2] Applying makeup styles...")
        available_styles = reconstructor.get_available_makeup_styles()
        print(f"Available makeup styles: {available_styles}")
        
        for style in available_styles:
            makeup_result = reconstructor.apply_makeup(
                results['aligned_face'], 
                results['landmarks'], 
                style=style,
                output_dir=os.path.join(config.OUTPUT_DIR, 'makeup')
            )
            print(f"  - Applied {style} makeup")
        
        print("\n[Phase 3] 3D model makeup application...")
        makeup_texture = reconstructor.apply_makeup_to_3d(
            results['vertices'].squeeze(0).cpu().numpy(),
            results['lit_texture'].squeeze(0).cpu().numpy(),
            results['landmarks'],
            style='glam'
        )
        print("  - Applied glam makeup to 3D model texture")
        
        print(f"\nAll results saved to: {config.OUTPUT_DIR}")
    else:
        print("Reconstruction failed!")
    
    print("\n" + "=" * 70)
    print("Quick Start Guide:")
    print("  1. To run real-time face tracking:")
    print("     python realtime_driver.py")
    print("  2. To train with enhanced losses:")
    print("     python train.py")
    print("  3. Available makeup styles:", reconstructor.get_available_makeup_styles())
    print("=" * 70)


if __name__ == '__main__':
    main()
