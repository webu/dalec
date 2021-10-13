from setuptools import setup, find_packages
import os
import dalec


CLASSIFIERS = [
    "Development Status :: 1 - Planning",
    "Environment :: Web Environment",
    "Framework :: Django",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: BSD License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    "Topic :: Software Development",
    "Topic :: Software Development :: Libraries :: Application Frameworks",
    "Programming Language :: Python :: 3.7",
]

setup(
    author="WebU",
    author_email="contact@webu.coop",
    name="dalec",
    version=dalec.__version__,
    description="Extendable app to retrieve external contents from various sources",
    long_description=open(os.path.join(os.path.dirname(__file__), "README.md")).read(),
    url="https://dev.webu.coop/w/i/dalec",
    license="BSD License",
    platforms=["OS Independent"],
    classifiers=CLASSIFIERS,
    install_requires=["Django>=2.2"],
    packages=find_packages(exclude=["project", "project.*"]),
    include_package_data=True,
    zip_safe=False,
)
