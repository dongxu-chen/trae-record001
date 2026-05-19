"""
架构搜索算法 - 实现DARTS风格的双层优化
同时优化网络权重和架构参数
"""

import torch
import torch.nn as nn
import numpy as np
from copy import deepcopy


class Architect:
    """
    架构优化器 - 实现双层优化
    使用一阶近似（默认）或二阶近似来更新架构参数
    """
    def __init__(self, model, config, device):
        """
        Args:
            model: 搜索网络模型
            config: 搜索配置
            device: 计算设备
        """
        self.model = model
        self.config = config
        self.device = device
        
        # 架构参数优化器
        self.optimizer = torch.optim.Adam(
            model.arch_parameters(),
            lr=config.ARCH_LEARNING_RATE,
            betas=(0.5, 0.999),
            weight_decay=config.ARCH_WEIGHT_DECAY
        )
        
        self.criterion = nn.CrossEntropyLoss().to(device)
    
    def step(self, input_train, target_train, input_valid, target_valid, 
             eta, network_optimizer, unrolled=False):
        """
        执行一步架构参数更新
        Args:
            input_train: 训练批次输入
            target_train: 训练批次标签
            input_valid: 验证批次输入
            target_valid: 验证批次标签
            eta: 权重学习率
            network_optimizer: 权重优化器
            unrolled: 是否使用二阶近似
        """
        self.optimizer.zero_grad()
        
        if unrolled:
            # 二阶近似 - 更准确但计算量更大
            loss = self._backward_step_unrolled(
                input_train, target_train, input_valid, target_valid, 
                eta, network_optimizer
            )
        else:
            # 一阶近似 - 速度快
            loss = self._backward_step(input_valid, target_valid)
        
        nn.utils.clip_grad_norm_(self.model.arch_parameters(), self.config.GRAD_CLIP)
        self.optimizer.step()
        
        return loss.item()
    
    def _backward_step(self, input_valid, target_valid):
        """一阶近似 - 直接在验证集上计算梯度"""
        loss = self.model.loss(input_valid, target_valid, self.config.TEMPERATURE)
        loss.backward()
        return loss
    
    def _backward_step_unrolled(self, input_train, target_train, input_valid, target_valid,
                                eta, network_optimizer):
        """
        二阶近似 - 考虑权重更新对架构梯度的影响
        先在训练集上更新权重（虚拟步骤），然后在验证集上计算架构梯度
        """
        # 保存当前权重
        model_weights = deepcopy(self.model.state_dict())
        optim_state = deepcopy(network_optimizer.state_dict())
        
        # 在训练集上执行一步权重更新（虚拟步骤）
        network_optimizer.zero_grad()
        train_loss = self.model.loss(input_train, target_train, self.config.TEMPERATURE)
        train_loss.backward()
        nn.utils.clip_grad_norm_(self.model.weight_parameters(), self.config.GRAD_CLIP)
        network_optimizer.step()
        
        # 在验证集上计算架构梯度
        valid_loss = self.model.loss(input_valid, target_valid, self.config.TEMPERATURE)
        valid_loss.backward()
        
        # 恢复原始权重
        self.model.load_state_dict(model_weights)
        network_optimizer.load_state_dict(optim_state)
        
        return valid_loss


class AverageMeter:
    """平均值计算器 - 用于跟踪训练指标"""
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.avg = 0
        self.sum = 0
        self.count = 0
    
    def update(self, val, n=1):
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def accuracy(output, target, topk=(1,)):
    """计算top-k准确率"""
    maxk = max(topk)
    batch_size = target.size(0)
    
    _, pred = output.topk(maxk, 1, True, True)
    pred = pred.t()
    correct = pred.eq(target.view(1, -1).expand_as(pred))
    
    res = []
    for k in topk:
        correct_k = correct[:k].reshape(-1).float().sum(0)
        res.append(correct_k.mul_(100.0 / batch_size))
    return res


