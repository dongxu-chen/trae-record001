import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import torch
from training import JointLoss, Trainer, VideoDataset, create_trainer
from models import create_vespcn_model

jl = JointLoss(interp_weight=0.5, sr_weight=0.5)
ip = torch.randn(1,3,32,32)
ig = torch.randn(1,3,32,32)
sp = torch.randn(1,3,64,64)
sg = torch.randn(1,3,64,64)
pf = torch.randn(1,3,32,32)
nf = torch.randn(1,3,32,32)
m = create_vespcn_model(device='cpu')
tl, d = jl(ip, ig, sp, sg, pf, nf, m)
print(f'JointLoss: total={tl.item():.4f}')
for k, v in d.items():
    val = v.item() if isinstance(v, torch.Tensor) else v
    print(f'  {k}: {val:.4f}')

jl.set_weights(interp_weight=0.7, sr_weight=0.3)
print(f'Weights: interp={jl.interp_weight} sr={jl.sr_weight}')
print('Training module OK!')
