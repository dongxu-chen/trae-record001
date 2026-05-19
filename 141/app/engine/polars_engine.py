import importlib
import importlib.util
import sys
import time
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Union
from decimal import Decimal
from datetime import datetime
from functools import lru_cache

try:
    import polars as pl
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False
    pl = None

try:
    import cudf
    import cupy as cp
    CUDF_AVAILABLE = True
except ImportError:
    CUDF_AVAILABLE = False
    cudf = None
    cp = None

try:
    import pyarrow as pa
    PYARROW_AVAILABLE = True
except ImportError:
    PYARROW_AVAILABLE = False
    pa = None


class BackendType:
    POLARS = "polars"
    CUDF = "cudf"
    AUTO = "auto"


class ZeroCopyPricingEngine:
    def __init__(self, backend: str = BackendType.AUTO):
        self.backend = self._detect_backend(backend)
        self.df = None
        self._model_cache: Dict[str, Callable] = {}
        self._model_metadata: Dict[str, Dict[str, Any]] = {}
        self._factor_cache: Dict[str, Any] = {}
        self._warmup_complete = False
        
    def _detect_backend(self, requested_backend: str) -> str:
        if requested_backend == BackendType.AUTO:
            if CUDF_AVAILABLE:
                return BackendType.CUDF
            elif POLARS_AVAILABLE:
                return BackendType.POLARS
            else:
                raise ImportError("Neither Polars nor CuDF is available")
        elif requested_backend == BackendType.CUDF and not CUDF_AVAILABLE:
            print("Warning: CuDF requested but not available, falling back to Polars")
            return BackendType.POLARS
        elif requested_backend == BackendType.POLARS and not POLARS_AVAILABLE:
            raise ImportError("Polars is not available")
        return requested_backend
    
    def get_backend_info(self) -> Dict[str, Any]:
        return {
            "active_backend": self.backend,
            "polars_available": POLARS_AVAILABLE,
            "cudf_available": CUDF_AVAILABLE,
            "pyarrow_available": PYARROW_AVAILABLE,
            "polars_version": pl.__version__ if POLARS_AVAILABLE else None,
            "gpu_accelerated": self.backend == BackendType.CUDF
        }
    
    def load_data_from_records(self, records: List[Dict[str, Any]]) -> 'ZeroCopyPricingEngine':
        if self.backend == BackendType.CUDF:
            self.df = cudf.DataFrame(records)
        else:
            self.df = pl.DataFrame(records)
        return self
    
    def load_data_from_arrow(self, arrow_table: Any) -> 'ZeroCopyPricingEngine':
        if not PYARROW_AVAILABLE:
            raise ImportError("PyArrow is required for Arrow zero-copy")
        
        if self.backend == BackendType.CUDF:
            self.df = cudf.DataFrame.from_arrow(arrow_table)
        else:
            self.df = pl.from_arrow(arrow_table)
        return self
    
    def load_data_from_dict(self, data: Dict[str, List]) -> 'ZeroCopyPricingEngine':
        if self.backend == BackendType.CUDF:
            self.df = cudf.DataFrame(data)
        else:
            self.df = pl.DataFrame(data)
        return self
    
    def to_arrow(self) -> Any:
        if self.df is None:
            return None
        if self.backend == BackendType.CUDF:
            return self.df.to_arrow()
        else:
            return self.df.to_arrow()
    
    def to_pandas(self):
        if self.df is None:
            return None
        return self.df.to_pandas()
    
    def to_dict(self, as_series: bool = False) -> Dict[str, Any]:
        if self.df is None:
            return {}
        if self.backend == BackendType.CUDF:
            return self.df.to_dict(as_series=as_series)
        else:
            return self.df.to_dict(as_series=as_series)
    
    def apply_factor_formula(self, factor_name: str, formula: str) -> 'ZeroCopyPricingEngine':
        if self.df is None:
            raise ValueError("No data loaded")
        
        if self.backend == BackendType.CUDF:
            self.df = self.df.eval(f"{factor_name} = {formula}")
        else:
            self.df = self.df.with_columns(
                pl.Expr.lazy().eval(formula).alias(factor_name)
            )
        return self
    
    def groupby_transform(self, group_cols: List[str], target_col: str, agg_func: str, new_col_name: str = None) -> 'ZeroCopyPricingEngine':
        if self.df is None:
            raise ValueError("No data loaded")
        
        new_col_name = new_col_name or f"{target_col}_{agg_func}"
        
        if self.backend == BackendType.CUDF:
            grouped = self.df.groupby(group_cols)[target_col]
            if agg_func == "mean":
                self.df[new_col_name] = grouped.transform("mean")
            elif agg_func == "sum":
                self.df[new_col_name] = grouped.transform("sum")
            elif agg_func == "std":
                self.df[new_col_name] = grouped.transform("std")
            elif agg_func == "min":
                self.df[new_col_name] = grouped.transform("min")
            elif agg_func == "max":
                self.df[new_col_name] = grouped.transform("max")
            elif agg_func == "count":
                self.df[new_col_name] = grouped.transform("count")
            else:
                raise ValueError(f"Unsupported aggregation function: {agg_func}")
        else:
            expr = pl.col(target_col)
            if agg_func == "mean":
                agg_expr = expr.mean().over(group_cols)
            elif agg_func == "sum":
                agg_expr = expr.sum().over(group_cols)
            elif agg_func == "std":
                agg_expr = expr.std().over(group_cols)
            elif agg_func == "min":
                agg_expr = expr.min().over(group_cols)
            elif agg_func == "max":
                agg_expr = expr.max().over(group_cols)
            elif agg_func == "count":
                agg_expr = expr.count().over(group_cols)
            else:
                raise ValueError(f"Unsupported aggregation function: {agg_func}")
            
            self.df = self.df.with_columns(agg_expr.alias(new_col_name))
        
        return self
    
    def calculate_risk_zscore(self, group_cols: List[str], value_col: str, result_col: str = "risk_zscore") -> 'ZeroCopyPricingEngine':
        if self.df is None:
            raise ValueError("No data loaded")
        
        mean_col = f"_temp_mean_{int(time.time() * 1000)}"
        std_col = f"_temp_std_{int(time.time() * 1000)}"
        
        self.groupby_transform(group_cols, value_col, "mean", mean_col)
        self.groupby_transform(group_cols, value_col, "std", std_col)
        
        if self.backend == BackendType.CUDF:
            self.df[result_col] = (self.df[value_col] - self.df[mean_col]) / self.df[std_col].fillna(1)
            self.df = self.df.drop([mean_col, std_col])
        else:
            self.df = self.df.with_columns(
                ((pl.col(value_col) - pl.col(mean_col)) / pl.col(std_col).fill_nan(1)).alias(result_col)
            ).drop([mean_col, std_col])
        
        return self
    
    def apply_pricing_formula(self, formula: str, result_col: str = "final_premium") -> 'ZeroCopyPricingEngine':
        if self.df is None:
            raise ValueError("No data loaded")
        
        if self.backend == BackendType.CUDF:
            self.df = self.df.eval(f"{result_col} = {formula}")
        else:
            self.df = self.df.with_columns(
                pl.selectors.lazy().eval(formula).alias(result_col)
            )
        return self
    
    def with_column(self, name: str, expr: Any) -> 'ZeroCopyPricingEngine':
        if self.df is None:
            raise ValueError("No data loaded")
        
        if self.backend == BackendType.CUDF:
            self.df[name] = expr
        else:
            self.df = self.df.with_columns(expr.alias(name))
        return self
    
    def filter(self, condition: Any) -> 'ZeroCopyPricingEngine':
        if self.df is None:
            raise ValueError("No data loaded")
        
        if self.backend == BackendType.CUDF:
            self.df = self.df.query(condition)
        else:
            self.df = self.df.filter(condition)
        return self
    
    def compute(self):
        if self.backend == BackendType.POLARS and not isinstance(self.df, pl.DataFrame):
            self.df = self.df.collect()
        return self
    
    def get_column(self, col_name: str):
        if self.df is None:
            return None
        return self.df[col_name]
    
    def first(self) -> Dict[str, Any]:
        if self.df is None or len(self.df) == 0:
            return {}
        if self.backend == BackendType.CUDF:
            return self.df.head(1).to_dict(as_series=False)
        else:
            return self.df.head(1).to_dicts()[0]
    
    def to_records(self) -> List[Dict[str, Any]]:
        if self.df is None:
            return []
        if self.backend == BackendType.CUDF:
            return self.df.to_dict(as_series=False)
        else:
            return self.df.to_dicts()
    
    @lru_cache(maxsize=128)
    def cached_groupby_agg(self, group_cols_tuple: tuple, target_col: str, agg_func: str) -> Dict[str, float]:
        group_cols = list(group_cols_tuple)
        if self.backend == BackendType.CUDF:
            result = self.df.groupby(group_cols)[target_col].agg(agg_func).to_dict()
        else:
            result = self.df.groupby(group_cols).agg(
                pl.col(target_col).agg(agg_func)
            ).to_dict(as_series=False)
        return result
    
    def warmup(self):
        if self._warmup_complete:
            return
        
        test_data = {
            "age": [30, 40, 50],
            "premium": [1000, 2000, 3000],
            "region": ["A", "B", "A"]
        }
        
        if self.backend == BackendType.CUDF:
            test_df = cudf.DataFrame(test_data)
            _ = test_df.groupby("region")["premium"].mean()
            _ = test_df.eval("adjusted = premium * 1.1")
        else:
            test_df = pl.DataFrame(test_data)
            _ = test_df.groupby("region", maintain_order=True).agg(pl.col("premium").mean())
            _ = test_df.with_columns((pl.col("premium") * 1.1).alias("adjusted"))
        
        self._warmup_complete = True
        return self


