from pkg_resources import parse_requirements
from setuptools import find_packages, setup


def load_requirements(fname: str) -> list:
    requirements = []
    with open(fname, 'r') as fp:
        for req in parse_requirements(fp.read()):
            extras = '[{}]'.format(','.join(req.extras)) if req.extras else ''
            requirements.append('{}{}{}'.format(req.name, extras, req.specifier))
    return requirements


setup(
    name='gokgs',
    version='1.0.0',
    author='Daniil Novoselov',
    author_email='gudnmail@gmail.com',
    python_requires='>=3.9',
    packages=find_packages(exclude=['tests']),
    install_requires=load_requirements('requirements.txt'),
    entry_points={
        'console_scripts': [
            'gokgs = gokgs.__main__:main',
        ],
    },
    include_package_data=True,
)
