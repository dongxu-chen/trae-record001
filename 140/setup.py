from setuptools import setup, find_packages

setup(
    name="seqalign",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "biopython>=1.79",
        "numpy>=1.21.0",
        "matplotlib>=3.4.0",
    ],
    author="Bioinformatics Developer",
    description="A biological sequence alignment analysis package",
    keywords="bioinformatics sequence-alignment",
)
