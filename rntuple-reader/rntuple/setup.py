"""A setuptools for rntuple-reader project
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from os import path
# io.open is needed for projects that support Python 2.7
# It ensures open() defaults to text mode with universal newlines,
# and accepts an argument to specify the text encoding
# Python 3 only projects can skip this import
from io import open

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(

    name='rntuple-reader',  # Required

    version='1.3.1',  # Required

    description='A sample Python project',  # Optional

    long_description=long_description,  # Optional
    
    long_description_content_type='text/markdown',  # Optional

    url='https://github.com/pypa/rntuple-reader',  # Optional

    author='Oksana Shadura',  # Optional

    author_email='ksu.shadura@gmail.com',  # Optional

    classifiers=[  # Optional
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],

    keywords='rntuple hep root file format',  # Optional

    ##package_dir={'': 'src'},  # Optional

    ##packages=find_packages(where='src'),  # Required

    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, <4',

    install_requires=['numpy'],  # Optional

    extras_require={  # Optional
        'test': ['pytest'],
    },

    project_urls={  # Optional
        'Bug Reports': 'https://github.com/pypa/rntuple-reader/issues',
        'Funding': 'https://donate.pypi.org',
        'Say Thanks!': 'http://saythanks.io/to/example',
        'Source': 'https://github.com/pypa/rntuple-reader/',
    },
)