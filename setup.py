# -*- coding:utf-8 -*-
import sys
from distutils.core import setup

if '--user' in sys.argv: # There must be a better way to do this,
                         # if you know it, please tell me.
    import site
    packages_path = site.getusersitepackages()
else:
    from distutils import sysconfig
    packages_path = sysconfig.get_python_lib()

version = '1'

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
