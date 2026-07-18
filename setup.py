from setuptools import setup, find_packages

setup(
    name="sml",
    version="1.0.0",
    description="SML - ME Frp 终端图形化管理工具 (SSH/Terminal TUI)",
    packages=find_packages(exclude=["tests"]),
    python_requires=">=3.8",
    install_requires=[
        "textual>=1.0.0",
        "requests>=2.25.0",
        "pyyaml>=5.1",
    ],
    entry_points={
        "console_scripts": [
            "sml=sml.__main__:main",
        ],
    },
)
