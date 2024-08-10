from setuptools import setup, find_packages
import json


with open("metadata.json", encoding="utf-8") as fp:
    metadata = json.load(fp)


setup(
    name='lexibank_mixtecansubgrouping',
    description=metadata["title"],
    py_modules=['lexibank_mixtecansubgrouping'],
    license=metadata.get("license", ""),
    url=metadata.get("url", ""),
    include_package_data=True,
    packages=find_packages(where="."),
    zip_safe=False,
    entry_points={
        'cldfbench.dataset': [
            'mixtecansubgrouping=lexibank_mixtecansubgrouping:Dataset',
        ],
        'cldfbench.commands': [
            'mixtecansubgrouping=mixtecansubgroupingcommands',
        ],
    },
    install_requires=[
        'pycldf>=1.24',
        'pylexibank',
        'cldfbench',
        'cldfviz',
        'python-nexus',
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
