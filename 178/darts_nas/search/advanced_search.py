"""
高级架构搜索算法
集成多目标优化、权重继承和知识蒸馏
"""

import torch
import torch.nn as nn
import numpy as np
import os
from copy import deepcopy

from darts_nas.search.architect import (
    Architect, AverageMeter, accuracy, train_one_epoch
)
from darts_nas.core.multi_objective import (
    compute_objectives, ParetoOptimizer, MultiObjectiveLoss,
    get_default_objectives_config
)
from darts_nas.core.weight_inheritance import WeightInheritanceManager
from darts_nas.core.distillation import (
    DistillationTrainer, create_default_teacher
)
from darts_nas.models.architecture import derive_architecture


def search_architecture_advanced(model, train_loader, valid_loader, test_loader, 
                                 config, device, unrolled=False, save_path='./checkpoints',
                                 use_multi_objective=True, use_weight_inheritance=True,
                                 use_distillation=True):
    """
    执行高级架构搜索
    集成多目标优化、权重继承和知识蒸馏
    
    Args:
        model: 搜索网络
        train_loader: 训练数据加载器
        valid_loader: 验证数据加载器
        test_loader: 测试数据加载器
        config: 搜索配置
        device: 计算设备
        unrolled: 是否使用二阶近似
        save_path: 检查点保存路径
        use_multi_objective: 是否启用多目标优化
        use_weight_inheritance: 是否启用权重继承
        use_distillation: 是否启用知识蒸馏
    
    Returns:
        训练好的模型，搜索历史
    """
    os.makedirs(save_path, exist_ok=True)
    
    print("\n" + "="*60)
    print("高级架构搜索配置")
    print("="*60)
    print(f"多目标优化: {'启用' if use_multi_objective else '禁用'}")
    print(f"权重继承: {'启用' if use_weight_inheritance else '禁用'}")
    print(f"知识蒸馏: {'启用' if use_distillation else '禁用'}")
    print(f"二阶近似: {'启用' if unrolled else '禁用 (使用一阶近似)'}")
    print("="*60 + "\n")
    
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
    
    # 初始化多目标优化器
    pareto_optimizer = None
    multi_objective_loss = None
    if use_multi_objective:
        obj_config = get_default_objectives_config()
        # 更新权重
        for key, weight in config.MULTI_OBJECTIVE_WEIGHTS.items():
            if key in obj_config:
                obj_config[key]['weight'] = weight
        
        pareto_optimizer = ParetoOptimizer(obj_config)
        multi_objective_loss = MultiObjectiveLoss(obj_config, device)
        print("✓ 多目标优化器已初始化")
    
    # 初始化权重继承管理器
    weight_inheritance_manager = None
    if use_weight_inheritance:
        weight_inheritance_manager = WeightInheritanceManager(
            save_dir=f"{save_path}/weight_inheritance",
            inheritance_interval=config.INHERITANCE_INTERVAL,
            architecture_change_threshold=config.INHERITANCE_CHANGE_THRESHOLD
        )
        print("✓ 权重继承管理器已初始化")
    
    # 初始化知识蒸馏训练器
    distillation_trainer = None
    if use_distillation:
        teacher = create_default_teacher(num_classes=config.NUM_CLASSES, device=device)
        distillation_trainer = DistillationTrainer(
            teacher=teacher,
            temperature=config.DISTILLATION_TEMPERATURE,
            alpha=config.DISTILLATION_ALPHA,
            device=device
        )
        print("✓ 知识蒸馏训练器已初始化")
    
    # 搜索历史记录
    search_history = []
    best_solution = None
    best_score = float('-inf')
    
    for epoch in range(config.SEARCH_EPOCHS):
        print(f"\n{'='*60}")
        print(f"Search Epoch {epoch + 1}/{config.SEARCH_EPOCHS}")
        print(f"Learning Rate: {optimizer.param_groups[0]['lr']:.6f}")
        print(f"{'='*60}")
        
        # 检查是否需要权重继承
        if use_weight_inheritance and weight_inheritance_manager is not None:
            current_arch = derive_architecture(
                model.alphas_normal.detach().cpu(),
                model.alphas_reduce.detach().cpu(),
                num_nodes=config.NUM_NODES_PER_CELL
            )
            
            if weight_inheritance_manager.should_inherit(current_arch, epoch):
                print("\n触发权重继承...")
                model = weight_inheritance_manager.inherit_from_best(model)
                # 重新初始化优化器（因为模型参数可能变化）
                optimizer = torch.optim.SGD(
                    model.weight_parameters(),
                    optimizer.param_groups[0]['lr'],
                    momentum=config.MOMENTUM,
                    weight_decay=config.WEIGHT_DECAY
                )
        
        # 训练一个epoch（支持知识蒸馏）
        if use_distillation and distillation_trainer is not None:
            train_loss, train_acc, valid_loss, valid_acc = train_one_epoch_with_distillation(
                model, architect, distillation_trainer, train_loader, valid_loader,
                optimizer, config, device, epoch + 1, unrolled
            )
        else:
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
        
        test_acc = test_top1.avg
        
        # 计算多目标指标
        objectives = {}
        if use_multi_objective:
            print("\n计算多目标指标...")
            objectives = compute_objectives(model, input_size=(1, 3, 32, 32), device=device)
            objectives['accuracy'] = valid_acc
            objectives['test_accuracy'] = test_acc
            
            # 更新归一化因子
            if multi_objective_loss is not None:
                multi_objective_loss.update_normalization(objectives)
            
            # 计算综合得分
            score = pareto_optimizer.compute_scalarized_score(objectives)
            
            print(f"多目标指标:")
            print(f"  准确率: {objectives['accuracy']:.2f}%")
            print(f"  FLOPs: {objectives['flops_gflops']:.2f} GFLOPs")
            print(f"  参数量: {objectives['params_million']:.2f} M")
            print(f"  延迟: {objectives['latency_ms']:.2f} ms")
            print(f"  综合得分: {score:.4f}")
        else:
            objectives = {'accuracy': valid_acc, 'test_accuracy': test_acc}
            score = valid_acc
        
        # 记录历史
        epoch_record = {
            'epoch': epoch + 1,
            'train_loss': train_loss,
            'train_acc': train_acc,
            'valid_loss': valid_loss,
            'valid_acc': valid_acc,
            'test_acc': test_acc,
            'objectives': objectives,
            'score': score,
        }
        search_history.append(epoch_record)
        
        # 保存检查点用于权重继承
        if use_weight_inheritance and weight_inheritance_manager is not None:
            current_arch = derive_architecture(
                model.alphas_normal.detach().cpu(),
                model.alphas_reduce.detach().cpu(),
                num_nodes=config.NUM_NODES_PER_CELL
            )
            weight_inheritance_manager.save_checkpoint(
                model, current_arch, epoch + 1, valid_acc, objectives
            )
        
        # 更新最佳解
        if score > best_score:
            best_score = score
            best_solution = epoch_record
            
            # 保存最佳模型
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'alphas_normal': model.alphas_normal.detach().cpu(),
                'alphas_reduce': model.alphas_reduce.detach().cpu(),
                'valid_acc': valid_acc,
                'test_acc': test_acc,
                'objectives': objectives,
                'score': score,
            }, f"{save_path}/best_search_model.pt")
            print(f"\n✓ 新的最佳模型已保存 (得分: {best_score:.4f})")
        
        # 定期保存检查点
        if (epoch + 1) % 10 == 0:
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'alphas_normal': model.alphas_normal.detach().cpu(),
                'alphas_reduce': model.alphas_reduce.detach().cpu(),
                'objectives': objectives,
                'score': score,
            }, f"{save_path}/search_checkpoint_epoch{epoch + 1}.pt")
            
            # 保存搜索历史
            torch.save(search_history, f"{save_path}/search_history.pt")
        
        # 打印总结
        print(f"\nEpoch {epoch + 1} Summary:")
        print(f"Train - Loss: {train_loss:.4f}, Acc: {train_acc:.2f}%")
        print(f"Valid - Loss: {valid_loss:.4f}, Acc: {valid_acc:.2f}%")
        print(f"Test  - Acc: {test_acc:.2f}%")
        print(f"Score - {score:.4f}  (Best: {best_score:.4f})")
    
    # 搜索完成，进行Pareto分析
    if use_multi_objective and len(search_history) > 1:
        print("\n" + "="*60)
        print("Pareto最优分析")
        print("="*60)
        
        solutions = [record['objectives'] for record in search_history]
        ranks = pareto_optimizer.pareto_rank(solutions)
        
        pareto_front = [i for i, r in enumerate(ranks) if r == 0]
        print(f"Pareto最优解数量: {len(pareto_front)}")
        print(f"Pareto最优解 epoch: {[search_history[i]['epoch'] for i in pareto_front]}")
        
        # 打印每个Pareto最优解的指标
        for i in pareto_front:
            obj = solutions[i]
            print(f"\nEpoch {search_history[i]['epoch']}:")
            print(f"  准确率: {obj['accuracy']:.2f}%")
            print(f"  FLOPs: {obj['flops_gflops']:.2f} GFLOPs")
            print(f"  参数量: {obj['params_million']:.2f} M")
            print(f"  延迟: {obj['latency_ms']:.2f} ms")
    
    print(f"\n{'='*60}")
    print("搜索完成!")
    print(f"最佳综合得分: {best_score:.4f}")
    if best_solution:
        print(f"最佳验证准确率: {best_solution['valid_acc']:.2f}%")
        print(f"最佳测试准确率: {best_solution['test_acc']:.2f}%")
        if 'flops_gflops' in best_solution['objectives']:
            print(f"最佳FLOPs: {best_solution['objectives']['flops_gflops']:.2f} GFLOPs")
            print(f"最佳参数量: {best_solution['objectives']['params_million']:.2f} M")
    print("="*60)
    
    # 保存完整的搜索结果
    final_results = {
        'best_solution': best_solution,
        'search_history': search_history,
        'model_state_dict': model.state_dict(),
        'alphas_normal': model.alphas_normal.detach().cpu(),
        'alphas_reduce': model.alphas_reduce.detach().cpu(),
    }
    torch.save(final_results, f"{save_path}/final_search_results.pt")
    
    return model, search_history


def train_one_epoch_with_distillation(model, architect, distillation_trainer, 
                                      train_loader, valid_loader, optimizer, 
                                      config, device, epoch, unrolled=False):
    """
    使用知识蒸馏训练一个epoch
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
        
        # 步骤2: 使用蒸馏损失更新网络权重
        distillation_metrics = distillation_trainer.train_step(
            model, input_train, target_train, optimizer, config.GRAD_CLIP
        )
        
        # 记录指标
        train_losses.update(distillation_metrics['loss'], input_train.size(0))
        train_top1.update(distillation_metrics['accuracy'], input_train.size(0))
        
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
