from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="maxbridge",
    version="0.2.2",
    author="MaxBridge Team",
    author_email="",
    description="Асинхронная Python библиотека для MAX API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Sereuser/max-bridge",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Communications :: Chat",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="vk max messenger api websocket async",
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": ["black", "pytest", "pytest-asyncio"],
    },
    project_urls={
        "Bug Reports": "https://github.com/Sereuser/max-bridge/issues",
        "Source": "https://github.com/Sereuser/max-bridge",
        "Documentation": "https://github.com/Sereuser/max-bridge/tree/main/docs",
    },
)