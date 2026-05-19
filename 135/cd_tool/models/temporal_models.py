import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional
from .attention import CBAM, BoundaryAttention


class ConvLSTMCell(nn.Module):
    def __init__(self,
                 input_dim: int,
                 hidden_dim: int,
                 kernel_size: int = 3,
                 bias: bool = True):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.kernel_size = kernel_size
        self.padding = kernel_size // 2
        self.bias = bias
        
        self.conv = nn.Conv2d(
            in_channels=self.input_dim + self.hidden_dim,
            out_channels=4 * self.hidden_dim,
            kernel_size=self.kernel_size,
            padding=self.padding,
            bias=self.bias
        )
    
    def forward(self,
                input_tensor: torch.Tensor,
                cur_state: Tuple[torch.Tensor, torch.Tensor]) -> Tuple[torch.Tensor, torch.Tensor]:
        h_cur, c_cur = cur_state
        combined = torch.cat([input_tensor, h_cur], dim=1)
        combined_conv = self.conv(combined)
        
        cc_i, cc_f, cc_o, cc_g = torch.split(combined_conv, self.hidden_dim, dim=1)
        i = torch.sigmoid(cc_i)
        f = torch.sigmoid(cc_f)
        o = torch.sigmoid(cc_o)
        g = torch.tanh(cc_g)
        
        c_next = f * c_cur + i * g
        h_next = o * torch.tanh(c_next)
        
        return h_next, c_next
    
    def init_hidden(self, batch_size: int, image_size: Tuple[int, int], device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
        h = torch.zeros(batch_size, self.hidden_dim, image_size[0], image_size[1], device=device)
        c = torch.zeros(batch_size, self.hidden_dim, image_size[0], image_size[1], device=device)
        return h, c


class ConvLSTM(nn.Module):
    def __init__(self,
                 input_dim: int,
                 hidden_dims: list,
                 kernel_size: int = 3,
                 num_layers: int = 3,
                 bias: bool = True,
                 return_all_layers: bool = False):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dims = hidden_dims if isinstance(hidden_dims, list) else [hidden_dims] * num_layers
        self.kernel_size = kernel_size
        self.num_layers = num_layers
        self.bias = bias
        self.return_all_layers = return_all_layers
        
        cell_list = []
        for i in range(num_layers):
            cur_input_dim = self.input_dim if i == 0 else self.hidden_dims[i-1]
            cell_list.append(
                ConvLSTMCell(cur_input_dim, self.hidden_dims[i], kernel_size, bias)
            )
        self.cell_list = nn.ModuleList(cell_list)
    
    def forward(self,
                input_tensor: torch.Tensor,
                hidden_state: Optional[list] = None) -> Tuple[list, list]:
        b, seq_len, _, h, w = input_tensor.size()
        
        if hidden_state is None:
            hidden_state = self._init_hidden(b, (h, w), input_tensor.device)
        
        layer_output_list = []
        last_state_list = []
        
        cur_layer_input = input_tensor
        
        for layer_idx in range(self.num_layers):
            h, c = hidden_state[layer_idx]
            output_inner = []
            
            for t in range(seq_len):
                h, c = self.cell_list[layer_idx](cur_layer_input[:, t, :, :, :], (h, c))
                output_inner.append(h)
            
            layer_output = torch.stack(output_inner, dim=1)
            cur_layer_input = layer_output
            
            layer_output_list.append(layer_output)
            last_state_list.append((h, c))
        
        if not self.return_all_layers:
            layer_output_list = layer_output_list[-1:]
            last_state_list = last_state_list[-1:]
        
        return layer_output_list, last_state_list
    
    def _init_hidden(self, batch_size: int, image_size: Tuple[int, int], device: torch.device) -> list:
        init_states = []
        for i in range(self.num_layers):
            init_states.append(self.cell_list[i].init_hidden(batch_size, image_size, device))
        return init_states


class TemporalEncoder(nn.Module):
    def __init__(self,
                 in_channels: int = 3,
                 hidden_dims: list = [64, 128, 256],
                 kernel_size: int = 3,
                 dropout: float = 0.1):
        super().__init__()
        
        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, hidden_dims[0], kernel_size=7, stride=2, padding=3),
            nn.BatchNorm2d(hidden_dims[0]),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        )
        
        self.layers = nn.ModuleList()
        for i in range(len(hidden_dims) - 1):
            self.layers.append(nn.Sequential(
                nn.Conv2d(hidden_dims[i], hidden_dims[i+1], kernel_size=3, padding=1),
                nn.BatchNorm2d(hidden_dims[i+1]),
                nn.ReLU(inplace=True),
                nn.Conv2d(hidden_dims[i+1], hidden_dims[i+1], kernel_size=3, padding=1),
                nn.BatchNorm2d(hidden_dims[i+1]),
                nn.ReLU(inplace=True),
                nn.Dropout2d(dropout)
            ))
    
    def forward(self, x: torch.Tensor) -> list:
        b, t, c, h, w = x.shape
        x = x.view(b * t, c, h, w)
        x = self.stem(x)
        features = [x.view(b, t, -1, x.shape[-2], x.shape[-1])]
        
        for layer in self.layers:
            x = layer(x)
            features.append(x.view(b, t, -1, x.shape[-2], x.shape[-1]))
        
        return features


