from setuptools import setup, find_packages

setup(
    name='pyexch',
    version='0.1',
    packages=find_packages(),
    install_requires=[],
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
    url='https://github.com/brianddk/pyexchange',
    license='MIT',
)
