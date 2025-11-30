# setup.py
from setuptools import find_packages, setup

setup(
    name="gym-equipment-directory",
    version="0.0.1",
    packages=find_packages(include=["app", "app.*", "configs", "configs.*"]),
    include_package_data=True,
    package_data={"configs": ["municipal/*.yaml"]},
)
