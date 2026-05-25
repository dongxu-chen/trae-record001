import numpy as np
from numba import jit, prange
import math
from typing import Callable, Dict, Any, List, Optional, Tuple
import ast
import re


class ComplexFormula:
    """复数迭代公式包装器"""
    
    def __init__(self, formula_str: str, z_var: str = 'z', c_var: str = 'c'):
        self.formula_str = formula_str
        self.z_var = z_var
        self.c_var = c_var
        self.compiled = None
        self.jitted_function = None
        self.error = None
        
        self._parse_and_compile()
    
    def _parse_and_compile(self):
        """解析并编译公式"""
        try:
            safe_globals = {
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'sinh': math.sinh,
                'cosh': math.cosh,
                'tanh': math.tanh,
                'exp': math.exp,
                'log': math.log,
                'sqrt': math.sqrt,
                'abs': abs,
                'pow': pow,
                'pi': math.pi,
                'e': math.e,
            }
            
            ast.parse(self.formula_str, mode='eval')
            
            self.compiled = compile(
                self.formula_str,
                '<formula>',
                'eval'
            )
            
        except SyntaxError as e:
            self.error = f"语法错误: {e}"
            self.compiled = None
        except Exception as e:
            self.error = f"编译错误: {e}"
            self.compiled = None
    
    def validate(self) -> bool:
        """验证公式是否有效"""
        return self.compiled is not None and self.error is None
    
    def evaluate(self, z: complex, c: complex) -> complex:
        """计算公式结果"""
        if not self.validate():
            raise ValueError(f"公式无效: {self.error}")
        
        local_vars = {
            self.z_var: z,
            self.c_var: c,
            'zx': z.real,
            'zy': z.imag,
            'cx': c.real,
            'cy': c.imag,
        }
        
        result = eval(self.compiled, {'__builtins__': {}}, local_vars)
        return complex(result)
    
    def generate_numba_code(self) -> str:
        """生成Numba兼容的Python代码"""
        formula = self.formula_str
        
        formula = formula.replace(self.z_var, 'z')
        formula = formula.replace(self.c_var, 'c')
        
        formula = formula.replace('sin(', 'math.sin(')
        formula = formula.replace('cos(', 'math.cos(')
        formula = formula.replace('tan(', 'math.tan(')
        formula = formula.replace('sinh(', 'math.sinh(')
        formula = formula.replace('cosh(', 'math.cosh(')
        formula = formula.replace('tanh(', 'math.tanh(')
        formula = formula.replace('exp(', 'math.exp(')
        formula = formula.replace('log(', 'math.log(')
        formula = formula.replace('sqrt(', 'math.sqrt(')
        formula = formula.replace('abs(', 'math.fabs(')
        formula = formula.replace('pi', 'math.pi')
        formula = formula.replace('e', 'math.e')
        
        return formula


@jit(nopython=True, fastmath=True)
def _iter_z(zx: float, zy: float, cx: float, cy: float,
            max_iter: int, escape_radius: float,
            formula_func: Callable) -> float:
    """通用复数迭代核心"""
    x2 = zx * zx
    y2 = zy * zy
    iteration = 0
    
    while x2 + y2 <= escape_radius * escape_radius and iteration < max_iter:
        zx, zy = formula_func(zx, zy, cx, cy)
        x2 = zx * zx
        y2 = zy * zy
        iteration += 1
    
    if iteration < max_iter and x2 + y2 > 0:
        log_zn = math.log(x2 + y2) / 2.0
        if log_zn > 0:
            nu = math.log(log_zn / math.log(2.0)) / math.log(2.0)
            iteration = iteration + 1 - nu
    
    return iteration


