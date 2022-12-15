from setuptools import setup


setup(
    name='lexibank_mixtecansubgrouping',
    py_modules=['lexibank_mixtecansubgrouping'],
    include_package_data=True,
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
