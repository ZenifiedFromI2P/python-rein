"""
A decentralized professional services marketplace.
"""
from setuptools import find_packages, setup

dependencies = ['click', 'requests>=2.10', 'flask-wtf', 'python-bitcoinlib', 'sqlalchemy', 'pysocks']

setup(
    name='rein',
    version='0.2.0',
    url='https://github.com/ReinProject/python-rein',
    license='BSD',
    author='David Sterry',
    author_email='davids@exchb.com',
    description='Decentralized freelance market',
    long_description=__doc__,
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    package_data={'': ['rein/html/*']},
    install_requires=dependencies,
    entry_points={
        'console_scripts': [
            'rein = rein.cli:cli',
        ],
    },
    classifiers=[
         'Development Status :: 3 - Alpha',
        # 'Development Status :: 4 - Beta',
        # 'Development Status :: 5 - Production/Stable',
        # 'Development Status :: 6 - Mature',
        # 'Development Status :: 7 - Inactive',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Operating System :: Unix',
        'Operating System :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