class ModelHotLoader:
    def __init__(self, model_dir: str = "./models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self._modules: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        
    def _get_module_hash(self, code: str) -> str:
        return hashlib.md5(code.encode()).hexdigest()
    
    def load_model_from_string(self, model_name: str, code: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        module_name = f"dynamic_model_{model_name.replace('/', '_').replace('.py', '')}"
        
        spec = importlib.util.spec_from_loader(module_name, loader=None)
        if spec is None:
            raise ValueError("Could not create module spec")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        
        exec(code, module.__dict__)
        
        self._modules[model_name] = module
        self._timestamps[model_name] = time.time()
        
        available_functions = [name for name in dir(module) if callable(getattr(module, name)) and not name.startswith('_')]
        available_classes = [name for name in dir(module) if isinstance(getattr(module, name), type)]
        
        return {
            "model_name": model_name,
            "module_name": module_name,
            "loaded_at": datetime.now().isoformat(),
            "functions": available_functions,
            "classes": available_classes,
            "metadata": metadata or {},
            "code_hash": self._get_module_hash(code)
        }
    
    def load_model_from_file(self, file_path: str, model_name: Optional[str] = None) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        name = model_name or path.stem
        return self.load_model_from_string(name, code)
    
    def save_model_to_file(self, model_name: str, code: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        safe_name = model_name.replace('/', '_').replace('.py', '')
        file_path = self.model_dir / f"{safe_name}.py"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            if metadata:
                f.write(f'"""\n')
                f.write(f'Model: {model_name}\n')
                f.write(f'Created: {datetime.now().isoformat()}\n')
                for k, v in metadata.items():
                    f.write(f'{k}: {v}\n')
                f.write(f'"""\n\n')
            f.write(code)
        
        return str(file_path)
    
    def get_model(self, model_name: str):
        if model_name not in self._modules:
            file_path = self.model_dir / f"{model_name}.py"
            if file_path.exists():
                self.load_model_from_file(str(file_path), model_name)
        
        return self._modules.get(model_name)
    
    def run_model_function(self, model_name: str, func_name: str, *args, **kwargs) -> Any:
        module = self.get_model(model_name)
        if module is None:
            raise ValueError(f"Model '{model_name}' not found")
        
        func = getattr(module, func_name, None)
        if func is None:
            raise ValueError(f"Function '{func_name}' not found in model '{model_name}'")
        
        return func(*args, **kwargs)
    
    def list_models(self) -> List[Dict[str, Any]]:
        models = []
        for name, module in self._modules.items():
            models.append({
                "name": name,
                "loaded_at": self._timestamps.get(name),
                "functions": [f for f in dir(module) if callable(getattr(module, f)) and not f.startswith('_')]
            })
        
        for py_file in self.model_dir.glob("*.py"):
            name = py_file.stem
            if name not in self._modules:
                models.append({
                    "name": name,
                    "loaded": False,
                    "file_path": str(py_file)
                })
        
        return models
    
    def unload_model(self, model_name: str) -> bool:
        if model_name in self._modules:
            module_name = self._modules[model_name].__name__
            if module_name in sys.modules:
                del sys.modules[module_name]
            del self._modules[model_name]
            if model_name in self._timestamps:
                del self._timestamps[model_name]
            return True
        return False
    
    def reload_model(self, model_name: str) -> Dict[str, Any]:
        file_path = self.model_dir / f"{model_name}.py"
        if not file_path.exists():
            raise FileNotFoundError(f"Model file not found: {file_path}")
        
        self.unload_model(model_name)
        return self.load_model_from_file(str(file_path), model_name)


class HighPerformancePricingEngine:
    def __init__(self, backend: str = BackendType.AUTO):
        self.engine = ZeroCopyPricingEngine(backend)
        self.model_loader = ModelHotLoader()
        self.engine.warmup()
    
    @property
    def backend_info(self):
        return self.engine.get_backend_info()
    
    def load_single_policy(self, policy_data: Dict[str, Any]) -> 'HighPerformancePricingEngine':
        self.engine.load_data_from_records([policy_data])
        return self
    
    def load_batch_policies(self, policies: List[Dict[str, Any]]) -> 'HighPerformancePricingEngine':
        self.engine.load_data_from_records(policies)
        return self
    
    def calculate_premium_fast(
        self,
        base_rate: float = 0.005,
        risk_multipliers: Optional[Dict[str, float]] = None,
        discount_factors: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        
        if self.engine.df is None:
            raise ValueError("No policy data loaded")
        
        risk_multipliers = risk_multipliers or {}
        discount_factors = discount_factors or {}
        
        if self.engine.backend == BackendType.CUDF:
            df = self.engine.df
            df['base_premium'] = df['insured_amount'] * base_rate
            
            final_multiplier = 1.0
            for col, multiplier in risk_multipliers.items():
                if col in df.columns:
                    final_multiplier *= multiplier
            
            for col, discount in discount_factors.items():
                if col in df.columns:
                    final_multiplier *= (1 - discount)
            
            df['risk_adjusted_premium'] = df['base_premium'] * final_multiplier
            
            discount_rate = df['safe_driving_score'] / 100 * 0.15
            df['ubi_discount'] = discount_rate
            df['final_premium'] = df['risk_adjusted_premium'] * (1 - discount_rate)
        else:
            df = self.engine.df
            df = df.with_columns(
                (pl.col('insured_amount') * base_rate).alias('base_premium')
            )
            
            risk_expr = pl.lit(1.0)
            for col, multiplier in risk_multipliers.items():
                if col in df.columns:
                    risk_expr *= pl.col(col) * multiplier + (1 - multiplier)
            
            df = df.with_columns(risk_expr.alias('risk_multiplier'))
            
            discount_expr = pl.lit(1.0)
            for col, discount in discount_factors.items():
                if col in df.columns:
                    discount_expr *= (1 - pl.col(col) * discount)
            
            df = df.with_columns(discount_expr.alias('discount_factor'))
            
            df = df.with_columns(
                (pl.col('base_premium') * pl.col('risk_multiplier') * pl.col('discount_factor')).alias('final_premium')
            )
            
            self.engine.df = df
        
        result = self.engine.first()
        elapsed = (time.perf_counter() - start_time) * 1000
        
        return {
            "result": result,
            "latency_ms": round(elapsed, 3),
            "backend": self.engine.backend
        }
    
    def run_custom_pricing_model(
        self,
        model_name: str,
        func_name: str = "calculate_premium",
        **kwargs
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        
        engine = self.engine
        result = self.model_loader.run_model_function(model_name, func_name, engine=engine, **kwargs)
        
        elapsed = (time.perf_counter() - start_time) * 1000
        
        return {
            "result": result,
            "model_name": model_name,
            "function": func_name,
            "latency_ms": round(elapsed, 3),
            "backend": self.engine.backend
        }
    
    def batch_calculate_premium(self) -> Dict[str, Any]:
        start_time = time.perf_counter()
        
        if self.engine.df is None:
            raise ValueError("No policy data loaded")
        
        row_count = len(self.engine.df)
        
        if self.engine.backend == BackendType.CUDF:
            df = self.engine.df
            df['base_premium'] = df['insured_amount'] * 0.005
            df['final_premium'] = df['base_premium']
        else:
            df = self.engine.df
            df = df.with_columns(
                (pl.col('insured_amount') * 0.005).alias('base_premium'),
                pl.col('insured_amount').alias('final_premium')
            )
            self.engine.df = df
        
        elapsed = (time.perf_counter() - start_time) * 1000
        per_row_latency = elapsed / row_count if row_count > 0 else 0
        
        return {
            "row_count": row_count,
            "total_latency_ms": round(elapsed, 3),
            "per_row_latency_ms": round(per_row_latency, 5),
            "backend": self.engine.backend,
            "gpu_accelerated": self.engine.backend == BackendType.CUDF
        }
    
    def list_models(self):
        return self.model_loader.list_models()
    
    def load_model(self, code: str, model_name: str, metadata: Optional[Dict[str, Any]] = None):
        return self.model_loader.load_model_from_string(model_name, code, metadata)
    
    def save_model(self, model_name: str, code: str, metadata: Optional[Dict[str, Any]] = None):
        return self.model_loader.save_model_to_file(model_name, code, metadata)
