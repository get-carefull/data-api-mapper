from setuptools import find_packages, setup

setup(
    name='data-api-mapper',
    version='0.0.2',
    url='https://github.com/get-carefull/data-api-mapper',
    author='Flavio Oliveri',
    author_email='flavio.oliveri@gmail.com',
    description='A very simplistic AWS Aurora Serverless Data API mapper',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    install_requires=[
        'boto3 >= 1.16.31, < 2'
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
    ],
    packages=find_packages(exclude=['test']),
    test_suite='test'
)
