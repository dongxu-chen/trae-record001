"""
配置文件 - 定义搜索空间和训练超参数
"""

class SearchConfig:
    """搜索配置"""
    # 搜索空间定义
    KERNEL_SIZES = [3, 5, 7]  # 卷积核大小
    CHANNEL_MULTIPLIERS = [0.5, 1.0, 1.5, 2.0]  # 通道扩展比例
    
    # 网络结构配置
    NUM_CELLS = 4  # 搜索阶段的cell数量
    NUM_NODES_PER_CELL = 4  # 每个cell中的节点数
    INIT_CHANNELS = 16  # 初始通道数
    
    # 搜索训练配置
    SEARCH_EPOCHS = 50
    BATCH_SIZE = 128  # 提升batch size降低内存占用
    LEARNING_RATE = 0.025
    ARCH_LEARNING_RATE = 3e-4
    WEIGHT_DECAY = 3e-4
    ARCH_WEIGHT_DECAY = 1e-3
    MOMENTUM = 0.9
    GRAD_CLIP = 5.0
    
    # DropPath正则化 - 强制探索多样化架构
    DROP_PATH_PROB = 0.2  # 随机失活概率，越高探索越多
    
    # 多目标优化配置
    USE_MULTI_OBJECTIVE = True  # 是否启用多目标优化
    MULTI_OBJECTIVE_WEIGHTS = {
        'accuracy': 1.0,
        'flops_gflops': 0.3,
        'params_million': 0.2,
        'latency_ms': 0.25,
    }
    
    # 权重继承配置
    USE_WEIGHT_INHERITANCE = True  # 是否启用权重继承
    INHERITANCE_INTERVAL = 5  # 继承间隔（epoch）
    INHERITANCE_CHANGE_THRESHOLD = 0.3  # 架构变化阈值
    
    # 知识蒸馏配置
    USE_DISTILLATION = True  # 是否启用知识蒸馏
    DISTILLATION_TEMPERATURE = 4.0  # 蒸馏温度
    DISTILLATION_ALPHA = 0.7  # 软标签权重
    
    # 数据配置
    IMAGE_SIZE = 32
    NUM_CLASSES = 10
    DATA_PATH = "./data"
    
    # 损失函数温度系数 (用于softmax松弛)
    TEMPERATURE = 1.0
    
    # 架构导出阈值
    SKIP_THRESHOLD = 0.1  # 跳层连接的权重阈值


class TrainConfig:
    """最终模型训练配置"""
    NUM_CELLS = 20
    INIT_CHANNELS = 36
    BATCH_SIZE = 128  # 提升batch size
    LEARNING_RATE = 0.025
    MOMENTUM = 0.9
    WEIGHT_DECAY = 3e-4
    EPOCHS = 600
    GRAD_CLIP = 5.0
    DROPOUT_RATE = 0.2
    AUXILIARY = True
    AUXILIARY_WEIGHT = 0.4
    CUTOUT = True
    CUTOUT_LENGTH = 16
