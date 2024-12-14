from setuptools import setup, find_packages


def read_requirements():
    with open("requirements.txt") as f:
        return f.read().splitlines()


packages = find_packages(".", exclude=["*.test", "*.test.*"])


setup(
    name="econuy-extras",
    version="0.0.1",
    url="https://github.com/rxavier/econuy-extras",
    author="Rafael Xavier",
    author_email="rxaviermontero@gmail.com",
    description="econuy extras",
    packages=packages,
    install_requires=read_requirements(),
    python_requires=">=3.6",
)
