from setuptools import setup, find_namespace_packages  # type: ignore


def parse_requirements_file(path):
    with open(path) as file:
        lines = file.read().splitlines()
    dependencies = (x.strip() for x in lines)
    return [x for x in dependencies if x and not x.startswith("#")]


setup(
    name="cleaner_ratelimit",
    version="0.1.0",
    url="https://github.com/cleaner-bot/cleaner-ratelimit",
    author="Leo Developer",
    author_email="git@leodev.xyz",
    description="ratelimit library for fastapi",
    requires=parse_requirements_file("requirements.txt"),
    packages=find_namespace_packages(include=["cleaner_ratelimit*"]),
    package_data={"cleaner_ratelimit": ["py.typed"]},
)
