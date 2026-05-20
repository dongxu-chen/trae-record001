FROM pangeo/pangeo-notebook:latest

LABEL maintainer="Climate Analysis Team"
LABEL description="Pangeo-based Climate Analysis Platform Notebook Image"

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    netcdf-bin \
    hdf5-tools \
    && rm -rf /var/lib/apt/lists/*

USER ${NB_USER}

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

RUN pip install --no-cache-dir \
    dask-gateway \
    s3fs \
    zarr \
    fsspec \
    gcsfs \
    adlfs \
    kerchunk \
    hvplot \
    geoviews \
    datashader \
    panel \
    intake \
    intake-esm \
    intake-xarray

RUN jupyter labextension install @jupyter-widgets/jupyterlab-manager dask-labextension

COPY --chown=${NB_UID}:${NB_GID} climate_analysis /tmp/climate_analysis
RUN cd /tmp && pip install --no-cache-dir -e climate_analysis && \
    rm -rf /tmp/climate_analysis

RUN fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

WORKDIR /home/${NB_USER}
