from pathlib import Path

from setuptools import find_namespace_packages, setup  # type: ignore

setup(
    name="cleaner_ratelimit",
    version="0.1.0",
    url="https://github.com/cleaner-bot/cleaner-ratelimit",
    author="Leo Developer",
    author_email="git@leodev.xyz",
    description="ratelimit library for fastapi",
    install_requires=Path("requirements.txt").read_text().splitlines(),
    packages=find_namespace_packages(include=["cleaner_ratelimit*"]),
    package_data={"cleaner_ratelimit": ["py.typed"]},
)