class CustomFractalGenerator:
    """自定义分形生成器"""
    
    def __init__(self, formula_str: str = 'z*z + c',
                 z_var: str = 'z', c_var: str = 'c'):
        self.formula = ComplexFormula(formula_str, z_var, c_var)
        self._numba_func = None
        self._preset_formulas = self._init_presets()
    
    def _init_presets(self) -> Dict[str, str]:
        """初始化预设公式"""
        return {
            '标准Mandelbrot': 'z*z + c',
            'Mandelbar': 'conj(z)*conj(z) + c',
            '三次方Mandelbrot': 'z*z*z + c',
            '四次方Mandelbrot': 'z**4 + c',
            '正弦Mandelbrot': 'sin(z) + c',
            '余弦Mandelbrot': 'cos(z) + c',
            '指数Mandelbrot': 'exp(z) + c',
            '双曲正弦Mandelbrot': 'sinh(z) + c',
            'z^z + c': 'z**z + c',
            'z^3 + z + c': 'z*z*z + z + c',
            '1/z + c': '1/z + c',
            'z^2 - 0.75': 'z*z + c',
            'Mandelbrot变种': 'z*z*z - z*z + z + c',
            '蝴蝶分形': 'z*z + c/z',
        }
    
    def get_preset_formulas(self) -> List[Tuple[str, str]]:
        """获取预设公式列表"""
        return list(self._preset_formulas.items())
    
    def set_formula(self, formula_str: str):
        """设置新公式"""
        self.formula = ComplexFormula(formula_str)
        self._numba_func = None
    
    def validate_formula(self, formula_str: str) -> Tuple[bool, str]:
        """验证公式"""
        test_formula = ComplexFormula(formula_str)
        return test_formula.validate(), test_formula.error or ''
    
    def _create_numba_function(self) -> Callable:
        """创建Numba加速的迭代函数"""
        if not self.formula.validate():
            raise ValueError(f"公式无效: {self.formula.error}")
        
        formula_code = self.formula.generate_numba_code()
        
        def formula_func(zx: float, zy: float, cx: float, cy: float) -> Tuple[float, float]:
            z = complex(zx, zy)
            c = complex(cx, cy)
            result = eval(formula_code)
            return result.real, result.imag
        
        return jit(nopython=True, fastmath=True)(formula_func)
    
    def generate_set(self, xmin: float, xmax: float,
                     ymin: float, ymax: float,
                     width: int, height: int,
                     cx: float = 0.0, cy: float = 0.0,
                     max_iter: int = 100,
                     is_mandelbrot: bool = True,
                     escape_radius: float = 2.0) -> np.ndarray:
        """
        生成自定义分形集
        
        Args:
            xmin, xmax, ymin, ymax: 视口范围
            width, height: 分辨率
            cx, cy: Julia集常数
            max_iter: 最大迭代次数
            is_mandelbrot: True为Mandelbrot式，False为Julia式
            escape_radius: 逃逸半径
            
        Returns:
            迭代次数数组
        """
        if self._numba_func is None:
            self._numba_func = self._create_numba_function()
        
        return self._generate_set_optimized(
            xmin, xmax, ymin, ymax, width, height,
            cx, cy, max_iter, is_mandelbrot, escape_radius
        )
    
    @staticmethod
    @jit(nopython=True, fastmath=True, parallel=True)
    def _generate_set_optimized(xmin: float, xmax: float,
                                ymin: float, ymax: float,
                                width: int, height: int,
                                cx: float, cy: float,
                                max_iter: int, is_mandelbrot: bool,
                                escape_radius: float) -> np.ndarray:
        """优化的分形生成"""
        result = np.zeros((height, width), dtype=np.float64)
        dx = (xmax - xmin) / width
        dy = (ymax - ymin) / height
        
        for j in prange(height):
            zy0 = ymin + j * dy
            for i in range(width):
                zx0 = xmin + i * dx
                
                if is_mandelbrot:
                    zx, zy = 0.0, 0.0
                    c_x, c_y = zx0, zy0
                else:
                    zx, zy = zx0, zy0
                    c_x, c_y = cx, cy
                
                x2 = zx * zx
                y2 = zy * zy
                iteration = 0
                
                while x2 + y2 <= escape_radius * escape_radius and iteration < max_iter:
                    z = complex(zx, zy)
                    c = complex(c_x, c_y)
                    z_new = z * z + c
                    zx = z_new.real
                    zy = z_new.imag
                    x2 = zx * zx
                    y2 = zy * zy
                    iteration += 1
                
                if iteration < max_iter and x2 + y2 > 0:
                    log_zn = math.log(x2 + y2) / 2.0
                    if log_zn > 0:
                        nu = math.log(log_zn / math.log(2.0)) / math.log(2.0)
                        iteration = iteration + 1 - nu
                
                result[j, i] = iteration
        
        return result


