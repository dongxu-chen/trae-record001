import importlib.util

if importlib.util.find_spec("cupy") is not None:
    import cupy as np
    GPU_AVAILABLE = True
else:
    import numpy as np
    GPU_AVAILABLE = False


ELEMENT_MAP = {
    'Ar': {'symbol': 'Ar', 'mass': 39.948, 'color': 'blue'},
    'Ne': {'symbol': 'Ne', 'mass': 20.180, 'color': 'green'},
    'He': {'symbol': 'He', 'mass': 4.003, 'color': 'red'},
    'Xe': {'symbol': 'Xe', 'mass': 131.293, 'color': 'purple'},
    'Kr': {'symbol': 'Kr', 'mass': 83.798, 'color': 'orange'},
    'C': {'symbol': 'C', 'mass': 12.011, 'color': 'gray'},
    'O': {'symbol': 'O', 'mass': 15.999, 'color': 'red'},
    'N': {'symbol': 'N', 'mass': 14.007, 'color': 'blue'},
    'H': {'symbol': 'H', 'mass': 1.008, 'color': 'white'},
    'Na': {'symbol': 'Na', 'mass': 22.990, 'color': 'purple'},
    'Cl': {'symbol': 'Cl', 'mass': 35.453, 'color': 'green'},
}


class XYZWriter:
    """
    XYZ格式轨迹写入器
    
    XYZ格式:
        第1行: 原子数
        第2行: 注释/性质
        后续行: 元素符号 x y z
    """
    
    def __init__(self, filename, element='Ar', write_frequency=100):
        """
        初始化XYZ写入器
        
        参数:
            filename: 输出文件名
            element: 元素符号 (用于LJ系统)
            write_frequency: 写入频率 (步数)
        """
        self.filename = filename
        self.element = element
        self.write_frequency = write_frequency
        self.frame_count = 0
        self.file = None
        
    def open(self):
        """打开文件"""
        self.file = open(self.filename, 'w', encoding='utf-8')
        return self
    
    def close(self):
        """关闭文件"""
        if self.file:
            self.file.close()
            self.file = None
    
    def write_frame(self, positions, step=0, box_length=None, properties=None):
        """
        写入单帧轨迹
        
        参数:
            positions: 位置矩阵 (N, 3)
            step: 当前步数
            box_length: 盒子边长
            properties: 额外属性字典
        """
        if self.file is None:
            return
        
        n_particles = positions.shape[0]
        
        comment_parts = [f'Step: {step}']
        if box_length is not None:
            if isinstance(box_length, (int, float)):
                comment_parts.append(f'Box: {box_length:.4f} {box_length:.4f} {box_length:.4f}')
            elif hasattr(box_length, '__len__') and len(box_length) == 3:
                comment_parts.append(f'Box: {box_length[0]:.4f} {box_length[1]:.4f} {box_length[2]:.4f}')
        
        if properties:
            for key, value in properties.items():
                comment_parts.append(f'{key}: {value}')
        
        comment = ' '.join(comment_parts)
        
        self.file.write(f'{n_particles}\n')
        self.file.write(f'{comment}\n')
        
        pos = positions
        if GPU_AVAILABLE and hasattr(positions, 'get'):
            pos = positions.get()
        
        for i in range(n_particles):
            x, y, z = pos[i, 0], pos[i, 1], pos[i, 2] if pos.shape[1] == 3 else (pos[i, 0], pos[i, 1], 0.0)
            self.file.write(f'{self.element} {x:12.6f} {y:12.6f} {z:12.6f}\n')
        
        self.frame_count += 1
    
    def __enter__(self):
        return self.open()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class ExtendedXYZWriter:
    """
    扩展XYZ格式轨迹写入器 (支持速度、力等性质)
    
    格式类似于XYZ，但在注释行中包含更多信息，
    并且每个原子行可以包含额外的列 (vx, vy, vz, fx, fy, fz等)
    """
    
    def __init__(self, filename, element='Ar', write_frequency=100,
                 include_velocities=True, include_forces=False):
        """
        初始化扩展XYZ写入器
        
        参数:
            filename: 输出文件名
            element: 元素符号
            write_frequency: 写入频率
            include_velocities: 是否包含速度
            include_forces: 是否包含力
        """
        self.filename = filename
        self.element = element
        self.write_frequency = write_frequency
        self.include_velocities = include_velocities
        self.include_forces = include_forces
        self.frame_count = 0
        self.file = None
        
    def open(self):
        self.file = open(self.filename, 'w', encoding='utf-8')
        return self
    
    def close(self):
        if self.file:
            self.file.close()
            self.file = None
    
    def write_frame(self, positions, velocities=None, forces=None,
                    step=0, box_length=None, properties=None):
        if self.file is None:
            return
        
        n_particles = positions.shape[0]
        
        properties_line = []
        if box_length is not None:
            if isinstance(box_length, (int, float)):
                properties_line.append(f'pbc=\"T T T\"')
                properties_line.append(f'Lattice=\"{box_length} 0 0 0 {box_length} 0 0 0 {box_length}\"')
        
        if properties:
            for key, value in properties.items():
                properties_line.append(f'{key}=\"{value}\"')
        
        comment = ' '.join(properties_line) if properties_line else f'Step: {step}'
        
        self.file.write(f'{n_particles}\n')
        self.file.write(f'{comment}\n')
        
        pos = positions
        if GPU_AVAILABLE and hasattr(positions, 'get'):
            pos = positions.get()
        
        vel = velocities
        if vel is not None and GPU_AVAILABLE and hasattr(velocities, 'get'):
            vel = velocities.get()
        
        f = forces
        if f is not None and GPU_AVAILABLE and hasattr(forces, 'get'):
            f = forces.get()
        
        for i in range(n_particles):
            x = pos[i, 0]
            y = pos[i, 1]
            z = pos[i, 2] if pos.shape[1] == 3 else 0.0
            
            line = f'{self.element} {x:12.6f} {y:12.6f} {z:12.6f}'
            
            if self.include_velocities and vel is not None:
                vx = vel[i, 0]
                vy = vel[i, 1]
                vz = vel[i, 2] if vel.shape[1] == 3 else 0.0
                line += f' {vx:12.6f} {vy:12.6f} {vz:12.6f}'
            
            if self.include_forces and f is not None:
                fx = f[i, 0]
                fy = f[i, 1]
                fz = f[i, 2] if f.shape[1] == 3 else 0.0
                line += f' {fx:12.6f} {fy:12.6f} {fz:12.6f}'
            
            self.file.write(line + '\n')
        
        self.frame_count += 1
    
    def __enter__(self):
        return self.open()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def read_xyz(filename):
    """
    读取XYZ格式轨迹文件
    
    参数:
        filename: 文件名
    
    返回:
        frames: 帧列表，每帧包含 {'positions': ..., 'comment': ..., 'n_atoms': ...}
    """
    frames = []
    
    with open(filename, 'r') as f:
        while True:
            line = f.readline()
            if not line:
                break
            
            n_atoms = int(line.strip())
            comment = f.readline().strip()
            
            positions = []
            elements = []
            
            for _ in range(n_atoms):
                parts = f.readline().split()
                element = parts[0]
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                elements.append(element)
                positions.append([x, y, z])
            
            frames.append({
                'n_atoms': n_atoms,
                'comment': comment,
                'elements': elements,
                'positions': np.array(positions)
            })
    
    return frames


