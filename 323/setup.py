from setuptools import setup, find_packages

setup(
    name="k8s-resource-recommender",
    version="1.0.0",
    description="Kubernetes资源推荐工具 - 基于VPA算法和Prometheus数据的智能资源分析",
    author="K8s Resource Recommender",
    packages=find_packages(),
    install_requires=[
        "prometheus-api-client>=0.5.0",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "scipy>=1.10.0",
        "click>=8.1.0",
        "PyYAML>=6.0",
        "python-dateutil>=2.8.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "k8s-resource-recommender=k8s_resource_recommender.cli:main",
        ],
    },
    python_requires=">=3.9",
)
