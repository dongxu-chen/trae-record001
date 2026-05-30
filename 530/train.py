import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import cv2
from tqdm import tqdm

import config
from bfm_model import BFMModel
from param_regression import build_model, save_checkpoint
from losses import EnhancedTotalLoss, LargeAnglePoseLoss, CrossLightingTextureLoss
from data_augmentation import FaceDataAugmentationPipeline, random_occlusion, add_noise


class FaceDataset(Dataset):
    def __init__(self, image_dir=None, transform=None, use_augmentation=True):
        self.image_dir = image_dir
        self.transform = transform
        self.use_augmentation = use_augmentation
        
        self.image_paths = self._load_image_paths()
        self.aug_pipeline = FaceDataAugmentationPipeline()
    
    def _load_image_paths(self):
        paths = []
        if self.image_dir and os.path.exists(self.image_dir):
            for ext in ['*.jpg', '*.jpeg', '*.png']:
                paths.extend(glob.glob(os.path.join(self.image_dir, ext)))
        
        if len(paths) == 0:
            print("Warning: No images found, using synthetic data for demonstration")
            paths = [None] * 100
        
        return paths
    
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        if self.image_paths[idx] is None:
            image = self._generate_synthetic_face()
        else:
            image = cv2.imread(self.image_paths[idx])
            image = cv2.resize(image, (config.IMG_SIZE, config.IMG_SIZE))
        
        if self.use_augmentation:
            aug_results = self.aug_pipeline(image)
            image = aug_results['augmented']
            image = random_occlusion(image)
            image = add_noise(image)
        
        if self.transform:
            image = self.transform(image)
        
        return image
    
    def _generate_synthetic_face(self):
        img = np.zeros((config.IMG_SIZE, config.IMG_SIZE, 3), dtype=np.uint8)
        img[:] = (200, 200, 200)
        
        center = (config.IMG_SIZE // 2, config.IMG_SIZE // 2)
        face_radius = int(config.IMG_SIZE * 0.35)
        cv2.ellipse(img, center, (face_radius, int(face_radius * 1.2)), 0, 0, 360, (240, 200, 160), -1)
        
        left_eye = (int(config.IMG_SIZE * 0.35), int(config.IMG_SIZE * 0.4))
        right_eye = (int(config.IMG_SIZE * 0.65), int(config.IMG_SIZE * 0.4))
        cv2.circle(img, left_eye, int(face_radius * 0.15), (255, 255, 255), -1)
        cv2.circle(img, right_eye, int(face_radius * 0.15), (255, 255, 255), -1)
        cv2.circle(img, left_eye, int(face_radius * 0.08), (50, 50, 50), -1)
        cv2.circle(img, right_eye, int(face_radius * 0.08), (50, 50, 50), -1)
        
        cv2.ellipse(img, (center[0], int(config.IMG_SIZE * 0.55)), 
                   (int(face_radius * 0.1), int(face_radius * 0.15)), 0, 0, 360, (200, 150, 120), -1)
        
        cv2.ellipse(img, (center[0], int(config.IMG_SIZE * 0.7)), 
                   (int(face_radius * 0.3), int(face_radius * 0.15)), 0, 0, 180, (150, 80, 80), -1)
        
        return img


class EnhancedTrainer:
    def __init__(self, device='cuda' if torch.cuda.is_available() else 'cpu'):
        self.device = device
        
        self.bfm_model = BFMModel(device=device)
        self.model = build_model(backbone='resnet50', pretrained=True, device=device)
        
        self.criterion = EnhancedTotalLoss(device=device)
        self.pose_loss = LargeAnglePoseLoss(weight=0.5)
        self.cross_light_loss = CrossLightingTextureLoss(weight=0.05)
        
        self.optimizer = optim.Adam(self.model.parameters(), lr=config.LEARNING_RATE)
        self.scheduler = optim.lr_scheduler.StepLR(self.optimizer, step_size=20, gamma=0.5)
        
        self.aug_pipeline = FaceDataAugmentationPipeline()
        
        self.train_losses = []
        self.val_losses = []
    
    def train_step(self, batch_images):
        self.model.train()
        self.optimizer.zero_grad()
        
        batch_size = batch_images.shape[0]
        
        params = self.model(batch_images)
        
        shape_param = params['shape']
        exp_param = params['exp']
        tex_param = params['tex']
        pose_param = params['pose']
        light_param = params['light']
        
        vertices = self.bfm_model.compute_shape(shape_param, exp_param)
        texture = self.bfm_model.compute_texture(tex_param)
        vertices_transformed = self.bfm_model.transform_vertices(vertices, pose_param)
        lit_texture, _ = self.bfm_model.apply_lighting(vertices_transformed, texture, light_param)
        
        landmarks_3d = self.bfm_model.get_landmarks(vertices_transformed)
        landmarks_2d = self.bfm_model.project_vertices(landmarks_3d)
        
        pred_dict = {
            'landmarks': landmarks_2d,
            'albedo': texture
        }
        
        target_dict = {}
        if 'target_landmarks' in batch_images:
            target_dict['landmarks'] = batch_images['target_landmarks']
        
        loss, loss_dict = self.criterion(
            pred_dict, target_dict, params,
            self.bfm_model.idBase_t, self.bfm_model.expBase_t
        )
        
        pose_loss = self.pose_loss(pose_param)
        loss += pose_loss
        loss_dict['pose'] = pose_loss.item()
        
        loss.backward()
        self.optimizer.step()
        
        return loss.item(), loss_dict
    
    def train_with_multi_view(self, images_list, angles_list):
        self.model.train()
        self.optimizer.zero_grad()
        
        total_loss = 0.0
        
        textures_list = []
        
        for images in images_list:
            params = self.model(images)
            
            shape_param = params['shape']
            exp_param = params['exp']
            tex_param = params['tex']
            pose_param = params['pose']
            light_param = params['light']
            
            vertices = self.bfm_model.compute_shape(shape_param, exp_param)
            texture = self.bfm_model.compute_texture(tex_param)
            textures_list.append(texture)
            
            vertices_transformed = self.bfm_model.transform_vertices(vertices, pose_param)
            lit_texture, _ = self.bfm_model.apply_lighting(vertices_transformed, texture, light_param)
            
            landmarks_3d = self.bfm_model.get_landmarks(vertices_transformed)
            landmarks_2d = self.bfm_model.project_vertices(landmarks_3d)
            
            pred_dict = {'landmarks': landmarks_2d, 'albedo': texture}
            target_dict = {}
            
            loss, _ = self.criterion(pred_dict, target_dict, params,
                                     self.bfm_model.idBase_t, self.bfm_model.expBase_t)
            total_loss += loss
        
        if len(textures_list) >= 2:
            cross_light_loss = self.cross_light_loss(textures_list[0], textures_list[1:])
            total_loss += cross_light_loss
        
        total_loss.backward()
        self.optimizer.step()
        
        return total_loss.item()
    
    def train(self, num_epochs=None, batch_size=None):
        if num_epochs is None:
            num_epochs = config.NUM_EPOCHS
        if batch_size is None:
            batch_size = config.BATCH_SIZE
        
        from torchvision import transforms
        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((config.IMG_SIZE, config.IMG_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        train_dataset = FaceDataset(transform=transform, use_augmentation=True)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
        
        print(f"Starting training for {num_epochs} epochs...")
        print(f"Device: {self.device}")
        print(f"Number of batches per epoch: {len(train_loader)}")
        
        for epoch in range(num_epochs):
            epoch_loss = 0.0
            num_batches = 0
            
            pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{num_epochs}")
            
            for batch in pbar:
                if isinstance(batch, dict):
                    batch_images = batch['image'].to(self.device)
                else:
                    batch_images = batch.to(self.device)
                
                loss, loss_dict = self.train_step(batch_images)
                
                epoch_loss += loss
                num_batches += 1
                
                pbar.set_postfix({'loss': loss})
            
            avg_loss = epoch_loss / num_batches
            self.train_losses.append(avg_loss)
            
            self.scheduler.step()
            
            print(f"Epoch {epoch+1}/{num_epochs}, Average Loss: {avg_loss:.6f}")
            
            if (epoch + 1) % 10 == 0:
                checkpoint_path = os.path.join(config.CHECKPOINT_DIR, f'checkpoint_epoch_{epoch+1}.pth')
                save_checkpoint(self.model, self.optimizer, epoch+1, avg_loss, checkpoint_path)
                print(f"Saved checkpoint to {checkpoint_path}")
        
        final_checkpoint_path = os.path.join(config.CHECKPOINT_DIR, 'final_model.pth')
        save_checkpoint(self.model, self.optimizer, num_epochs, self.train_losses[-1], final_checkpoint_path)
        print(f"Training completed. Final model saved to {final_checkpoint_path}")
        
        return self.train_losses
    
    def train_with_mixed_pose(self, num_epochs=50):
        print("Training with mixed pose augmentation...")
        
        from torchvision import transforms
        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((config.IMG_SIZE, config.IMG_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        dataset = FaceDataset(transform=transform, use_augmentation=False)
        loader = DataLoader(dataset, batch_size=config.BATCH_SIZE, shuffle=True)
        
        for epoch in range(num_epochs):
            epoch_loss = 0.0
            num_batches = 0
            
            for batch in tqdm(loader, desc=f"Epoch {epoch+1}/{num_epochs}"):
                images = batch.to(self.device)
                
                original_params = self.model(images)
                
                aug_results = self.aug_pipeline.generate_multi_view_batch(images[0], num_views=3)
                
                aug_images = [transform(img).unsqueeze(0).to(self.device) for img in aug_results[0]]
                aug_images = torch.cat(aug_images, dim=0)
                
                aug_params = self.model(aug_images)
                
                consistency_loss = torch.mean((aug_params['shape'] - original_params['shape'].repeat(3, 1)) ** 2)
                consistency_loss += torch.mean((aug_params['exp'] - original_params['exp'].repeat(3, 1)) ** 2)
                
                loss, _ = self.criterion({'landmarks': torch.zeros(1, 68, 2).to(self.device)}, {}, original_params)
                loss += 0.1 * consistency_loss
                
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
                
                epoch_loss += loss.item()
                num_batches += 1
            
            print(f"Epoch {epoch+1}, Loss: {epoch_loss/num_batches:.6f}")
            self.scheduler.step()
        
        return self.model
    
    def fine_tune_with_cross_lighting(self, num_epochs=20):
        print("Fine-tuning with cross-lighting consistency...")
        
        from torchvision import transforms
        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((config.IMG_SIZE, config.IMG_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        dataset = FaceDataset(transform=transform, use_augmentation=False)
        loader = DataLoader(dataset, batch_size=8, shuffle=True)
        
        for epoch in range(num_epochs):
            epoch_loss = 0.0
            num_batches = 0
            
            for batch in tqdm(loader, desc=f"Fine-tune Epoch {epoch+1}/{num_epochs}"):
                images = batch.to(self.device)
                
                base_params = self.model(images)
                
                base_texture = self.bfm_model.compute_texture(base_params['tex'])
                
                lit_textures_list = []
                for _ in range(3):
                    light_variation = torch.randn_like(base_params['light']) * 0.5
                    varied_light = base_params['light'] + light_variation.to(self.device)
                    
                    vertices = self.bfm_model.compute_shape(base_params['shape'], base_params['exp'])
                    vertices_t = self.bfm_model.transform_vertices(vertices, base_params['pose'])
                    lit_texture, _ = self.bfm_model.apply_lighting(vertices_t, base_texture, varied_light)
                    lit_textures_list.append(lit_texture)
                
                cross_light_loss = self.cross_light_loss(base_texture, lit_textures_list)
                
                total_loss = cross_light_loss
                
                self.optimizer.zero_grad()
                total_loss.backward()
                self.optimizer.step()
                
                epoch_loss += total_loss.item()
                num_batches += 1
            
            print(f"Fine-tune Epoch {epoch+1}, Loss: {epoch_loss/num_batches:.6f}")
        
        return self.model
    
    def get_model(self):
        return self.model


def train_with_all_enhancements():
    print("=" * 60)
    print("Training with all enhancements:")
    print("1. Parameter orthogonality constraint")
    print("2. Large angle pose augmentation")
    print("3. Cross-lighting consistency")
    print("=" * 60)
    
    trainer = EnhancedTrainer()
    
    print("\nPhase 1: Initial training with pose augmentation")
    trainer.train(num_epochs=30)
    
    print("\nPhase 2: Mixed pose training for robustness")
    trainer.train_with_mixed_pose(num_epochs=10)
    
    print("\nPhase 3: Fine-tuning with cross-lighting consistency")
    trainer.fine_tune_with_cross_lighting(num_epochs=10)
    
    print("\nTraining complete!")
    return trainer


if __name__ == '__main__':
    import glob
    train_with_all_enhancements()
