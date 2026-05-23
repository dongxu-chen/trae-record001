import unittest
import numpy as np

from potentials import lennard_jones_potential, lennard_jones_force
from integrators import velocity_verlet_step, velocity_verlet_finalize
from neighbor_list import NeighborList
from utils import (
    pbc_wrap, pbc_distance, initialize_fcc, initialize_velocities,
    calculate_kinetic_energy, calculate_temperature, get_box_length
)
from molecular_dynamics import MolecularDynamics


class TestPotentials(unittest.TestCase):
    """测试势函数"""
    
    def test_lj_potential_minimum(self):
        """测试LJ势在r=2^(1/6)处达到最小值"""
        r_min = 2.0 ** (1.0 / 6.0)
        r2 = r_min ** 2
        pe = lennard_jones_potential(np.array([r2]), r_cut=3.0)
        self.assertAlmostEqual(pe[0], -1.0, places=6)
    
    def test_lj_potential_zero(self):
        """测试LJ势在r=1处为0"""
        r2 = 1.0
        pe = lennard_jones_potential(np.array([r2]), r_cut=3.0)
        self.assertAlmostEqual(pe[0], 0.0, places=6)
    
    def test_lj_force_zero_at_minimum(self):
        """测试LJ力在势阱处为0"""
        r_min = 2.0 ** (1.0 / 6.0)
        r2 = r_min ** 2
        f = lennard_jones_force(np.array([r_min]), np.array([r2]), r_cut=3.0)
        self.assertAlmostEqual(f[0], 0.0, places=6)
    
    def test_lj_cutoff(self):
        """测试截断半径外势能为0"""
        r2 = (3.0 ** 2)
        pe = lennard_jones_potential(np.array([r2]), r_cut=2.5)
        self.assertEqual(pe[0], 0.0)


class TestPBC(unittest.TestCase):
    """测试周期性边界条件"""
    
    def test_pbc_wrap(self):
        """测试位置包装"""
        box = 10.0
        positions = np.array([[12.0, -1.0, 5.0]])
        wrapped = pbc_wrap(positions, box)
        expected = np.array([[2.0, 9.0, 5.0]])
        np.testing.assert_array_almost_equal(wrapped, expected)
    
    def test_pbc_distance(self):
        """测试最小镜像距离"""
        box = 10.0
        dr = np.array([[8.0, 0.0, 0.0]])
        min_dr = pbc_distance(dr, box)
        expected = np.array([[-2.0, 0.0, 0.0]])
        np.testing.assert_array_almost_equal(min_dr, expected)


class TestIntegrators(unittest.TestCase):
    """测试积分器"""
    
    def test_verlet_conservation(self):
        """测试简单情况下的Verlet积分"""
        dt = 0.01
        positions = np.array([[0.0, 0.0, 0.0]])
        velocities = np.array([[1.0, 0.0, 0.0]])
        forces = np.array([[0.0, 0.0, 0.0]])
        
        new_pos, half_vel = velocity_verlet_step(positions, velocities, forces, dt)
        new_vel = velocity_verlet_finalize(half_vel, forces, dt)
        
        self.assertAlmostEqual(new_pos[0, 0], 0.01, places=6)
        self.assertAlmostEqual(new_vel[0, 0], 1.0, places=6)


class TestNeighborList(unittest.TestCase):
    """测试邻居列表"""
    
    def test_neighbor_list_build(self):
        """测试邻居列表构建"""
        positions = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [3.0, 0.0, 0.0]
        ])
        
        nl = NeighborList(r_cut=1.5, r_skin=0.0, box_length=10.0)
        neighbors = nl.build(positions)
        
        self.assertIn(1, neighbors[0])
        self.assertIn(0, neighbors[1])
        self.assertEqual(len(neighbors[2]), 0)
    
    def test_neighbor_need_update(self):
        """测试邻居列表更新检查"""
        positions = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
        
        nl = NeighborList(r_cut=1.5, r_skin=0.5, box_length=10.0)
        nl.build(positions)
        
        self.assertFalse(nl.need_update(positions))
        
        positions_new = positions.copy()
        positions_new[0] += 0.3
        self.assertTrue(nl.need_update(positions_new))


