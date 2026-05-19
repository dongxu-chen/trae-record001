from setuptools import setup, find_packages

setup(
    name="seisprocessor",
    version="0.1.0",
    description="地震波形处理工具包 - 基于ObsPy和Matplotlib的Python科学计算库",
    author="SeisProcessor Team",
    packages=find_packages(),
    install_requires=[
        "obspy>=1.4.0",
        "matplotlib>=3.5.0",
        "numpy>=1.21.0",
        "scipy>=1.7.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Physics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
