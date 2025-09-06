# setup.py
from setuptools import setup, find_packages

setup(
    name="gym-equipment-directory",
    version="0.0.1",
    packages=find_packages(include=["app", "app.*"]),
)
