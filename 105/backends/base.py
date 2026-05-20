from abc import ABC, abstractmethod
from typing import Any, Tuple, Optional

Array = Any


class LinearAlgebraBackend(ABC):
    """线性代数后端抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """后端名称"""
        pass

    @property
    @abstractmethod
    def xp(self):
        """数组模块 (numpy, cupy 等)"""
        pass

    @property
    @abstractmethod
    def available(self) -> bool:
        """后端是否可用"""
        pass

    @abstractmethod
    def to_device(self, array: Array) -> Array:
        """将数组转移到后端设备"""
        pass

    @abstractmethod
    def to_host(self, array: Array) -> Array:
        """将数组转移到主机内存"""
        pass

    @abstractmethod
    def dot(self, a: Array, b: Array) -> Array:
        """矩阵乘法"""
        pass

    @abstractmethod
    def norm(self, a: Array, axis: Optional[int] = None) -> Array:
        """计算范数"""
        pass

    @abstractmethod
    def eye(self, n: int, dtype: Any = None) -> Array:
        """创建单位矩阵"""
        pass

    @abstractmethod
    def zeros(self, shape: Tuple[int, ...], dtype: Any = None) -> Array:
        """创建零矩阵"""
        pass

    @abstractmethod
    def ones(self, shape: Tuple[int, ...], dtype: Any = None) -> Array:
        """创建全一矩阵"""
        pass

    @abstractmethod
    def random(self, shape: Tuple[int, ...]) -> Array:
        """创建随机矩阵"""
        pass

    @abstractmethod
    def sqrt(self, x: Array) -> Array:
        """平方根"""
        pass

    @abstractmethod
    def abs(self, x: Array) -> Array:
        """绝对值"""
        pass

    @abstractmethod
    def real(self, x: Array) -> Array:
        """实部"""
        pass

    @abstractmethod
    def imag(self, x: Array) -> Array:
        """虚部"""
        pass

    @abstractmethod
    def conj(self, x: Array) -> Array:
        """共轭"""
        pass

    @abstractmethod
    def cos(self, x: Array) -> Array:
        """余弦"""
        pass

    @abstractmethod
    def sin(self, x: Array) -> Array:
        """正弦"""
        pass

    @abstractmethod
    def atan2(self, y: Array, x: Array) -> Array:
        """反正切"""
        pass

    @abstractmethod
    def argsort(self, x: Array) -> Array:
        """排序索引"""
        pass

    @abstractmethod
    def sum(self, x: Array, axis: Optional[int] = None) -> Array:
        """求和"""
        pass

    @abstractmethod
    def diag(self, x: Array) -> Array:
        """提取对角线或创建对角矩阵"""
        pass

    @abstractmethod
    def eig(self, a: Array) -> Tuple[Array, Array]:
        """计算特征值和特征向量（用于验证）"""
        pass

    @abstractmethod
    def is_sparse(self, a: Array) -> bool:
        """检查是否为稀疏矩阵"""
        pass

    @abstractmethod
    def supports_sparse(self) -> bool:
        """是否支持稀疏矩阵"""
        pass

    def synchronize(self):
        """同步设备（用于GPU计时）"""
        pass
