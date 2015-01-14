from setuptools import setup
from bitnomon import __version__

setup(
    name='bitnomon',
    version=__version__,
    description='Bitcoin Node Monitor',
    long_description='[placeholder]',
    author='Jacob Welsh',
    author_email='jacob@welshcomputing.com',
    license='MIT',
    classifiers=[],
    packages=['bitnomon'],
    requires=[
        'pyqtgraph',
        'rrdtool',
    ],
    package_data={
        'bitnomon': [],
    },
    entry_points={
        'gui_scripts': [
            'bitnomon=bitnomon.main:main',
        ],
    },
    test_suite='tests',
    test_loader='run_unit_tests:Loader',
)
