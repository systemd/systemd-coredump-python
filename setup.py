# -*- coding:utf-8 -*-
import site
import sys
import sysconfig
from setuptools import setup

if '--user' in sys.argv: # There must be a better way to do this,
                         # if you know it, please tell me.
    packages_path = site.getusersitepackages()
else:
    packages_path = sysconfig.get_path('purelib')

version = '3'

setup (name = 'systemd-coredump-python',
       version = version,
       description = 'sys.excepthook helper to log Python exceptions in the journal via systemd-coredump',
       long_description = open('README').read(),
       author = 'Zbigniew Jędrzejewski-Szmek',
       author_email = 'zbyszek@in.waw.pl',
       url = 'https://github.com/systemd/systemd-coredump-python',
       license = 'GPLv2+',
       classifiers = [
           'Programming Language :: Python :: 2',
           'Programming Language :: Python :: 3',
           'Topic :: Software Development :: Libraries :: Python Modules',
           'Topic :: System :: Logging',
           'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
           ],
       py_modules = ['systemd_coredump_exception_handler'],
       data_files = [(packages_path, ["systemd_coredump.pth"])],
)
