import os
import numpy as np
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data.distributed import DistributedSampler
import warnings
warnings.filterwarnings('ignore')


class DistributedTrainer:
    def __init__(
        self,
        model_class,
        model_kwargs,
        train_dataset,
        val_dataset=None,
        batch_size=16,
        lr=1e-4,
        weight_decay=1e-5,
        epochs=100,
        save_dir='./models',
        save_name='distributed_model.pth',
        local_rank=0,
        seed=42,
        use_amp=True,
    ):
        self.local_rank = local_rank
        self.rank = int(os.environ.get('RANK', 0))
        self.world_size = int(os.environ.get('WORLD_SIZE', 1))
        
        torch.manual_seed(seed + self.rank)
        np.random.seed(seed + self.rank)
        
        self.train_sampler = DistributedSampler(
            train_dataset,
            num_replicas=self.world_size,
            rank=self.rank,
            shuffle=True,
        )
        
        self.val_sampler = None
        if val_dataset is not None:
            self.val_sampler = DistributedSampler(
                val_dataset,
                num_replicas=self.world_size,
                rank=self.rank,
                shuffle=False,
            )
        
        from torch.utils.data import DataLoader
        self.train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            sampler=self.train_sampler,
            num_workers=4,
            pin_memory=True,
        )
        
        self.val_loader = None
        if val_dataset is not None:
            self.val_loader = DataLoader(
                val_dataset,
                batch_size=batch_size,
                sampler=self.val_sampler,
                num_workers=4,
                pin_memory=True,
            )
        
        self.device = torch.device(f'cuda:{local_rank}' if torch.cuda.is_available() else 'cpu')
        
        self.model = model_class(**model_kwargs)
        if hasattr(self.model, 'model'):
            self.model = self.model.model
        self.model = self.model.to(self.device)
        self.model = DDP(self.model, device_ids=[local_rank], output_device=local_rank)
        
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=lr,
            weight_decay=weight_decay,
        )
        
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=epochs,
        )
        
        self.loss_fn = torch.nn.CrossEntropyLoss()
        
        self.use_amp = use_amp
        self.scaler = torch.cuda.amp.GradScaler(enabled=use_amp)
        
        self.epochs = epochs
        self.save_dir = save_dir
        self.save_name = save_name
        self.best_metric = 0.0
        self.train_losses = []
        self.val_metrics = []
        
    def _get_data_from_batch(self, batch):
        if 'hsi' in batch and 'lidar' in batch:
            hsi = batch['hsi'].to(self.device)
            lidar = batch['lidar'].to(self.device)
            labels = batch['label'].to(self.device).long()
            if labels.ndim > 1:
                labels = labels.squeeze(1)
            return (hsi, lidar), labels
        else:
            images = batch['image'].to(self.device)
            labels = batch['label'].to(self.device).long()
            if labels.ndim > 1:
                labels = labels.squeeze(1)
            return (images,), labels
    
    def train_epoch(self, epoch):
        from tqdm import tqdm
        
        self.model.train()
        self.train_sampler.set_epoch(epoch)
        
        epoch_loss = 0.0
        correct = 0
        total = 0
        
        pbar = tqdm(self.train_loader, desc=f'Epoch {epoch+1} (Rank {self.rank})', disable=self.rank != 0)
        
        for batch in pbar:
            inputs, labels = self._get_data_from_batch(batch)
            
            self.optimizer.zero_grad()
            
            with torch.cuda.amp.autocast(enabled=self.use_amp):
                outputs = self.model(*inputs)
                loss = self.loss_fn(outputs, labels)
            
            self.scaler.scale(loss).backward()
            self.scaler.step(self.optimizer)
            self.scaler.update()
            
            epoch_loss += loss.item()
            
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
            if self.rank == 0:
                pbar.set_postfix(loss=loss.item())
        
        epoch_loss /= len(self.train_loader)
        accuracy = correct / total if total > 0 else 0
        
        loss_tensor = torch.tensor(epoch_loss, device=self.device)
        acc_tensor = torch.tensor(accuracy, device=self.device)
        
        dist.all_reduce(loss_tensor, op=dist.ReduceOp.SUM)
        dist.all_reduce(acc_tensor, op=dist.ReduceOp.SUM)
        
        avg_loss = loss_tensor.item() / self.world_size
        avg_acc = acc_tensor.item() / self.world_size
        
        return avg_loss, avg_acc
    
    def validate(self):
        if self.val_loader is None:
            return 0.0
        
        self.model.eval()
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch in self.val_loader:
                inputs, labels = self._get_data_from_batch(batch)
                
                with torch.cuda.amp.autocast(enabled=self.use_amp):
                    outputs = self.model(*inputs)
                
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
        
        accuracy = correct / total if total > 0 else 0
        acc_tensor = torch.tensor(accuracy, device=self.device)
        dist.all_reduce(acc_tensor, op=dist.ReduceOp.SUM)
        avg_acc = acc_tensor.item() / self.world_size
        
        return avg_acc
    
    def train(self, verbose=True):
        if self.rank == 0:
            os.makedirs(self.save_dir, exist_ok=True)
            save_path = os.path.join(self.save_dir, self.save_name)
            print(f"Starting distributed training on {self.world_size} GPUs...")
        
        for epoch in range(self.epochs):
            train_loss, train_acc = self.train_epoch(epoch)
            val_acc = self.validate()
            
            if self.rank == 0:
                self.train_losses.append(train_loss)
                self.val_metrics.append(val_acc)
                
                if verbose and (epoch + 1) % 5 == 0:
                    print(f"Epoch {epoch+1}/{self.epochs}, Train Loss: {train_loss:.4f}, "
                          f"Train Acc: {train_acc:.4f}, Val Acc: {val_acc:.4f}")
                
                if val_acc > self.best_metric:
                    self.best_metric = val_acc
                    torch.save({
                        'model_state_dict': self.model.module.state_dict(),
                        'optimizer_state_dict': self.optimizer.state_dict(),
                        'best_metric': self.best_metric,
                    }, save_path)
                    if verbose:
                        print(f"Saved best model with accuracy: {val_acc:.4f}")
            
            self.scheduler.step()
        
        if self.rank == 0:
            print(f"Training completed. Best validation accuracy: {self.best_metric:.4f}")
        
        return self.train_losses, self.val_metrics


