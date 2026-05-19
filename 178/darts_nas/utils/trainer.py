"""
最终模型训练器 - 用于训练搜索到的最优架构
"""

import torch
import torch.nn as nn
import time
import os
import sys
import importlib.util


class AverageMeter:
    """平均值计算器"""
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


def load_model_from_code(code_path, model_class_name='SearchedNetwork'):
    """从生成的代码文件中加载模型类"""
    spec = importlib.util.spec_from_file_location("searched_model", code_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["searched_model"] = module
    spec.loader.exec_module(module)
    return getattr(module, model_class_name)


def train_epoch(model, train_loader, criterion, optimizer, device, epoch, 
                auxiliary=False, auxiliary_weight=0.4, grad_clip=5.0):
    """训练一个epoch"""
    model.train()
    
    batch_time = AverageMeter()
    data_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()
    top5 = AverageMeter()
    
    end = time.time()
    
    for step, (input, target) in enumerate(train_loader):
        data_time.update(time.time() - end)
        
        input = input.to(device)
        target = target.to(device)
        
        # 前向传播
        if auxiliary:
            logits, aux_logits = model(input)
            loss = criterion(logits, target) + auxiliary_weight * criterion(aux_logits, target)
        else:
            logits = model(input)
            loss = criterion(logits, target)
        
        # 计算准确率
        prec1, prec5 = accuracy(logits, target, topk=(1, 5))
        losses.update(loss.item(), input.size(0))
        top1.update(prec1.item(), input.size(0))
        top5.update(prec5.item(), input.size(0))
        
        # 反向传播和优化
        optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        optimizer.step()
        
        batch_time.update(time.time() - end)
        end = time.time()
        
        if step % 50 == 0:
            print(f"Epoch: [{epoch}][{step}/{len(train_loader)}] "
                  f"Time {batch_time.avg:.3f} "
                  f"Data {data_time.avg:.3f} "
                  f"Loss {losses.avg:.4f} "
                  f"Prec@1 {top1.avg:.3f} "
                  f"Prec@5 {top5.avg:.3f}")
    
    return losses.avg, top1.avg, top5.avg


def validate(model, valid_loader, criterion, device, auxiliary=False):
    """验证模型"""
    model.eval()
    
    batch_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()
    top5 = AverageMeter()
    
    end = time.time()
    
    with torch.no_grad():
        for step, (input, target) in enumerate(valid_loader):
            input = input.to(device)
            target = target.to(device)
            
            if auxiliary:
                logits, _ = model(input)
            else:
                logits = model(input)
            
            loss = criterion(logits, target)
            
            prec1, prec5 = accuracy(logits, target, topk=(1, 5))
            losses.update(loss.item(), input.size(0))
            top1.update(prec1.item(), input.size(0))
            top5.update(prec5.item(), input.size(0))
            
            batch_time.update(time.time() - end)
            end = time.time()
            
            if step % 50 == 0:
                print(f"Valid: [{step}/{len(valid_loader)}] "
                      f"Time {batch_time.avg:.3f} "
                      f"Loss {losses.avg:.4f} "
                      f"Prec@1 {top1.avg:.3f} "
                      f"Prec@5 {top5.avg:.3f}")
    
    print(f" * Prec@1 {top1.avg:.3f} Prec@5 {top5.avg:.3f}")
    return losses.avg, top1.avg, top5.avg


def train_final_model(model_code_path, train_loader, test_loader, config, device, 
                      save_path='./checkpoints/final_model'):
    """
    训练最终的搜索到的模型
    Args:
        model_code_path: 生成的模型代码路径
        train_loader: 训练数据加载器
        test_loader: 测试数据加载器
        config: 训练配置
        device: 计算设备
        save_path: 模型保存路径
    Returns:
        训练好的模型
    """
    os.makedirs(save_path, exist_ok=True)
    
    # 加载模型类
    SearchedNetwork = load_model_from_code(model_code_path)
    
    # 创建模型
    model = SearchedNetwork(
        C=config.INIT_CHANNELS,
        num_classes=config.NUM_CLASSES,
        layers=config.NUM_CELLS,
        auxiliary=config.AUXILIARY
    ).to(device)
    
    # 损失函数
    criterion = nn.CrossEntropyLoss().to(device)
    
    # 优化器
    optimizer = torch.optim.SGD(
        model.parameters(),
        config.LEARNING_RATE,
        momentum=config.MOMENTUM,
        weight_decay=config.WEIGHT_DECAY
    )
    
    # 学习率调度器
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, float(config.EPOCHS)
    )
    
    best_acc = 0.0
    
    for epoch in range(config.EPOCHS):
        print(f"\n{'='*60}")
        print(f"Final Train Epoch {epoch + 1}/{config.EPOCHS}")
        print(f"Learning Rate: {optimizer.param_groups[0]['lr']:.6f}")
        print(f"{'='*60}")
        
        # 训练
        train_loss, train_acc1, train_acc5 = train_epoch(
            model, train_loader, criterion, optimizer, device, epoch + 1,
            auxiliary=config.AUXILIARY,
            auxiliary_weight=config.AUXILIARY_WEIGHT,
            grad_clip=config.GRAD_CLIP
        )
        
        # 更新学习率
        scheduler.step()
        
        # 验证
        valid_loss, valid_acc1, valid_acc5 = validate(
            model, test_loader, criterion, device,
            auxiliary=config.AUXILIARY
        )
        
        print(f"\nEpoch {epoch + 1} Summary:")
        print(f"Train - Loss: {train_loss:.4f}, Acc@1: {train_acc1:.2f}%, Acc@5: {train_acc5:.2f}%")
        print(f"Test  - Loss: {valid_loss:.4f}, Acc@1: {valid_acc1:.2f}%, Acc@5: {valid_acc5:.2f}%")
        
        # 保存最佳模型
        if valid_acc1 > best_acc:
            best_acc = valid_acc1
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'best_acc': best_acc,
            }, f"{save_path}/best_model.pt")
            print(f"Saved best model with test acc: {best_acc:.2f}%")
        
        # 定期保存检查点
        if (epoch + 1) % 50 == 0:
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'acc': valid_acc1,
            }, f"{save_path}/checkpoint_epoch{epoch + 1}.pt")
    
    print(f"\n训练完成! 最佳测试准确率: {best_acc:.2f}%")
    return model