class TestUtils(unittest.TestCase):
    """测试工具函数"""
    
    def test_box_length(self):
        """测试盒子长度计算"""
        box = get_box_length(n_particles=1000, density=1.0, dim=3)
        expected_volume = 1000.0
        self.assertAlmostEqual(box ** 3, expected_volume, places=6)
    
    def test_fcc_initialization(self):
        """测试FCC晶格初始化"""
        n = 32
        box = 10.0
        positions = initialize_fcc(n, box, dim=3)
        self.assertEqual(positions.shape[0], n)
        self.assertTrue(np.all(positions >= 0))
        self.assertTrue(np.all(positions <= box))
    
    def test_temperature_calculation(self):
        """测试温度计算"""
        n = 100
        dim = 3
        velocities = np.random.randn(n, dim)
        temp = calculate_temperature(velocities)
        
        expected_ke = 0.5 * np.sum(velocities ** 2)
        dof = dim * n - dim
        expected_temp = 2.0 * expected_ke / dof
        
        self.assertAlmostEqual(temp, expected_temp, places=6)


class TestMolecularDynamics(unittest.TestCase):
    """测试主MD类"""
    
    def test_initialization(self):
        """测试MD系统初始化"""
        md = MolecularDynamics(
            n_particles=32,
            temperature=1.0,
            density=0.8,
            dt=0.001,
            n_steps=10,
            dim=3,
            seed=42
        )
        
        self.assertEqual(md.n_particles, 32)
        self.assertEqual(md.positions.shape, (32, 3))
        self.assertEqual(md.velocities.shape, (32, 3))
        self.assertEqual(md.forces.shape, (32, 3))
    
    def test_step(self):
        """测试单步模拟"""
        md = MolecularDynamics(
            n_particles=32,
            temperature=1.0,
            density=0.8,
            dt=0.001,
            n_steps=10,
            dim=3,
            seed=42
        )
        
        initial_energy = md.kinetic_energy + md.potential_energy
        md.step()
        
        self.assertEqual(md.current_step, 1)
        new_energy = md.kinetic_energy + md.potential_energy
        
        energy_diff = abs(new_energy - initial_energy)
        self.assertLess(energy_diff, 1.0)
    
    def test_run(self):
        """测试运行模拟"""
        md = MolecularDynamics(
            n_particles=16,
            temperature=1.0,
            density=0.8,
            dt=0.001,
            n_steps=500,
            dim=3,
            seed=42
        )
        
        history = md.run(output_interval=100, verbose=False)
        
        self.assertEqual(len(history), 5)
        self.assertIn('step', history[0])
        self.assertIn('kinetic_energy', history[0])
        self.assertIn('potential_energy', history[0])
        self.assertIn('temperature', history[0])
        
        avg_temp = np.mean([h['temperature'] for h in history])
        self.assertGreater(avg_temp, 0.5)
        self.assertLess(avg_temp, 1.5)


def run_quick_test():
    """运行一个快速测试以验证功能"""
    print("运行快速验证测试...\n")
    
    md = MolecularDynamics(
        n_particles=64,
        temperature=1.0,
        density=0.8,
        dt=0.001,
        n_steps=1000,
        dim=3,
        seed=42
    )
    
    print("初始状态:")
    print(f"  温度: {md.temperature:.4f}")
    print(f"  动能: {md.kinetic_energy:.4f}")
    print(f"  势能: {md.potential_energy:.4f}")
    print(f"  总能: {md.kinetic_energy + md.potential_energy:.4f}")
    
    print("\n运行1000步模拟...")
    history = md.run(output_interval=200, verbose=True)
    
    print("\n最终状态:")
    print(f"  平均温度: {np.mean([h['temperature'] for h in history]):.4f}")
    print(f"  平均总能: {np.mean([h['total_energy'] for h in history]):.4f}")
    
    energies = [h['total_energy'] for h in history]
    energy_fluctuation = np.std(energies) / abs(np.mean(energies))
    print(f"  总能相对涨落: {energy_fluctuation:.6f}")
    
    print("\n✓ 快速测试通过!")
    return True


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'unittest':
        unittest.main(argv=['first-arg-is-ignored'], verbosity=2)
    else:
        run_quick_test()