def setup_distributed(rank, world_size):
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '12355'
    os.environ['RANK'] = str(rank)
    os.environ['WORLD_SIZE'] = str(world_size)
    dist.init_process_group(backend='nccl', rank=rank, world_size=world_size)
    torch.cuda.set_device(rank)


def cleanup_distributed():
    dist.destroy_process_group()


class ONNXExporter:
    def __init__(self, model, device=None):
        self.model = model
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        if hasattr(self.model, 'model'):
            self.model = self.model.model
        
        self.model = self.model.to(self.device)
        self.model.eval()
        
    def export(
        self,
        input_shape,
        output_path='model.onnx',
        opset_version=17,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes=None,
        verbose=False,
    ):
        if dynamic_axes is None:
            dynamic_axes = {
                'input': {0: 'batch_size'},
                'output': {0: 'batch_size'},
            }
        
        dummy_input = torch.randn(input_shape, device=self.device)
        
        torch.onnx.export(
            self.model,
            dummy_input,
            output_path,
            opset_version=opset_version,
            do_constant_folding=do_constant_folding,
            input_names=input_names,
            output_names=output_names,
            dynamic_axes=dynamic_axes,
            verbose=verbose,
        )
        
        if verbose:
            print(f"Model exported to {output_path}")
            print(f"Input shape: {input_shape}")
        
        return output_path
    
    def export_multimodal(
        self,
        hsi_shape,
        lidar_shape,
        output_path='multimodal_model.onnx',
        opset_version=17,
        do_constant_folding=True,
        verbose=False,
    ):
        hsi_dummy = torch.randn(hsi_shape, device=self.device)
        lidar_dummy = torch.randn(lidar_shape, device=self.device)
        
        torch.onnx.export(
            self.model,
            (hsi_dummy, lidar_dummy),
            output_path,
            opset_version=opset_version,
            do_constant_folding=do_constant_folding,
            input_names=['hsi', 'lidar'],
            output_names=['output'],
            dynamic_axes={
                'hsi': {0: 'batch_size'},
                'lidar': {0: 'batch_size'},
                'output': {0: 'batch_size'},
            },
            verbose=verbose,
        )
        
        if verbose:
            print(f"Multi-modal model exported to {output_path}")
            print(f"HSI shape: {hsi_shape}, LiDAR shape: {lidar_shape}")
        
        return output_path


class ONNXInference:
    def __init__(self, model_path, providers=None):
        import onnxruntime as ort
        
        if providers is None:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        
        self.session = ort.InferenceSession(model_path, providers=providers)
        self.input_names = [input.name for input in self.session.get_inputs()]
        self.output_names = [output.name for output in self.session.get_outputs()]
        
        print(f"Loaded ONNX model from {model_path}")
        print(f"Input names: {self.input_names}")
        print(f"Output names: {self.output_names}")
        print(f"Available providers: {self.session.get_providers()}")
    
    def predict(self, inputs):
        if isinstance(inputs, np.ndarray):
            inputs = {self.input_names[0]: inputs.astype(np.float32)}
        elif isinstance(inputs, dict):
            inputs = {k: v.astype(np.float32) for k, v in inputs.items()}
        
        outputs = self.session.run(self.output_names, inputs)
        logits = outputs[0]
        predictions = np.argmax(logits, axis=1)
        probabilities = self._softmax(logits)
        
        return predictions, probabilities
    
    def predict_batch(self, inputs, batch_size=32):
        if isinstance(inputs, np.ndarray):
            predictions = []
            probabilities = []
            
            for i in range(0, len(inputs), batch_size):
                batch = inputs[i:i+batch_size]
                preds, probs = self.predict(batch)
                predictions.extend(preds)
                probabilities.extend(probs)
            
            return np.array(predictions), np.array(probabilities)
        else:
            return self.predict(inputs)
    
    def _softmax(self, x):
        exp_x = np.exp(x - np.max(x, axis=1, keepdims=True))
        return exp_x / np.sum(exp_x, axis=1, keepdims=True)


def run_distributed_training(
    train_fn,
    model_class,
    model_kwargs,
    train_dataset,
    val_dataset=None,
    batch_size=16,
    lr=1e-4,
    epochs=100,
    world_size=None,
):
    if world_size is None:
        world_size = torch.cuda.device_count()
    
    print(f"Starting distributed training with {world_size} GPUs...")
    
    torch.multiprocessing.spawn(
        train_fn,
        args=(world_size, model_class, model_kwargs, train_dataset, val_dataset, batch_size, lr, epochs),
        nprocs=world_size,
        join=True,
    )


def _train_worker(rank, world_size, model_class, model_kwargs, train_dataset, val_dataset, batch_size, lr, epochs):
    setup_distributed(rank, world_size)
    
    trainer = DistributedTrainer(
        model_class=model_class,
        model_kwargs=model_kwargs,
        train_dataset=train_dataset,
        val_dataset=val_dataset,
        batch_size=batch_size,
        lr=lr,
        epochs=epochs,
        local_rank=rank,
    )
    
    trainer.train()
    
    cleanup_distributed()
