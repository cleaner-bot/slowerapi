from pathlib import Path

from setuptools import find_namespace_packages, setup  # type: ignore

setup(
    name="slowerapi",
    version="0.2.0",
    url="https://github.com/cleaner-bot/slowerapi",
    author="Leo Developer",
    author_email="git@leodev.xyz",
    description="ratelimit library for fastapi",
    install_requires=Path("requirements.txt").read_text().splitlines(),
    packages=find_namespace_packages(include=["slowerapi*"]),
    package_data={"slowerapi": ["py.typed"]},
)
