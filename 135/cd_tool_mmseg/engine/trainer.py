# Copyright (c) Remote Sensing Change Detection Team. All rights reserved.

import os
import time
import torch
import torch.nn as nn
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler
from torch.cuda.amp import autocast, GradScaler
import numpy as np
from tqdm import tqdm


class Trainer:
    def __init__(self, model, optimizer, lr_scheduler=None, loss_fn=None,
                 device='cuda', use_amp=False, grad_accum_steps=1,
                 max_grad_norm=None, work_dir='./work_dirs', logger=None):
        self.model = model
        self.optimizer = optimizer
        self.lr_scheduler = lr_scheduler
        self.loss_fn = loss_fn
        self.device = device
        self.use_amp = use_amp
        self.grad_accum_steps = grad_accum_steps
        self.max_grad_norm = max_grad_norm
        self.work_dir = work_dir
        self.logger = logger
        
        self.scaler = GradScaler() if use_amp else None
        self.rank = 0
        self.world_size = 1
        
        os.makedirs(work_dir, exist_ok=True)

    def setup_distributed(self, rank, world_size, backend='nccl'):
        self.rank = rank
        self.world_size = world_size
        
        os.environ['MASTER_ADDR'] = 'localhost'
        os.environ['MASTER_PORT'] = '12355'
        
        dist.init_process_group(backend, rank=rank, world_size=world_size)
        torch.cuda.set_device(rank)
        
        self.model = self.model.to(rank)
        self.model = DDP(self.model, device_ids=[rank], find_unused_parameters=True)

    def cleanup_distributed(self):
        if dist.is_initialized():
            dist.destroy_process_group()

    def train_epoch(self, dataloader, epoch, total_epochs):
        self.model.train()
        total_loss = 0.0
        num_batches = len(dataloader)
        
        if self.rank == 0:
            pbar = tqdm(total=num_batches, desc=f'Epoch {epoch + 1}/{total_epochs}')
        
        for batch_idx, batch_data in enumerate(dataloader):
            img1 = batch_data['img1'].to(self.device)
            img2 = batch_data['img2'].to(self.device)
            mask = batch_data['mask'].to(self.device)
            
            step = epoch * num_batches + batch_idx
            
            if self.use_amp:
                with autocast():
                    output = self.model(img1, img2)
                    loss = self.loss_fn(output, mask)
                    loss = loss / self.grad_accum_steps
                
                self.scaler.scale(loss).backward()
                
                if (batch_idx + 1) % self.grad_accum_steps == 0:
                    if self.max_grad_norm is not None:
                        self.scaler.unscale_(self.optimizer)
                        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                    
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                    self.optimizer.zero_grad()
                    
                    if self.lr_scheduler is not None:
                        self.lr_scheduler.step()
            else:
                output = self.model(img1, img2)
                loss = self.loss_fn(output, mask)
                loss = loss / self.grad_accum_steps
                
                loss.backward()
                
                if (batch_idx + 1) % self.grad_accum_steps == 0:
                    if self.max_grad_norm is not None:
                        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                    
                    self.optimizer.step()
                    self.optimizer.zero_grad()
                    
                    if self.lr_scheduler is not None:
                        self.lr_scheduler.step()
            
            total_loss += loss.item() * self.grad_accum_steps
            
            if self.rank == 0:
                pbar.update(1)
                pbar.set_postfix({'loss': f'{loss.item() * self.grad_accum_steps:.4f}'})
        
        if self.rank == 0:
            pbar.close()
        
        avg_loss = total_loss / num_batches
        return avg_loss

    @torch.no_grad()
    def validate(self, dataloader, metrics=None):
        self.model.eval()
        total_metrics = {}
        
        for batch_data in dataloader:
            img1 = batch_data['img1'].to(self.device)
            img2 = batch_data['img2'].to(self.device)
            mask = batch_data['mask'].to(self.device)
            
            output = self.model(img1, img2)
            pred = torch.sigmoid(output) > 0.5
            
            if metrics is not None:
                for name, metric_fn in metrics.items():
                    value = metric_fn(pred, mask)
                    if name not in total_metrics:
                        total_metrics[name] = 0.0
                    total_metrics[name] += value
        
        for name in total_metrics:
            total_metrics[name] /= len(dataloader)
        
        return total_metrics

    def train(self, train_loader, val_loader=None, num_epochs=100,
              val_interval=1, save_interval=10, metrics=None):
        best_metric = 0.0
        start_time = time.time()
        
        for epoch in range(num_epochs):
            train_loss = self.train_epoch(train_loader, epoch, num_epochs)
            
            if self.rank == 0:
                log_str = f'Epoch {epoch + 1}, Train Loss: {train_loss:.4f}'
                
                if val_loader is not None and (epoch + 1) % val_interval == 0:
                    val_metrics = self.validate(val_loader, metrics)
                    for name, value in val_metrics.items():
                        log_str += f', Val {name}: {value:.4f}'
                    
                    if 'IoU' in val_metrics and val_metrics['IoU'] > best_metric:
                        best_metric = val_metrics['IoU']
                        self.save_checkpoint(os.path.join(self.work_dir, 'best_model.pth'))
                
                if (epoch + 1) % save_interval == 0:
                    self.save_checkpoint(os.path.join(self.work_dir, f'epoch_{epoch + 1}.pth'))
                
                if self.logger is not None:
                    self.logger.info(log_str)
                else:
                    print(log_str)
        
        total_time = time.time() - start_time
        if self.rank == 0:
            print(f'Training completed in {total_time / 3600:.2f} hours')
            if best_metric > 0:
                print(f'Best Val IoU: {best_metric:.4f}')

    def save_checkpoint(self, path):
        if isinstance(self.model, DDP):
            state_dict = self.model.module.state_dict()
        else:
            state_dict = self.model.state_dict()
        
        checkpoint = {
            'model_state_dict': state_dict,
            'optimizer_state_dict': self.optimizer.state_dict(),
        }
        if self.lr_scheduler is not None:
            checkpoint['lr_scheduler_state_dict'] = self.lr_scheduler.state_dict()
        
        torch.save(checkpoint, path)

    def load_checkpoint(self, path, load_optimizer=True):
        checkpoint = torch.load(path, map_location=self.device)
        
        if isinstance(self.model, DDP):
            self.model.module.load_state_dict(checkpoint['model_state_dict'])
        else:
            self.model.load_state_dict(checkpoint['model_state_dict'])
        
        if load_optimizer and 'optimizer_state_dict' in checkpoint:
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        
        if self.lr_scheduler is not None and 'lr_scheduler_state_dict' in checkpoint:
            self.lr_scheduler.load_state_dict(checkpoint['lr_scheduler_state_dict'])


def distributed_train(rank, world_size, model, optimizer, train_dataset, val_dataset,
                      loss_fn=None, lr_scheduler=None, batch_size=8, num_epochs=100,
                      num_workers=4, use_amp=False, work_dir='./work_dirs'):
    trainer = Trainer(
        model=model,
        optimizer=optimizer,
        lr_scheduler=lr_scheduler,
        loss_fn=loss_fn,
        device=rank,
        use_amp=use_amp,
        work_dir=work_dir
    )
    
    trainer.setup_distributed(rank, world_size)
    
    train_sampler = DistributedSampler(train_dataset, num_replicas=world_size, rank=rank, shuffle=True)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, sampler=train_sampler,
                              num_workers=num_workers, pin_memory=True)
    
    val_sampler = DistributedSampler(val_dataset, num_replicas=world_size, rank=rank, shuffle=False)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, sampler=val_sampler,
                            num_workers=num_workers, pin_memory=True)
    
    trainer.train(train_loader, val_loader, num_epochs=num_epochs)
    trainer.cleanup_distributed()