def convert_to_ase_atoms(frames, box_length=None):
    """
    将XYZ帧转换为ASE Atoms对象 (需要ase库)
    
    参数:
        frames: read_xyz返回的帧列表
        box_length: 盒子边长
    
    返回:
        atoms_list: ASE Atoms对象列表
    """
    try:
        from ase import Atoms
        from ase.units import Bohr
    except ImportError:
        print("警告: 未安装ase库，无法转换")
        return []
    
    atoms_list = []
    
    for frame in frames:
        positions = frame['positions']
        symbols = frame['elements']
        
        cell = None
        if box_length is not None:
            cell = [box_length, box_length, box_length]
        
        atoms = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
        atoms_list.append(atoms)
    
    return atoms_list


def write_xyz_simple(filename, positions_list, element='Ar', step_list=None, box_length=None):
    """
    简单的XYZ写入函数
    
    参数:
        filename: 输出文件名
        positions_list: 位置列表，每个元素是 (N, 3) 数组
        element: 元素符号
        step_list: 步数列表
        box_length: 盒子边长
    """
    with open(filename, 'w') as f:
        for i, positions in enumerate(positions_list):
            n = positions.shape[0]
            step = step_list[i] if step_list else i * 100
            
            comment = f'Step: {step}'
            if box_length is not None:
                comment += f' Box: {box_length:.4f} {box_length:.4f} {box_length:.4f}'
            
            f.write(f'{n}\n')
            f.write(f'{comment}\n')
            
            for j in range(n):
                x, y, z = positions[j, 0], positions[j, 1], positions[j, 2]
                f.write(f'{element} {x:12.6f} {y:12.6f} {z:12.6f}\n')
