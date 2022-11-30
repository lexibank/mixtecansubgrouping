from setuptools import setup


setup(
    name='cldfbench_mixtecansubgrouping',
    py_modules=['cldfbench_mixtecansubgrouping'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'cldfbench.dataset': [
            'mixtecansubgrouping=cldfbench_mixtecansubgrouping:Dataset',
        ],
    },
    install_requires=[
        'pycldf>=1.24',
        'pylexibank',
        'cldfbench',
        'cldfviz',
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
