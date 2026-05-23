import sys
sys.path.insert(0, '.')

def main():
    try:
        import numpy as np
        from molecular_dynamics import MolecularDynamics
        
        output = []
        output.append('=' * 60)
        output.append('分子动力学模拟框架 - 测试报告')
        output.append('=' * 60)
        
        md = MolecularDynamics(
            n_particles=64,
            temperature=1.0,
            density=0.8,
            dt=0.001,
            n_steps=1000,
            dim=3,
            seed=42
        )
        
        output.append(f'✓ 系统初始化成功')
        output.append(f'  粒子数: {md.n_particles}')
        output.append(f'  盒子边长: {md.box_length:.4f}')
        output.append(f'  初始温度: {md.temperature:.4f}')
        output.append(f'  初始势能: {md.potential_energy:.4f}')
        output.append(f'  初始动能: {md.kinetic_energy:.4f}')
        output.append('')
        output.append(f'{'步':>6} | {'动能':>10} | {'势能':>10} | {'总能':>10} | {'温度':>8}')
        output.append('-' * 60)
        
        for step in range(1, 1001):
            md.step()
            if step % 100 == 0:
                te = md.kinetic_energy + md.potential_energy
                output.append(f'{step:>6d} | {md.kinetic_energy:>10.3f} | {md.potential_energy:>10.3f} | {te:>10.3f} | {md.temperature:>8.3f}')
        
        output.append('')
        output.append('✓ 模拟运行成功!')
        output.append(f'  邻居列表更新次数: {md.n_neighbor_updates}')
        
        history = md.run(output_interval=100, verbose=False)
        if len(history) > 0:
            temps = [h['temperature'] for h in history]
            energies = [h['total_energy'] for h in history]
            output.append(f'')
            output.append(f'统计结果 (后1000步):')
            output.append(f'  平均温度: {np.mean(temps):.4f} ± {np.std(temps):.4f}')
            output.append(f'  平均总能: {np.mean(energies):.4f} ± {np.std(energies):.4f}')
            output.append(f'  总能相对涨落: {np.std(energies)/abs(np.mean(energies)):.6f}')
        
        output.append('')
        output.append('=' * 60)
        output.append('测试通过!')
        output.append('=' * 60)
        
        result = '\n'.join(output)
        print(result)
        
        with open('test_result.txt', 'w', encoding='utf-8') as f:
            f.write(result)
        
        return 0
    except Exception as e:
        import traceback
        error_msg = f'错误: {e}\n{traceback.format_exc()}'
        print(error_msg)
        with open('test_result.txt', 'w', encoding='utf-8') as f:
            f.write(error_msg)
        return 1

if __name__ == '__main__':
    sys.exit(main())
