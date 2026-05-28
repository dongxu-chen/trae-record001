import os
import cv2
import numpy as np
import torch
import torch.nn as nn
from typing import Tuple, Optional, Dict, List
from tqdm import tqdm

from models.reflection_separation_net import ReflectionSeparationNet, PerceptualLoss
from models.polarization_estimator import PolarizationEstimator, TraditionalPolarizationEstimator
from core.texture_synthesis import TextureSynthesizer
from data.dataset import denormalize, tensor_to_numpy
from config import Config


class ReflectionRemover:
    def __init__(self, config: Config, model_path: Optional[str] = None):
        self.config = config
        self.device = torch.device(config.inference.device)
        
        self.model = ReflectionSeparationNet(
            n_channels=config.model.n_channels,
            bilinear=config.model.bilinear,
            use_polarization=config.model.use_polarization
        ).to(self.device)
        
        if model_path and os.path.exists(model_path):
            self.load_checkpoint(model_path)
        
        self.model.eval()
        
        self.texture_synthesizer = None
        if config.inference.enable_texture_synthesis:
            from core.texture_synthesis import InpaintingConfig
            inpaint_config = InpaintingConfig(
                patch_size=config.inpainting.patch_size,
                alpha_threshold=config.inpainting.alpha_threshold,
                max_iterations=config.inpainting.max_iterations,
                confidence_threshold=config.inpainting.confidence_threshold,
                poisson_blending=config.inpainting.poisson_blending,
                use_telea=config.inpainting.use_telea,
                telea_radius=config.inpainting.telea_radius
            )
            self.texture_synthesizer = TextureSynthesizer(inpaint_config)
        
        self.polarization_estimator = None
        if config.inference.enable_polarization_estimation and config.polarization.estimate_from_image:
            if config.polarization.use_traditional_method:
                self.polarization_estimator = TraditionalPolarizationEstimator()
            else:
                self.polarization_estimator = PolarizationEstimator(
                    model_path=config.polarization.polarization_model_path,
                    device=config.inference.device
                )
    
    def load_checkpoint(self, checkpoint_path: str):
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        if 'model_state_dict' in checkpoint:
            self.model.load_state_dict(checkpoint['model_state_dict'])
        else:
            self.model.load_state_dict(checkpoint)
        print(f"Loaded checkpoint from {checkpoint_path}")
    
    @torch.no_grad()
    def remove_reflection(
        self,
        image: np.ndarray,
        polarization_image: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        original_size = image.shape[:2]
        
        estimated_polarization = None
        if self.polarization_estimator is not None and polarization_image is None:
            estimated_polarization = self.polarization_estimator.estimate(image)
            dolp = estimated_polarization['dolp']
            pol_channels = np.stack([dolp, dolp, dolp], axis=-1)
            pol_channels = (pol_channels * 255).astype(np.uint8)
            polarization_image = pol_channels
        
        input_tensor = self._preprocess(image)
        pol_tensor = self._preprocess(polarization_image) if polarization_image is not None else None
        
        input_tensor = input_tensor.to(self.device)
        if pol_tensor is not None:
            pol_tensor = pol_tensor.to(self.device)
        
        transmission, reflection, alpha = self.model(input_tensor, pol_tensor)
        
        transmission_np = tensor_to_numpy(transmission, denorm=False)[0]
        reflection_np = tensor_to_numpy(reflection, denorm=False)[0]
        alpha_np = (alpha.squeeze().cpu().numpy() * 255).astype(np.uint8)
        input_np = tensor_to_numpy(input_tensor, denorm=True)[0]
        
        if self.config.inference.apply_post_processing:
            transmission_np = self._post_process(transmission_np, input_np)
        
        if original_size != transmission_np.shape[:2]:
            transmission_np = cv2.resize(transmission_np, (original_size[1], original_size[0]))
            reflection_np = cv2.resize(reflection_np, (original_size[1], original_size[0]))
            alpha_np = cv2.resize(alpha_np, (original_size[1], original_size[0]))
            input_np = cv2.resize(input_np, (original_size[1], original_size[0]))
        
        inpainted = None
        strong_reflection_mask = None
        if self.texture_synthesizer is not None:
            inpainted, strong_reflection_mask = self.texture_synthesizer.restore_strong_reflection(
                image=input_np,
                alpha_mask=alpha_np,
                reflection=reflection_np,
                initial_restoration=transmission_np
            )
            fusion_weight = self.config.polarization.fusion_weight
            transmission_np = cv2.addWeighted(
                inpainted, fusion_weight,
                transmission_np, 1 - fusion_weight,
                0
            )
            transmission_np = np.clip(transmission_np, 0, 255).astype(np.uint8)
        
        result = {
            'input': input_np,
            'transmission': transmission_np,
            'reflection': reflection_np,
            'alpha': alpha_np
        }
        
        if estimated_polarization is not None:
            result['estimated_dolp'] = estimated_polarization['dolp']
            result['estimated_aop'] = estimated_polarization['aop']
            result['polarization_mask'] = estimated_polarization['polarization_mask']
        
        if inpainted is not None:
            result['inpainted'] = inpainted
            result['strong_reflection_mask'] = strong_reflection_mask
        
        return result
    
    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        if image.shape[:2] != self.config.model.image_size:
            image = cv2.resize(image, (self.config.model.image_size[1], self.config.model.image_size[0]))
        
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if len(image.shape) == 3 else image
        
        image = image.astype(np.float32) / 255.0
        
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        image = (image - mean) / std
        
        tensor = torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0)
        return tensor
    
    def _post_process(self, transmission: np.ndarray, input_image: np.ndarray) -> np.ndarray:
        transmission_ycrcb = cv2.cvtColor(transmission, cv2.COLOR_RGB2YCrCb)
        input_ycrcb = cv2.cvtColor(input_image, cv2.COLOR_RGB2YCrCb)
        
        transmission_ycrcb[:, :, 0] = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(
            transmission_ycrcb[:, :, 0]
        )
        
        transmission_enhanced = cv2.cvtColor(transmission_ycrcb, cv2.COLOR_YCrCb2RGB)
        
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]], dtype=np.float32)
        transmission_sharp = cv2.filter2D(transmission_enhanced, -1, kernel)
        
        weight = 0.7
        transmission_final = cv2.addWeighted(transmission_enhanced, weight, transmission_sharp, 1 - weight, 0)
        
        return np.clip(transmission_final, 0, 255).astype(np.uint8)

    def train(self, train_loader, val_loader, num_epochs: Optional[int] = None):
        epochs = num_epochs if num_epochs else self.config.training.epochs
        
        optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=self.config.training.learning_rate,
            betas=(self.config.training.beta1, self.config.training.beta2),
            weight_decay=self.config.training.weight_decay
        )
        
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=epochs, eta_min=1e-6
        )
        
        criterion = PerceptualLoss().to(self.device)
        
        best_loss = float('inf')
        
        for epoch in range(epochs):
            self.model.train()
            total_loss = 0
            loss_components = {}
            
            pbar = tqdm(train_loader, desc=f'Epoch {epoch+1}/{epochs}')
            for batch_idx, batch in enumerate(pbar):
                images = batch['image'].to(self.device)
                target_t = batch['transmission'].to(self.device) if 'transmission' in batch else None
                target_r = batch['reflection'].to(self.device) if 'reflection' in batch else None
                pol_images = batch['polarization'].to(self.device) if 'polarization' in batch else None
                
                if target_t is None:
                    target_t = denormalize(images) * 0.8
                if target_r is None:
                    target_r = denormalize(images) * 0.2
                
                optimizer.zero_grad()
                
                pred_t, pred_r, pred_alpha = self.model(images, pol_images)
                
                losses = criterion(pred_t, pred_r, pred_alpha, target_t, target_r, denormalize(images))
                
                loss = losses['total']
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
                
                for k, v in losses.items():
                    if k not in loss_components:
                        loss_components[k] = 0
                    loss_components[k] += v.item()
                
                if batch_idx % self.config.training.log_interval == 0:
                    pbar.set_postfix({
                        'loss': f'{loss.item():.4f}',
                        't_loss': f'{losses["transmission"].item():.4f}',
                        'r_loss': f'{losses["reflection"].item():.4f}'
                    })
            
            avg_loss = total_loss / len(train_loader)
            avg_components = {k: v / len(train_loader) for k, v in loss_components.items()}
            
            print(f'\nEpoch {epoch+1} Average Loss: {avg_loss:.4f}')
            for k, v in avg_components.items():
                print(f'  {k}: {v:.4f}')
            
            val_loss = self.validate(val_loader, criterion)
            print(f'Validation Loss: {val_loss:.4f}')
            
            scheduler.step()
            
            if val_loss < best_loss:
                best_loss = val_loss
                self.save_checkpoint('checkpoints/best_model.pth', epoch, optimizer, val_loss)
                print(f'Saved best model with loss {best_loss:.4f}')
            
            if (epoch + 1) % self.config.training.save_interval == 0:
                self.save_checkpoint(f'checkpoints/epoch_{epoch+1}.pth', epoch, optimizer, val_loss)
    
    @torch.no_grad()
    def validate(self, val_loader, criterion) -> float:
        self.model.eval()
        total_loss = 0
        
        for batch in tqdm(val_loader, desc='Validation'):
            images = batch['image'].to(self.device)
            target_t = batch['transmission'].to(self.device) if 'transmission' in batch else None
            target_r = batch['reflection'].to(self.device) if 'reflection' in batch else None
            pol_images = batch['polarization'].to(self.device) if 'polarization' in batch else None
            
            if target_t is None:
                target_t = denormalize(images) * 0.8
            if target_r is None:
                target_r = denormalize(images) * 0.2
            
            pred_t, pred_r, pred_alpha = self.model(images, pol_images)
            losses = criterion(pred_t, pred_r, pred_alpha, target_t, target_r, denormalize(images))
            
            total_loss += losses['total'].item()
        
        return total_loss / len(val_loader)
    
    def save_checkpoint(self, path: str, epoch: int, optimizer: torch.optim.Optimizer, loss: float):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        torch.save({
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'loss': loss,
        }, path)