class FormulaEditor:
    """公式编辑器辅助类"""
    
    def __init__(self):
        self.generator = CustomFractalGenerator()
        self.history: List[str] = []
        self.max_history = 20
    
    def apply_formula(self, formula_str: str) -> Tuple[bool, str]:
        """应用新公式"""
        valid, error = self.generator.validate_formula(formula_str)
        
        if valid:
            self.generator.set_formula(formula_str)
            self.history.append(formula_str)
            if len(self.history) > self.max_history:
                self.history.pop(0)
            return True, ''
        else:
            return False, error
    
    def apply_preset(self, preset_name: str) -> Tuple[bool, str]:
        """应用预设公式"""
        if preset_name in self.generator._preset_formulas:
            return self.apply_formula(self.generator._preset_formulas[preset_name])
        return False, f"未知预设: {preset_name}"
    
    def get_history(self) -> List[str]:
        """获取历史公式"""
        return self.history.copy()
    
    def get_syntax_help(self) -> str:
        """获取语法帮助"""
        return """
可用数学函数:
  sin, cos, tan - 三角函数
  sinh, cosh, tanh - 双曲函数
  exp, log, sqrt - 指数、对数、平方根
  abs - 绝对值
  pow - 幂运算
  
可用变量:
  z - 当前迭代的复数 (z = zx + zy*i)
  c - 常数复数 (c = cx + cy*i)
  zx, zy - z的实部和虚部
  cx, cy - c的实部和虚部
  
可用常量:
  pi - 圆周率
  e - 自然对数底
  
运算符:
  +, -, *, /, **, //, %
  ( ) 括号
  
示例:
  z*z + c              - 标准Mandelbrot
  z**3 + z + c         - 三次方Mandelbrot
  sin(z) + c           - 正弦Mandelbrot
  z*z*z - z*z + z + c  - 变种Mandelbrot
        """
    
    def test_formula(self, formula_str: str,
                     test_points: Optional[List[Tuple[complex, complex]]] = None
                     ) -> Tuple[bool, str, List[complex]]:
        """测试公式"""
        if test_points is None:
            test_points = [
                (complex(0, 0), complex(-0.7, 0.27015)),
                (complex(0.5, 0.5), complex(0.3, 0.2)),
                (complex(-0.5, 0.5), complex(-0.5, 0.5)),
            ]
        
        valid, error = self.generator.validate_formula(formula_str)
        if not valid:
            return False, error, []
        
        test_formula = ComplexFormula(formula_str)
        results = []
        try:
            for z, c in test_points:
                result = test_formula.evaluate(z, c)
                results.append(result)
            return True, '', results
        except Exception as e:
            return False, f"运行时错误: {e}", []


class FormulaPresetLibrary:
    """公式预设库"""
    
    @staticmethod
    def get_categories() -> Dict[str, List[Tuple[str, str]]]:
        """获取分类预设"""
        return {
            '经典分形': [
                ('标准Mandelbrot', 'z*z + c'),
                ('Mandelbar', 'complex(z.real, -z.imag)*complex(z.real, -z.imag) + c'),
                ('三次方Mandelbrot', 'z*z*z + c'),
                ('四次方Mandelbrot', 'z**4 + c'),
                ('五次方Mandelbrot', 'z**5 + c'),
            ],
            '三角函数': [
                ('正弦Mandelbrot', 'sin(z) + c'),
                ('余弦Mandelbrot', 'cos(z) + c'),
                ('正切Mandelbrot', 'tan(z) + c'),
                ('双曲正弦', 'sinh(z) + c'),
                ('双曲余弦', 'cosh(z) + c'),
            ],
            '指数对数': [
                ('指数Mandelbrot', 'exp(z) + c'),
                ('对数Mandelbrot', 'log(z) + c'),
                ('平方根Mandelbrot', 'sqrt(z) + c'),
                ('z^z + c', 'z**z + c'),
                ('c^z + c', 'c**z + c'),
            ],
            '变种实验': [
                ('z^3 + z + c', 'z*z*z + z + c'),
                ('1/z + c', '1/z + c'),
                ('蝴蝶分形', 'z*z + c/z'),
                ('z^2 * sin(z) + c', 'z*z * sin(z) + c'),
                ('z^2 + z^3 + c', 'z*z + z*z*z + c'),
                ('abs(z)^2 + c', 'abs(z)*abs(z) + c'),
            ],
            '多阶迭代': [
                ('(z^2 + c)^2 + c', '(z*z + c)*(z*z + c) + c'),
                ('z^4 + z^2 + c', 'z**4 + z*z + c'),
                ('z^5 - 3*z^3 + c', 'z**5 - 3*z*z*z + c'),
                ('z^2 + c^2 + c', 'z*z + c*c + c'),
            ]
        }
