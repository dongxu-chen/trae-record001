import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
from collections import deque
import math


@dataclass
class ActionRecognitionResult:
    action_name: str
    action_id: int
    confidence: float
    all_predictions: Dict[str, float]
    sequence_length: int


@dataclass
class PredefinedAction:
    name: str
    description: str
    category: str
    key_joints: List[int]
    template_sequence: Optional[np.ndarray] = None


class GraphConvolution(nn.Module):
    def __init__(self, in_features: int, out_features: int, bias: bool = True):
        super(GraphConvolution, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.weight = nn.Parameter(torch.FloatTensor(in_features, out_features))
        if bias:
            self.bias = nn.Parameter(torch.FloatTensor(out_features))
        else:
            self.register_parameter('bias', None)
        self.reset_parameters()
    
    def reset_parameters(self):
        stdv = 1. / math.sqrt(self.weight.size(1))
        self.weight.data.uniform_(-stdv, stdv)
        if self.bias is not None:
            self.bias.data.uniform_(-stdv, stdv)
    
    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        support = torch.matmul(x, self.weight)
        output = torch.matmul(adj, support)
        if self.bias is not None:
            output = output + self.bias
        return output


class ST_GCN_Block(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, 
                 kernel_size: Tuple[int, int] = (9, 3), stride: int = 1,
                 dropout: float = 0.5):
        super(ST_GCN_Block, self).__init__()
        
        t_kernel, s_kernel = kernel_size
        padding = ((t_kernel - 1) // 2, 0)
        
        self.s_gcn = GraphConvolution(in_channels, out_channels)
        self.t_cnn = nn.Conv2d(out_channels, out_channels, 
                               kernel_size=(t_kernel, 1), 
                               stride=(stride, 1), 
                               padding=padding)
        
        self.residual = nn.Identity()
        if in_channels != out_channels or stride != 1:
            self.residual = nn.Conv2d(in_channels, out_channels,
                                      kernel_size=1, stride=(stride, 1))
        
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        N, C, T, V = x.size()
        
        x_reshaped = x.permute(0, 2, 3, 1).contiguous().view(N * T, V, C)
        x_s = self.s_gcn(x_reshaped, adj)
        x_s = x_s.view(N, T, V, -1).permute(0, 3, 1, 2).contiguous()
        x_s = self.bn1(x_s)
        x_s = self.relu(x_s)
        
        x_t = self.t_cnn(x_s)
        x_t = self.bn2(x_t)
        
        res = self.residual(x)
        x = x_t + res
        x = self.relu(x)
        x = self.dropout(x)
        
        return x


class ActionRecognitionModel(nn.Module):
    def __init__(self, num_joints: int = 24, in_channels: int = 3,
                 num_classes: int = 10, hidden_dim: int = 64,
                 dropout: float = 0.5):
        super(ActionRecognitionModel, self).__init__()
        
        self.num_joints = num_joints
        self.in_channels = in_channels
        self.num_classes = num_classes
        
        self.register_buffer('adjacency', self._build_adjacency(num_joints))
        
        self.data_bn = nn.BatchNorm1d(in_channels * num_joints)
        
        self.st_gcn_layers = nn.ModuleList([
            ST_GCN_Block(in_channels, hidden_dim, dropout=dropout),
            ST_GCN_Block(hidden_dim, hidden_dim, dropout=dropout),
            ST_GCN_Block(hidden_dim, hidden_dim * 2, stride=2, dropout=dropout),
            ST_GCN_Block(hidden_dim * 2, hidden_dim * 2, dropout=dropout),
            ST_GCN_Block(hidden_dim * 2, hidden_dim * 4, stride=2, dropout=dropout),
            ST_GCN_Block(hidden_dim * 4, hidden_dim * 4, dropout=dropout),
        ])
        
        self.fc1 = nn.Linear(hidden_dim * 4, hidden_dim * 2)
        self.fc2 = nn.Linear(hidden_dim * 2, num_classes)
        self.dropout = nn.Dropout(dropout)
    
    def _build_adjacency(self, num_joints: int) -> torch.Tensor:
        SMPL_SKELETON = [
            (0, 1), (0, 2), (0, 3), (1, 4), (2, 5), (3, 6),
            (4, 7), (5, 8), (6, 9), (7, 10), (8, 11), (9, 12),
            (9, 13), (9, 14), (12, 15), (13, 16), (14, 17),
            (16, 18), (17, 19), (18, 20), (19, 21), (20, 22), (21, 23)
        ]
        
        adj = torch.zeros(num_joints, num_joints)
        for i, j in SMPL_SKELETON:
            if i < num_joints and j < num_joints:
                adj[i, j] = 1
                adj[j, i] = 1
        
        for i in range(num_joints):
            adj[i, i] = 1
        
        degree = torch.sum(adj, dim=1)
        degree_inv = torch.pow(degree, -0.5)
        degree_inv[torch.isinf(degree_inv)] = 0
        adj_norm = degree_inv.unsqueeze(1) * adj * degree_inv.unsqueeze(0)
        
        return adj_norm
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        N, C, T, V = x.size()
        
        x = x.permute(0, 3, 1, 2).contiguous().view(N, V * C, T)
        x = self.data_bn(x)
        x = x.view(N, V, C, T).permute(0, 2, 3, 1).contiguous()
        
        for layer in self.st_gcn_layers:
            x = layer(x, self.adjacency)
        
        x = F.avg_pool2d(x, x.size()[2:])
        x = x.view(x.size(0), -1)
        x = self.dropout(x)
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        
        return x


class LSTMActionRecognizer(nn.Module):
    def __init__(self, num_joints: int = 24, in_channels: int = 3,
                 num_classes: int = 10, hidden_size: int = 128,
                 num_layers: int = 2, dropout: float = 0.5):
        super(LSTMActionRecognizer, self).__init__()
        
        self.num_joints = num_joints
        self.in_channels = in_channels
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        input_size = num_joints * in_channels
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        self.fc1 = nn.Linear(hidden_size * 2, hidden_size)
        self.fc2 = nn.Linear(hidden_size, num_classes)
        self.dropout = nn.Dropout(dropout)
        self.relu = nn.ReLU()
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        N, C, T, V = x.size()
        
        x = x.permute(0, 2, 1, 3).contiguous().view(N, T, C * V)
        
        lstm_out, _ = self.lstm(x)
        
        last_out = lstm_out[:, -1, :]
        
        x = self.dropout(last_out)
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        
        return x


class PoseFeatureExtractor:
    def __init__(self, num_joints: int = 24):
        self.num_joints = num_joints
        
        self.SMPL_SKELETON = [
            (0, 1), (0, 2), (0, 3), (1, 4), (2, 5), (3, 6),
            (4, 7), (5, 8), (6, 9), (7, 10), (8, 11), (9, 12),
            (9, 13), (9, 14), (12, 15), (13, 16), (14, 17),
            (16, 18), (17, 19), (18, 20), (19, 21), (20, 22), (21, 23)
        ]
    
    def extract_features(self, pose_sequence: np.ndarray) -> np.ndarray:
        if pose_sequence.ndim == 4:
            pose_sequence = pose_sequence[0]
        
        T, V, C = pose_sequence.shape
        
        features = []
        
        for t in range(T):
            frame_features = []
            joints = pose_sequence[t]
            
            velocities = np.zeros((V, C))
            if t > 0:
                velocities = joints - pose_sequence[t-1]
            
            accelerations = np.zeros((V, C))
            if t > 1:
                accelerations = velocities - (pose_sequence[t-1] - pose_sequence[t-2])
            
            for parent, child in self.SMPL_SKELETON:
                if parent < V and child < V:
                    bone_vec = joints[child] - joints[parent]
                    bone_len = np.linalg.norm(bone_vec)
                    frame_features.extend(bone_vec)
                    frame_features.append(bone_len)
            
            frame_features.extend(joints.flatten())
            frame_features.extend(velocities.flatten())
            frame_features.extend(accelerations.flatten())
            
            features.append(frame_features)
        
        return np.array(features)


class ActionRecognizer:
    def __init__(self, num_joints: int = 24, 
                 action_names: Optional[List[str]] = None,
                 sequence_length: int = 60,
                 overlap: int = 30,
                 device: str = 'cpu',
                 use_pretrained: bool = False):
        self.num_joints = num_joints
        self.sequence_length = sequence_length
        self.overlap = overlap
        self.device = device
        
        if action_names is None:
            self.action_names = [
                '站立', '行走', '跑步', '坐下', '站起',
                '弯腰', '抬手', '踢腿', '跳跃', '挥手',
                '深蹲', '俯卧撑', '引体向上', '拉伸', '转身'
            ]
        else:
            self.action_names = action_names
        
        self.num_classes = len(self.action_names)
        
        self.model = LSTMActionRecognizer(
            num_joints=num_joints,
            num_classes=self.num_classes
        )
        self.model.to(device)
        self.model.eval()
        
        self.feature_extractor = PoseFeatureExtractor(num_joints)
        
        self.pose_buffers = {}
        self.result_history = {}
        
        self.predefined_actions = self._init_predefined_actions()
        
        if use_pretrained:
            self._load_pretrained_weights()
    
    def _init_predefined_actions(self) -> Dict[str, PredefinedAction]:
        actions = {
            '站立': PredefinedAction(
                name='站立',
                description='身体直立，双脚稳定站立',
                category='基础',
                key_joints=[0, 1, 2, 3, 9, 12, 15]
            ),
            '行走': PredefinedAction(
                name='行走',
                description='双腿交替向前移动',
                category='移动',
                key_joints=[1, 2, 4, 5, 7, 8, 10, 11]
            ),
            '跑步': PredefinedAction(
                name='跑步',
                description='快速奔跑动作',
                category='移动',
                key_joints=[1, 2, 4, 5, 7, 8, 10, 11, 16, 17]
            ),
            '深蹲': PredefinedAction(
                name='深蹲',
                description='膝盖弯曲，身体下沉',
                category='健身',
                key_joints=[0, 1, 2, 4, 5, 7, 8]
            ),
            '抬手': PredefinedAction(
                name='抬手',
                description='手臂向上抬起',
                category='上肢',
                key_joints=[13, 14, 16, 17, 18, 19]
            ),
            '弯腰': PredefinedAction(
                name='弯腰',
                description='上身向前弯曲',
                category='躯干',
                key_joints=[0, 3, 6, 9, 12]
            ),
            '踢腿': PredefinedAction(
                name='踢腿',
                description='腿部向前或侧向踢出',
                category='下肢',
                key_joints=[1, 2, 4, 5, 7, 8, 10, 11]
            ),
            '挥手': PredefinedAction(
                name='挥手',
                description='手臂前后挥动',
                category='上肢',
                key_joints=[13, 14, 16, 17, 18, 19, 20, 21]
            ),
            '坐下': PredefinedAction(
                name='坐下',
                description='身体由站立变为坐姿',
                category='基础',
                key_joints=[0, 1, 2, 4, 5, 7, 8]
            ),
            '跳跃': PredefinedAction(
                name='跳跃',
                description='双脚离地向上跳起',
                category='移动',
                key_joints=[0, 1, 2, 4, 5, 7, 8, 10, 11]
            ),
        }
        return actions
    
    def _load_pretrained_weights(self, weights_path: Optional[str] = None):
        if weights_path is None:
            print("Warning: No pretrained weights path provided, using random weights")
            return
        
        try:
            checkpoint = torch.load(weights_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            print(f"Loaded pretrained action recognition weights from {weights_path}")
        except Exception as e:
            print(f"Warning: Could not load pretrained weights: {e}")
    
    def _normalize_pose(self, pose_sequence: np.ndarray) -> np.ndarray:
        if pose_sequence.ndim == 3:
            pose_sequence = np.expand_dims(pose_sequence, axis=0)
        
        N, T, V, C = pose_sequence.shape
        
        root_joint = 0
        for i in range(N):
            for t in range(T):
                root_pos = pose_sequence[i, t, root_joint].copy()
                pose_sequence[i, t, :, :] -= root_pos
        
        max_val = np.max(np.abs(pose_sequence))
        if max_val > 0:
            pose_sequence /= max_val
        
        return pose_sequence
    
    def _prepare_input(self, pose_sequence: np.ndarray) -> torch.Tensor:
        normalized = self._normalize_pose(pose_sequence)
        
        if normalized.shape[1] < self.sequence_length:
            padding = np.zeros((normalized.shape[0], 
                               self.sequence_length - normalized.shape[1],
                               normalized.shape[2], normalized.shape[3]))
            normalized = np.concatenate([normalized, padding], axis=1)
        elif normalized.shape[1] > self.sequence_length:
            start = (normalized.shape[1] - self.sequence_length) // 2
            normalized = normalized[:, start:start+self.sequence_length, :, :]
        
        tensor = torch.tensor(normalized, dtype=torch.float32, device=self.device)
        tensor = tensor.permute(0, 3, 1, 2).contiguous()
        
        return tensor
    
    def update_pose(self, track_id: int, joints_3d: np.ndarray) -> Optional[ActionRecognitionResult]:
        if joints_3d.ndim == 3:
            joints_3d = joints_3d[0]
        
        if joints_3d.shape[0] > self.num_joints:
            joints_3d = joints_3d[:self.num_joints, :]
        
        if track_id not in self.pose_buffers:
            self.pose_buffers[track_id] = deque(maxlen=self.sequence_length * 2)
        
        self.pose_buffers[track_id].append(joints_3d.copy())
        
        if len(self.pose_buffers[track_id]) >= self.sequence_length:
            if len(self.pose_buffers[track_id]) % max(1, self.sequence_length - self.overlap) == 0:
                sequence = np.array(list(self.pose_buffers[track_id]))
                return self._recognize(track_id, sequence)
        
        if track_id in self.result_history and len(self.result_history[track_id]) > 0:
            return self.result_history[track_id][-1]
        
        return None
    
    def _recognize(self, track_id: int, pose_sequence: np.ndarray) -> ActionRecognitionResult:
        if pose_sequence.ndim == 3:
            pose_sequence = np.expand_dims(pose_sequence, axis=0)
        
        input_tensor = self._prepare_input(pose_sequence)
        
        with torch.no_grad():
            outputs = self.model(input_tensor)
            probabilities = F.softmax(outputs, dim=1)
            
            top_probs, top_indices = torch.topk(probabilities, k=5, dim=1)
            
            action_id = int(top_indices[0, 0].item())
            confidence = float(top_probs[0, 0].item())
            
            all_predictions = {}
            for i in range(min(self.num_classes, 5)):
                idx = int(top_indices[0, i].item())
                prob = float(top_probs[0, i].item())
                all_predictions[self.action_names[idx]] = prob
        
        result = ActionRecognitionResult(
            action_name=self.action_names[action_id],
            action_id=action_id,
            confidence=confidence,
            all_predictions=all_predictions,
            sequence_length=pose_sequence.shape[1]
        )
        
        if track_id not in self.result_history:
            self.result_history[track_id] = deque(maxlen=10)
        self.result_history[track_id].append(result)
        
        return result
    
    def recognize_sequence(self, pose_sequence: np.ndarray) -> ActionRecognitionResult:
        return self._recognize(-1, pose_sequence)
    
    def get_action_history(self, track_id: int) -> List[ActionRecognitionResult]:
        return list(self.result_history.get(track_id, []))
    
    def reset(self, track_id: Optional[int] = None):
        if track_id is not None:
            if track_id in self.pose_buffers:
                del self.pose_buffers[track_id]
            if track_id in self.result_history:
                del self.result_history[track_id]
        else:
            self.pose_buffers.clear()
            self.result_history.clear()


ACTION_LIST = [
    '站立', '行走', '跑步', '坐下', '站起',
    '弯腰', '抬手', '踢腿', '跳跃', '挥手',
    '深蹲', '俯卧撑', '引体向上', '拉伸', '转身'
]

ACTION_CATEGORIES = {
    '日常活动': ['站立', '行走', '跑步', '坐下', '站起', '转身'],
    '上肢运动': ['抬手', '挥手', '拉伸'],
    '下肢运动': ['踢腿', '深蹲'],
    '力量训练': ['俯卧撑', '引体向上', '跳跃'],
    '其他': ['弯腰'],
}
