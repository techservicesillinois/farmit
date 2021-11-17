from setuptools import setup, find_packages


def version():
    from setuptools_scm.version import get_local_dirty_tag

    def clean_scheme(version):
        # Disable local scheme by default since it is not supported
        # by PyPI (See PEP 440). If code is not committed add +dirty
        # to version to prevent upload to either PyPI or test PyPI.
        return get_local_dirty_tag(version) if version.dirty else ''

    return {'local_scheme': clean_scheme}


setup(
    name="farmit",
    use_scm_version=version,
    setup_requires=['setuptools_scm'],
    author="David D. Riddle",
    author_email="securitysupport@illinois.edu",
    description="Fully Automated Release Management tool",
    long_description_content_type="text/markdown",
    url="https://github.com/techservicesillinois/farmit",
    packages=find_packages('src', exclude=['tests']),
    package_dir={'': 'src'},
    extras_require={
        'testing': ['pytest'],
    },
    install_requires=[
        "GitPython",
        "pydriller",
        "setuptools_scm",
    ],
    entry_points={
        'console_scripts': [
            'farmit = farmit:_main',
        ],
    },
    include_package_data=True,
    classifiers=[
        #  'Development Status :: 4 - Beta',
        "Operating System :: OS Independent",
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 3",
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    python_requires='>=3.6',
)
