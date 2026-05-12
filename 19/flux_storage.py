"""
HDF5 通量存储模块
支持：
- 批量写入辐射通量数据
- 多列、多波段、多层数据存储
- 增量写入和批量读取
"""

import numpy as np

try:
    import h5py
    H5PY_AVAILABLE = True
except ImportError:
    H5PY_AVAILABLE = False


class FluxStorage:
    """
    HDF5 格式的通量存储管理类
    """

    def __init__(self, file_path, mode='a', compression='gzip', compression_opts=4):
        """
        参数:
        - file_path: HDF5 文件路径
        - mode: 'r' 读取, 'w' 覆盖写入, 'a' 追加
        - compression: 压缩方式 ('gzip', 'lzf', 或 None)
        - compression_opts: 压缩级别 (1-9)
        """
        if not H5PY_AVAILABLE:
            raise ImportError("h5py is required for FluxStorage")

        self.file_path = file_path
        self.mode = mode
        self.compression = compression
        self.compression_opts = compression_opts
        self.file = None
        self._open()

    def _open(self):
        """打开 HDF5 文件"""
        if self.file is None:
            self.file = h5py.File(self.file_path, self.mode)

    def close(self):
        """关闭 HDF5 文件"""
        if self.file is not None:
            self.file.close()
            self.file = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _ensure_group(self, group_path):
        """确保组存在"""
        if group_path in self.file:
            return self.file[group_path]
        return self.file.create_group(group_path)

    def _create_or_resize_dataset(self, group, name, data, maxshape=None):
        """
        创建或扩展数据集
        """
        data = np.asarray(data)

        if name in group:
            dset = group[name]
            old_shape = dset.shape
            new_shape = list(old_shape)
            new_shape[0] = old_shape[0] + data.shape[0]

            dset.resize(new_shape)
            dset[old_shape[0]:] = data
        else:
            if maxshape is None:
                maxshape = (None,) + data.shape[1:]

            chunks = True
            if data.ndim >= 1:
                chunks = (min(100, data.shape[0]),) + data.shape[1:]

            compression_kwargs = {}
            if self.compression:
                compression_kwargs['compression'] = self.compression
                compression_kwargs['compression_opts'] = self.compression_opts

            dset = group.create_dataset(
                name,
                data=data,
                maxshape=maxshape,
                chunks=chunks,
                **compression_kwargs
            )

        return dset

    def save_atmosphere_profile(self, profile, group_name='profiles'):
        """
        保存大气廓线数据

        参数:
        - profile: 大气廓线字典
        - group_name: 组名
        """
        group = self._ensure_group(group_name)

        for key, value in profile.items():
            if isinstance(value, np.ndarray) or isinstance(value, list):
                self._create_or_resize_dataset(group, key, np.asarray(value))
            else:
                group.attrs[key] = value

    def save_fluxes(self, fluxes, prefix='step_', group_name='fluxes'):
        """
        保存辐射通量数据

        参数:
        - fluxes: 通量字典，包含 downward_flux, upward_flux, net_flux 等
        - prefix: 数据集名前缀
        - group_name: 组名
        """
        group = self._ensure_group(group_name)

        for key, value in fluxes.items():
            if isinstance(value, np.ndarray) or hasattr(value, '__array__'):
                data = np.asarray(value)
                if data.ndim == 0:
                    group.attrs[f'{prefix}{key}'] = float(data)
                else:
                    self._create_or_resize_dataset(group, f'{prefix}{key}', data)
            else:
                group.attrs[f'{prefix}{key}'] = value

    def save_radiation_results(self, results, timestep=None, group_name='radiation'):
        """
        保存完整的辐射计算结果

        参数:
        - results: 辐射计算结果字典
        - timestep: 时间步索引
        - group_name: 组名
        """
        prefix = f't{timestep:06d}_' if timestep is not None else ''

        if 'shortwave' in results:
            sw_group = self._ensure_group(f'{group_name}/shortwave')
            self.save_fluxes(results['shortwave'], prefix=prefix, group_name=f'{group_name}/shortwave')

        if 'longwave' in results:
            lw_group = self._ensure_group(f'{group_name}/longwave')
            self.save_fluxes(results['longwave'], prefix=prefix, group_name=f'{group_name}/longwave')

        if 'net' in results:
            net_group = self._ensure_group(f'{group_name}/net')
            self.save_fluxes(results['net'], prefix=prefix, group_name=f'{group_name}/net')

        if 'cloud_forcing' in results and results['cloud_forcing'] is not None:
            cf_group = self._ensure_group(f'{group_name}/cloud_forcing')
            self.save_fluxes(results['cloud_forcing'], prefix=prefix, group_name=f'{group_name}/cloud_forcing')

        if 'aerosol_forcing' in results and results['aerosol_forcing'] is not None:
            af_group = self._ensure_group(f'{group_name}/aerosol_forcing')
            self.save_fluxes(results['aerosol_forcing'], prefix=prefix, group_name=f'{group_name}/aerosol_forcing')

        if timestep is not None:
            group = self._ensure_group(group_name)
            if 'timesteps' not in group:
                group.create_dataset('timesteps', data=[timestep], maxshape=(None,), chunks=(100,))
            else:
                ts_dset = group['timesteps']
                ts_dset.resize((ts_dset.shape[0] + 1,))
                ts_dset[-1] = timestep

    def save_metadata(self, metadata, group_name='metadata'):
        """
        保存元数据

        参数:
        - metadata: 元数据字典
        - group_name: 组名
        """
        group = self._ensure_group(group_name)

        for key, value in metadata.items():
            if isinstance(value, np.ndarray) or isinstance(value, list):
                if key in group:
                    del group[key]
                group.create_dataset(key, data=np.asarray(value))
            else:
                group.attrs[key] = value

    def load_metadata(self, group_name='metadata'):
        """
        加载元数据

        参数:
        - group_name: 组名

        返回:
        - 元数据字典
        """
        if group_name not in self.file:
            return {}

        group = self.file[group_name]
        metadata = {}

        for key in group.attrs:
            metadata[key] = group.attrs[key]

        for dset_name in group:
            metadata[dset_name] = group[dset_name][:]

        return metadata

    def load_fluxes(self, group_name='fluxes', prefix='', indices=None):
        """
        加载通量数据

        参数:
        - group_name: 组名
        - prefix: 数据集名前缀
        - indices: 要读取的时间步索引范围 (start, end)

        返回:
        - 通量字典
        """
        if group_name not in self.file:
            return {}

        group = self.file[group_name]
        fluxes = {}

        for dset_name in group:
            if prefix and not dset_name.startswith(prefix):
                continue

            key = dset_name[len(prefix):] if prefix else dset_name

            if isinstance(group[dset_name], h5py.Dataset):
                dset = group[dset_name]
                if indices is not None:
                    start, end = indices
                    fluxes[key] = dset[start:end]
                else:
                    fluxes[key] = dset[:]

        return fluxes

    def load_radiation_results(self, timestep=None, group_name='radiation'):
        """
        加载辐射计算结果

        参数:
        - timestep: 时间步索引，如果为 None 则加载所有
        - group_name: 组名

        返回:
        - 辐射结果字典
        """
        if group_name not in self.file:
            return {}

        results = {}
        prefix = f't{timestep:06d}_' if timestep is not None else ''

        for sub_group_name in ['shortwave', 'longwave', 'net', 'cloud_forcing', 'aerosol_forcing']:
            full_path = f'{group_name}/{sub_group_name}'
            if full_path in self.file:
                results[sub_group_name] = self.load_fluxes(full_path, prefix=prefix)

        return results

    def list_contents(self, group_name='/'):
        """
        列出文件内容
        """
        if group_name not in self.file:
            return []

        group = self.file[group_name]
        contents = []

        for name in group:
            item = group[name]
            if isinstance(item, h5py.Group):
                contents.append(f'[GROUP] {name}')
            else:
                contents.append(f'[DATASET] {name} shape={item.shape} dtype={item.dtype}')

        return contents

    def get_shape(self, dataset_path):
        """
        获取数据集形状
        """
        if dataset_path in self.file:
            return self.file[dataset_path].shape
        return None

    def print_info(self):
        """打印文件信息"""
        print(f"HDF5 File: {self.file_path}")
        print(f"File mode: {self.mode}")
        print()

        def print_group(name, obj, indent=0):
            prefix = '  ' * indent
            if isinstance(obj, h5py.Group):
                print(f"{prefix}Group: {name}")
                for attr_name, attr_val in obj.attrs.items():
                    print(f"{prefix}  Attr: {attr_name} = {attr_val}")
            else:
                print(f"{prefix}Dataset: {name}")
                print(f"{prefix}  Shape: {obj.shape}, Dtype: {obj.dtype}")
                if obj.chunks:
                    print(f"{prefix}  Chunks: {obj.chunks}")
                if obj.compression:
                    print(f"{prefix}  Compression: {obj.compression} (level={obj.compression_opts})")
                for attr_name, attr_val in obj.attrs.items():
                    print(f"{prefix}  Attr: {attr_name} = {attr_val}")

        self.file.visititems(print_group)


class BatchFluxWriter:
    """
    批量通量写入器，支持缓存和批量写入
    """

    def __init__(self, storage, batch_size=100):
        """
        参数:
        - storage: FluxStorage 实例
        - batch_size: 批量大小
        """
        self.storage = storage
        self.batch_size = batch_size
        self.cache = []
        self.current_count = 0

    def add_results(self, results, timestep=None):
        """
        添加结果到缓存
        """
        self.cache.append((results, timestep))
        self.current_count += 1

        if self.current_count >= self.batch_size:
            self.flush()

    def flush(self):
        """
        将缓存写入文件
        """
        if not self.cache:
            return

        for results, timestep in self.cache:
            self.storage.save_radiation_results(results, timestep=timestep)

        self.cache = []
        self.current_count = 0

    def close(self):
        """
        关闭（刷新并关闭存储）
        """
        self.flush()
        self.storage.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
