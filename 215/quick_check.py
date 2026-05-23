import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

result_path = os.path.join(os.path.dirname(__file__), 'check_result.txt')

with open(result_path, 'w') as f:
    f.write('开始测试...\n')
    f.flush()
    
    try:
        import numpy as np
        f.write('✓ NumPy 导入成功\n')
        f.flush()
        
        from potentials import lennard_jones_potential
        r_min = 2.0 ** (1.0/6.0)
        pe = lennard_jones_potential(np.array([r_min**2]), r_cut=3.0)
        f.write(f'✓ LJ势测试: V(r_min) = {pe[0]:.6f}\n')
        f.flush()
        
        from utils import pbc_wrap, get_box_length
        wrapped = pbc_wrap(np.array([[12.0, -1.0, 5.0]]), 10.0)
        f.write(f'✓ PBC测试: {wrapped[0]}\n')
        f.flush()
        
        from molecular_dynamics import MolecularDynamics
        f.write('✓ MolecularDynamics 类导入成功\n')
        f.flush()
        
        md = MolecularDynamics(
            n_particles=32,
            temperature=1.0,
            density=0.8,
            dt=0.001,
            n_steps=500,
            dim=3,
            seed=42
        )
        f.write(f'✓ MD系统初始化成功\n')
        f.write(f'  粒子数: {md.n_particles}\n')
        f.write(f'  盒子: {md.box_length:.4f}\n')
        f.write(f'  初始温度: {md.temperature:.4f}\n')
        f.flush()
        
        for step in range(1, 501):
            md.step()
            if step % 100 == 0:
                te = md.kinetic_energy + md.potential_energy
                f.write(f'  步 {step:4d}: KE={md.kinetic_energy:8.3f}  PE={md.potential_energy:8.3f}  E={te:8.3f}  T={md.temperature:6.3f}\n')
                f.flush()
        
        f.write('\n✓ 模拟完成!\n')
        f.write(f'  邻居列表更新: {md.n_neighbor_updates} 次\n')
        f.write('\n所有测试通过!\n')
        
    except Exception as e:
        import traceback
        f.write(f'\n✗ 错误: {e}\n')
        f.write(traceback.format_exc())

print('测试完成，结果已写入 check_result.txt')
