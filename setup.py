from setuptools import setup


def version():
    from setuptools_scm.version import get_local_dirty_tag

    def clean_scheme(version):
        # Disable local scheme by default since it is not supported
        # by PyPI (See PEP 440). If code is not committed add +dirty
        # to version to prevent upload to either PyPI or test PyPI.
        return get_local_dirty_tag(version) if version.dirty else ''

    return {'local_scheme': clean_scheme}


setup(
    use_scm_version=version,
    setup_requires=['setuptools_scm', 'wheel'],
)
