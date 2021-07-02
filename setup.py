import os
import json

from setuptools import setup, find_packages
from typing import Union, Optional, List


def reqs_pipfile_lock(pipfile_lock: Union[str, os.PathLike, None] = None,
                      exclude: Optional[List[str]] = None):
    if exclude is None:
        exclude = []
    if pipfile_lock is None:
        pipfile_lock = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "Pipfile.lock"
        )
    lock_data = json.load(open(pipfile_lock))
    return [package_name for package_name in
            lock_data.get("default", {}).keys() if package_name not in exclude]


packages = find_packages(".", exclude=["*.test", "*.test.*"])
pipfile_lock_requirements = reqs_pipfile_lock()

here = os.path.abspath(os.path.dirname(__file__))

setup(
    name='econuy-extras',
    version='0.0.1',
    url='https://github.com/rxavier/econuy-extras',
    author='Rafael Xavier',
    author_email='rxaviermontero@gmail.com',
    description='econuy extras',
    packages=packages,
    install_requires=pipfile_lock_requirements,
    python_requires=">=3.6"
)