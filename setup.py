from setuptools import setup

setup(
    name='bitnomon',
    version='0.1',
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
)