def train_one_epoch(model, architect, train_loader, valid_loader, optimizer, 
                    config, device, epoch, unrolled=False):
    """
    训练一个epoch
    Args:
        model: 搜索网络
        architect: 架构优化器
        train_loader: 训练数据加载器
        valid_loader: 验证数据加载器
        optimizer: 权重优化器
        config: 搜索配置
        device: 计算设备
        epoch: 当前epoch
        unrolled: 是否使用二阶近似
    Returns:
        train_loss, train_acc, valid_loss, valid_acc
    """
    model.train()
    
    train_losses = AverageMeter()
    train_top1 = AverageMeter()
    valid_losses = AverageMeter()
    valid_top1 = AverageMeter()
    
    lr = optimizer.param_groups[0]['lr']
    
    train_iter = iter(train_loader)
    valid_iter = iter(valid_loader)
    
    num_batches = min(len(train_loader), len(valid_loader))
    
    for step in range(num_batches):
        try:
            input_train, target_train = next(train_iter)
            input_valid, target_valid = next(valid_iter)
        except StopIteration:
            break
        
        input_train = input_train.to(device)
        target_train = target_train.to(device)
        input_valid = input_valid.to(device)
        target_valid = target_valid.to(device)
        
        # 步骤1: 更新架构参数
        architect.step(
            input_train, target_train, input_valid, target_valid,
            lr, optimizer, unrolled=unrolled
        )
        
        # 步骤2: 更新网络权重
        optimizer.zero_grad()
        logits = model(input_train, config.TEMPERATURE)
        loss = model._criterion(logits, target_train)
        loss.backward()
        nn.utils.clip_grad_norm_(model.weight_parameters(), config.GRAD_CLIP)
        optimizer.step()
        
        # 记录指标
        prec1 = accuracy(logits, target_train, topk=(1,))[0]
        train_losses.update(loss.item(), input_train.size(0))
        train_top1.update(prec1.item(), input_train.size(0))
        
        # 在验证集上评估
        with torch.no_grad():
            valid_logits = model(input_valid, config.TEMPERATURE)
            valid_loss = model._criterion(valid_logits, target_valid)
            valid_prec1 = accuracy(valid_logits, target_valid, topk=(1,))[0]
            valid_losses.update(valid_loss.item(), input_valid.size(0))
            valid_top1.update(valid_prec1.item(), input_valid.size(0))
        
        if step % 50 == 0:
            print(f"Epoch [{epoch}] Step [{step}/{num_batches}] "
                  f"Train Loss: {train_losses.avg:.4f} "
                  f"Train Acc: {train_top1.avg:.2f}% "
                  f"Valid Loss: {valid_losses.avg:.4f} "
                  f"Valid Acc: {valid_top1.avg:.2f}%")
    
    return train_losses.avg, train_top1.avg, valid_losses.avg, valid_top1.avg


def search_architecture(model, train_loader, valid_loader, test_loader, config, device, 
                        unrolled=False, save_path='./checkpoints'):
    """
    执行完整的架构搜索
    Args:
        model: 搜索网络
        train_loader: 训练数据加载器
        valid_loader: 验证数据加载器
        test_loader: 测试数据加载器
        config: 搜索配置
        device: 计算设备
        unrolled: 是否使用二阶近似
        save_path: 检查点保存路径
    Returns:
        训练好的模型
    """
    import os
    os.makedirs(save_path, exist_ok=True)
    
    # 权重优化器
    optimizer = torch.optim.SGD(
        model.weight_parameters(),
        config.LEARNING_RATE,
        momentum=config.MOMENTUM,
        weight_decay=config.WEIGHT_DECAY
    )
    
    # 学习率调度器
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, float(config.SEARCH_EPOCHS)
    )
    
    # 架构优化器
    architect = Architect(model, config, device)
    
    best_valid_acc = 0.0
    
    for epoch in range(config.SEARCH_EPOCHS):
        print(f"\n{'='*50}")
        print(f"Search Epoch {epoch + 1}/{config.SEARCH_EPOCHS}")
        print(f"Learning Rate: {optimizer.param_groups[0]['lr']:.6f}")
        print(f"{'='*50}")
        
        # 训练一个epoch
        train_loss, train_acc, valid_loss, valid_acc = train_one_epoch(
            model, architect, train_loader, valid_loader, optimizer,
            config, device, epoch + 1, unrolled
        )
        
        # 更新学习率
        scheduler.step()
        
        # 在测试集上评估
        model.eval()
        test_losses = AverageMeter()
        test_top1 = AverageMeter()
        
        with torch.no_grad():
            for input_test, target_test in test_loader:
                input_test = input_test.to(device)
                target_test = target_test.to(device)
                logits = model(input_test, config.TEMPERATURE)
                loss = model._criterion(logits, target_test)
                prec1 = accuracy(logits, target_test, topk=(1,))[0]
                test_losses.update(loss.item(), input_test.size(0))
                test_top1.update(prec1.item(), input_test.size(0))
        
        print(f"\nEpoch {epoch + 1} Summary:")
        print(f"Train - Loss: {train_loss:.4f}, Acc: {train_acc:.2f}%")
        print(f"Valid - Loss: {valid_loss:.4f}, Acc: {valid_acc:.2f}%")
        print(f"Test  - Loss: {test_losses.avg:.4f}, Acc: {test_top1.avg:.2f}%")
        
        # 保存最佳模型
        if valid_acc > best_valid_acc:
            best_valid_acc = valid_acc
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'alphas_normal': model.alphas_normal.detach().cpu(),
                'alphas_reduce': model.alphas_reduce.detach().cpu(),
                'valid_acc': valid_acc,
                'test_acc': test_top1.avg,
            }, f"{save_path}/best_search_model.pt")
            print(f"Saved best model with valid acc: {best_valid_acc:.2f}%")
        
        # 定期保存检查点
        if (epoch + 1) % 10 == 0:
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'alphas_normal': model.alphas_normal.detach().cpu(),
                'alphas_reduce': model.alphas_reduce.detach().cpu(),
            }, f"{save_path}/search_checkpoint_epoch{epoch + 1}.pt")
    
    print(f"\n搜索完成! 最佳验证准确率: {best_valid_acc:.2f}%")
    return model
