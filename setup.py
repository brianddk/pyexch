from setuptools import setup, find_packages

setup(
    name='pyexch',
    version='0.0.2',
    packages=[
        'pyexch'
    ],
    python_requires='>=3.8.2',    
    install_requires=[
        'coinbase>=2.1.0',
        'coinbase-advanced-py>=1.2.0',
        'trezor>=0.13.8',
        'pyjson5>=1.6.6',
    ],
    entry_points={
        'console_scripts': [
            'pyexch = pyexch.pyexch:main'
        ]
    },
    author='brianddk',
    author_email='brianddk@users.noreply.github.com',
    description='Python CLI Exchange Rest Client',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/brianddk/pyexch',
    license='Apache-2.0',
)
