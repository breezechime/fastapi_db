from setuptools import setup, find_packages


with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='fastapi_db',
    version='0.7.0',
    author='且听风铃、我是指针*、ZDLAY、KYZ',
    author_email='breezechime@163.com',
    description='fastapi使用sqlalchemy任意接口位置获取db上下文，非常安全并可靠。',
    long_description=long_description,
    keywords='fastapi,db,sqlalchemy',
    long_description_content_type="text/markdown",
    url='https://github.com/breezechime/fastapi_db',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'sqlalchemy>=1.4.46',
        'fastapi'
    ],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
    ],
    python_requires='>=3.6',
)