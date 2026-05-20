import xarray as xr
import numpy as np
from typing import Optional, Dict, List, Union, Any
import logging
import fsspec
import zarr
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import s3fs
    S3FS_AVAILABLE = True
except ImportError:
    S3FS_AVAILABLE = False
    logger.warning("s3fs not installed. S3 functionality will be limited.")

try:
    import intake
    import intake_esm
    INTAKE_AVAILABLE = True
except ImportError:
    INTAKE_AVAILABLE = False
    logger.warning("intake not installed. ESM catalog functionality will be limited.")


class CloudDataStore:
    def __init__(
        self,
        bucket: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        anon: bool = True,
        **kwargs
    ):
        self.bucket = bucket
        self.endpoint_url = endpoint_url
        self.anon = anon
        self.s3_kwargs = kwargs
        self.fs = None
        self._init_filesystem()

    def _init_filesystem(self):
        if S3FS_AVAILABLE:
            self.fs = s3fs.S3FileSystem(
                anon=self.anon,
                endpoint_url=self.endpoint_url,
                **self.s3_kwargs
            )
        else:
            logger.warning("s3fs not available. Using local filesystem only.")
            self.fs = fsspec.filesystem('file')

    def open_zarr(
        self,
        path: str,
        chunks: Optional[Dict[str, int]] = None,
        consolidated: bool = True,
        **kwargs
    ) -> xr.Dataset:
        logger.info(f"Opening Zarr store: {path}")

        if path.startswith('s3://') or self.bucket:
            full_path = path if path.startswith('s3://') else f"s3://{self.bucket}/{path}"
            mapper = s3fs.S3Map(full_path, s3=self.fs)
        else:
            mapper = path

        ds = xr.open_zarr(
            mapper,
            consolidated=consolidated,
            chunks=chunks or {},
            **kwargs
        )

        logger.info(f"Dataset loaded with dimensions: {dict(ds.dims)}")
        return ds

    def open_netcdf(
        self,
        path: str,
        chunks: Optional[Dict[str, int]] = None,
        **kwargs
    ) -> xr.Dataset:
        logger.info(f"Opening NetCDF from cloud: {path}")

        if path.startswith('s3://') or self.bucket:
            full_path = path if path.startswith('s3://') else f"s3://{self.bucket}/{path}"
            f = self.fs.open(full_path)
        else:
            f = path

        ds = xr.open_dataset(f, chunks=chunks or {}, **kwargs)

        logger.info(f"Dataset loaded with dimensions: {dict(ds.dims)}")
        return ds

    def to_zarr(
        self,
        ds: xr.Dataset,
        path: str,
        mode: str = "w",
        consolidated: bool = True,
        **kwargs
    ):
        logger.info(f"Writing dataset to Zarr store: {path}")

        if path.startswith('s3://') or self.bucket:
            full_path = path if path.startswith('s3://') else f"s3://{self.bucket}/{path}"
            mapper = s3fs.S3Map(full_path, s3=self.fs)
        else:
            mapper = path

        ds.to_zarr(
            mapper,
            mode=mode,
            consolidated=consolidated,
            **kwargs
        )

        logger.info("Zarr store written successfully")

    def list_objects(self, prefix: str = "") -> List[str]:
        if not self.fs:
            raise RuntimeError("Filesystem not initialized")

        full_prefix = f"{self.bucket}/{prefix}" if self.bucket else prefix
        return self.fs.ls(full_prefix)

    def exists(self, path: str) -> bool:
        if path.startswith('s3://') or self.bucket:
            full_path = path if path.startswith('s3://') else f"s3://{self.bucket}/{path}"
            return self.fs.exists(full_path)
        return Path(path).exists()


class CMIP6Catalog:
    def __init__(self, catalog_url: Optional[str] = None):
        if not INTAKE_AVAILABLE:
            raise ImportError("intake-esm is required for CMIP6 catalog functionality")

        self.catalog_url = catalog_url or "https://storage.googleapis.com/cmip6/pangeo-cmip6.json"
        self.catalog = None
        self._load_catalog()

    def _load_catalog(self):
        logger.info(f"Loading CMIP6 catalog from: {self.catalog_url}")
        self.catalog = intake.open_esm_datastore(self.catalog_url)
        logger.info(f"Catalog loaded with {len(self.catalog.df)} entries")

    def search(
        self,
        experiment_id: Optional[Union[str, List[str]]] = None,
        variable_id: Optional[Union[str, List[str]]] = None,
        source_id: Optional[Union[str, List[str]]] = None,
        member_id: Optional[Union[str, List[str]]] = None,
        table_id: Optional[str] = None,
        **kwargs
    ) -> intake_esm.esm_datastore:
        search_kwargs = {}
        if experiment_id:
            search_kwargs["experiment_id"] = experiment_id
        if variable_id:
            search_kwargs["variable_id"] = variable_id
        if source_id:
            search_kwargs["source_id"] = source_id
        if member_id:
            search_kwargs["member_id"] = member_id
        if table_id:
            search_kwargs["table_id"] = table_id
        search_kwargs.update(kwargs)

        logger.info(f"Searching catalog with: {search_kwargs}")
        return self.catalog.search(**search_kwargs)

    def to_dataset_dict(
        self,
        catalog_subset: intake_esm.esm_datastore,
        **kwargs
    ) -> Dict[str, xr.Dataset]:
        logger.info("Loading datasets from catalog subset")
        dset_dict = catalog_subset.to_dataset_dict(**kwargs)
        logger.info(f"Loaded {len(dset_dict)} datasets")
        return dset_dict

    def unique_values(self, column: str) -> List[str]:
        return sorted(self.catalog.df[column].unique().tolist())


