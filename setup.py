from setuptools import setup, find_packages

setup(
    name="mi-analysis",
    version="0.1.0",
    packages=find_packages(),
    py_modules=["cli"],
    install_requires=[
        "typer",
        "radon",
        "GitPython",
        "matplotlib",
    ],
    entry_points={
        "console_scripts": [
            "mi-analysis=cli:app",
        ]
    },
)