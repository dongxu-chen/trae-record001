from setuptools import setup, find_packages

setup(
    name="climate_analysis",
    version="0.1.0",
    description="气候模式数据分析库 - Xarray + Dask + NetCDF科学计算工具",
    author="Climate Analysis Team",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "xarray>=2023.1.0",
        "dask>=2023.1.0",
        "netCDF4>=1.6.0",
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "matplotlib>=3.7.0",
        "cartopy>=0.21.0",
        "scikit-learn>=1.2.0",
        "pandas>=2.0.0",
        "cfgrib>=0.9.10",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Atmospheric Science",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
