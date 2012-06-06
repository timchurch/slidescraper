from setuptools import setup, find_packages

version = '0.1'

setup(
    name="slidescraper",
    version=version,
    maintainer='Tim Church',
    maintainer_email='tim.church+slidescraper@gmail.com',
    url='https://github.com/timchurch/slidescraper',
    packages=find_packages(),
    install_requires=[
        'lxml>=2.3.4',
        'oauth2>=1.5.211',
        'feedparser>=5.1.1',
        'beautifulsoup4>=4.0.2',
        'requests>=0.10.8',
        'python-dateutil==1.5',
#        'xmltodict>=0.1',
    ],
)

