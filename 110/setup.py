from setuptools import setup, find_packages

setup(
    name="cfdmesh",
    version="0.1.0",
    description="CFD前处理工具 - 网格读取、质量检查与格式转换",
    author="CFD Mesh Tools",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.21.0",
        "meshio>=5.0.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "cfdmesh=cfdmesh.cli:main",
        ],
    },
)
