from setuptools import setup, find_packages

setup(
    name="fenics-pde-solver",
    version="0.1.0",
    description="偏微分方程有限元求解器 - 基于FEniCS",
    author="FEniCS PDE Solver Team",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.21.0",
        "matplotlib>=3.4.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Mathematics",
    ],
)
