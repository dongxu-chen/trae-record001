from setuptools import setup, find_packages

setup(
    name='cd_tool',
    version='0.1.0',
    description='Remote Sensing Image Change Detection Toolbox',
    author='Change Detection Team',
    packages=find_packages(),
    install_requires=[
        'torch>=1.9.0',
        'torchvision>=0.10.0',
        'opencv-python>=4.5.0',
        'numpy>=1.19.0',
        'pillow>=8.0.0',
        'scikit-learn>=0.24.0',
        'matplotlib>=3.3.0',
        'tqdm>=4.60.0'
    ],
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Scientific/Engineering :: Image Processing'
    ],
    keywords='change detection remote sensing deep learning pytorch'
)
