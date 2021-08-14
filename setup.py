#!/usr/bin/python
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="raymarching",
    version="0.1.2",
    author="NamorNiradnug",
    author_email="roma57linux@gmail.com",
    description="Module for ray marching GLSL fragment shaders generation.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/NamorNiradnug/raymarching",
    project_urls={
        "Bug Tracker": "https://github.com/NamorNiradnug/raymarching/issues",
        "Source": "https://github.com/NamorNiradnug/raymarching",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=["raymarching"],
    package_data={'raymarching': ["raymarching.frag"]},
    python_requires=">=3.7",
)