class TemporalChangeDetection(nn.Module):
    def __init__(self,
                 in_channels: int = 3,
                 num_classes: int = 1,
                 hidden_dims: list = [64, 128, 256],
                 lstm_layers: int = 2,
                 use_attention: bool = True,
                 use_boundary_attention: bool = True):
        super().__init__()
        self.in_channels = in_channels
        self.num_classes = num_classes
        self.use_attention = use_attention
        self.use_boundary_attention = use_boundary_attention
        
        self.encoder = TemporalEncoder(in_channels, hidden_dims)
        
        self.conv_lstms = nn.ModuleList()
        for i in range(len(hidden_dims)):
            self.conv_lstms.append(
                ConvLSTM(
                    input_dim=hidden_dims[i],
                    hidden_dims=[hidden_dims[i]],
                    kernel_size=3,
                    num_layers=lstm_layers,
                    return_all_layers=False
                )
            )
        
        if use_attention:
            self.attention_modules = nn.ModuleList([
                CBAM(hidden_dims[i]) for i in range(len(hidden_dims))
            ])
        
        self.decoder = nn.ModuleList()
        for i in range(len(hidden_dims) - 1, 0, -1):
            self.decoder.append(nn.Sequential(
                nn.ConvTranspose2d(hidden_dims[i], hidden_dims[i-1], kernel_size=2, stride=2),
                nn.BatchNorm2d(hidden_dims[i-1]),
                nn.ReLU(inplace=True),
                nn.Conv2d(hidden_dims[i-1], hidden_dims[i-1], kernel_size=3, padding=1),
                nn.BatchNorm2d(hidden_dims[i-1]),
                nn.ReLU(inplace=True)
            ))
        
        if use_boundary_attention:
            self.boundary_attention = BoundaryAttention(hidden_dims[0])
        
        self.final_conv = nn.Sequential(
            nn.Conv2d(hidden_dims[0], hidden_dims[0] // 2, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(hidden_dims[0] // 2, hidden_dims[0] // 4, kernel_size=4, stride=4),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden_dims[0] // 4, num_classes, kernel_size=1)
        )
    
    def forward(self, x: torch.Tensor, return_boundary: bool = False):
        b, t, c, h, w = x.shape
        
        features = self.encoder(x)
        
        temporal_features = []
        for i, feat in enumerate(features):
            lstm_out, _ = self.conv_lstms[i](feat)
            tf = lstm_out[0][:, -1]
            if self.use_attention:
                tf = self.attention_modules[i](tf)
            temporal_features.append(tf)
        
        x = temporal_features[-1]
        for i, decoder_layer in enumerate(self.decoder):
            feat_idx = len(temporal_features) - 2 - i
            x = decoder_layer(x)
            x = x + temporal_features[feat_idx]
        
        boundary_map = None
        if self.use_boundary_attention:
            x, boundary_map = self.boundary_attention(x)
        
        logits = self.final_conv(x)
        
        if return_boundary and boundary_map is not None:
            return logits, boundary_map
        return logits
    
    @torch.no_grad()
    def predict(self, x: torch.Tensor) -> torch.Tensor:
        logits = self.forward(x)
        if self.num_classes == 1:
            pred = torch.sigmoid(logits)
        else:
            pred = torch.softmax(logits, dim=1)
        return pred


class SiameseLSTM(nn.Module):
    def __init__(self,
                 in_channels: int = 3,
                 num_classes: int = 1,
                 hidden_dim: int = 128,
                 num_layers: int = 2,
                 bidirectional: bool = True):
        super().__init__()
        self.num_classes = num_classes
        self.hidden_dim = hidden_dim
        self.bidirectional = bidirectional
        
        self.cnn_encoder = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, hidden_dim, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(hidden_dim),
            nn.ReLU(inplace=True)
        )
        
        self.lstm = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=bidirectional
        )
        
        self.decoder = nn.Sequential(
            nn.Conv2d(hidden_dim * (2 if bidirectional else 1), 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=4),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, num_classes, kernel_size=1)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, t, c, h, w = x.shape
        
        cnn_features = []
        for i in range(t):
            feat = self.cnn_encoder(x[:, i])
            feat = F.adaptive_avg_pool2d(feat, (1, 1)).view(b, -1)
            cnn_features.append(feat)
        
        seq_features = torch.stack(cnn_features, dim=1)
        
        lstm_out, _ = self.lstm(seq_features)
        final_feat = lstm_out[:, -1:]
        final_feat = final_feat.view(b, -1, 1, 1).repeat(1, 1, h // 8, w // 8)
        
        logits = self.decoder(final_feat)
        return logits
