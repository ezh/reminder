#!/usr/bin/env python

from distutils.core import setup

setup(name = 'reminder',
      version = open("version", "r+").read().split()[0],
      description = 'Getting Things GNOME! reminder plugin',
      long_description = "Populating at and cron jobs from GTG",
      author = 'Alexey Aksenov',
      author_email = 'ezh@ezh.msk.ru',
      url = 'http://github/',
      packages = [ 'GTG.plugins.reminder' ],
      classifiers = (
          'Development Status :: 2 - Pre-Alpha',
          'Environment :: Plugins',
          'License :: OSI Approved :: GNU General Public License (GPL)',
          'Operating System :: POSIX',
          'Operating System :: Unix',
          'Programming Language :: Python',
        ),
      license = "GPL-3"
      )