class DaskGatewayCluster:
    def __init__(
        self,
        address: Optional[str] = None,
        proxy_address: Optional[str] = None,
        auth: Optional[Any] = None,
        **kwargs
    ):
        try:
            from dask_gateway import Gateway
        except ImportError:
            raise ImportError("dask-gateway is required for Dask Gateway functionality")

        self.gateway = Gateway(
            address=address,
            proxy_address=proxy_address,
            auth=auth,
            **kwargs
        )
        self.cluster = None
        self.client = None

    def new_cluster(
        self,
        worker_cores: int = 2,
        worker_memory: str = "8G",
        worker_count: int = 4,
        autoscale: bool = True,
        **kwargs
    ):
        logger.info(f"Creating new Dask cluster: {worker_count} workers x {worker_cores} cores x {worker_memory}")

        options = self.gateway.cluster_options()
        options.worker_cores = worker_cores
        options.worker_memory = worker_memory
        options.worker_count = worker_count

        self.cluster = self.gateway.new_cluster(options, **kwargs)

        if autoscale:
            self.cluster.adapt(minimum=1, maximum=100)

        logger.info(f"Cluster created: {self.cluster.name}")
        return self.cluster

    def connect(self, cluster_name: str):
        logger.info(f"Connecting to existing cluster: {cluster_name}")
        self.cluster = self.gateway.connect(cluster_name)
        return self.cluster

    def get_client(self):
        if not self.cluster:
            raise RuntimeError("No cluster created. Call new_cluster() or connect() first.")

        from dask.distributed import Client
        self.client = Client(self.cluster)
        logger.info(f"Dask client connected: {self.client}")
        return self.client

    def list_clusters(self):
        return self.gateway.list_clusters()

    def stop_cluster(self, cluster_name: Optional[str] = None):
        if cluster_name:
            self.gateway.stop_cluster(cluster_name)
            logger.info(f"Stopped cluster: {cluster_name}")
        elif self.cluster:
            self.cluster.shutdown()
            logger.info("Stopped current cluster")
        else:
            logger.warning("No cluster to stop")

    def scale(self, n_workers: int):
        if not self.cluster:
            raise RuntimeError("No cluster created")
        self.cluster.scale(n_workers)
        logger.info(f"Scaled cluster to {n_workers} workers")


def create_s3_store(
    bucket: str,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    endpoint_url: Optional[str] = None,
    region_name: Optional[str] = None,
    anon: bool = False
) -> CloudDataStore:
    return CloudDataStore(
        bucket=bucket,
        endpoint_url=endpoint_url,
        anon=anon,
        key=aws_access_key_id,
        secret=aws_secret_access_key,
        region_name=region_name
    )


def list_pangeo_datasets() -> Dict[str, str]:
    datasets = {
        "CMIP6": "https://storage.googleapis.com/cmip6/pangeo-cmip6.json",
        "ERA5": "gs://pangeo-era5/reanalysis/spatial-analysis",
        "GPCP": "s3://pangeo-data/gpcp/",
        "SST": "s3://pangeo-data/noaa_oisst/",
    }
    return datasets


def create_kerchunk_index(
    files: List[str],
    output_path: str,
    remote_protocol: str = "s3",
    **kwargs
):
    try:
        import kerchunk
        from kerchunk.hdf import SingleHdf5ToZarr
        from kerchunk.combine import MultiZarrToZarr
    except ImportError:
        raise ImportError("kerchunk is required for creating indices")

    logger.info(f"Creating Kerchunk index for {len(files)} files")

    indices = []
    for f in files:
        logger.debug(f"Processing: {f}")
        h5chunks = SingleHdf5ToZarr(f, **kwargs)
        indices.append(h5chunks.translate())

    mzz = MultiZarrToZarr(
        indices,
        remote_protocol=remote_protocol,
        **kwargs
    )

    mzz.translate(output_path)
    logger.info(f"Kerchunk index written to: {output_path}")
    return output_path
