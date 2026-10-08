from setuptools import find_packages, setup

setup(
    name="md-link-check",
    version="0.1.0",
    description="Offline checks for relative links and anchors in Markdown files",
    packages=find_packages(include=["md_link_check*"]),
    python_requires=">=3.10",
    entry_points={"console_scripts": ["md-link-check=md_link_check.cli:main"]},
)
