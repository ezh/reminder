# -*- coding: utf-8 -*-
# Copyright (c) 2011 - Alexey Aksenov <ezh@ezh.msk.ru>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>

import os

if (not 'DISPLAY' in os.environ):
    os.environ['DISPLAY'] = ':0'

import pynotify
import sys
import base64
import subprocess

# for example: notify.py 00000000-0000-0000-0000-000000000000 IA== IA== IA== -1 -1 echo 123 > /tmp/test.echo
PLUGIN_NAME = 'reminder'
VERSION = open(os.path.join(os.path.dirname(__file__), 'version')).readline()

capabilities = {'actions':             False,
                'body':                False,
                'body-hyperlinks':     False,
                'body-images':         False,
                'body-markup':         False,
                'icon-multi':          False,
                'icon-static':         False,
                'sound':               False,
                'image/svg+xml':       False,
                'private-synchronous': False,
                'append':              False,
                'private-icon-only':   False}
 
def initCaps():
    caps = pynotify.get_server_caps()
    if caps is None:
        print "Failed to receive server caps."
        sys.exit(1)
    for cap in caps:
        capabilities[cap] = True
 
def printCaps():
    info = pynotify.get_server_info()
    print "Information about your notification component:"
    print "Name:          " + info["name"]
    print "Vendor:        " + info["vendor"]
    print "Version:       " + info["version"]
    print "Spec. Version: " + info["spec-version"]
    caps = pynotify.get_server_caps()
    if caps is None:
        print "Failed to receive server caps."
        sys.exit (1)
    print "Supported capabilities/hints:"
    if capabilities['actions']:
        print "\tactions"
    if capabilities['body']:
        print "\tbody"
    if capabilities['body-hyperlinks']:
        print "\tbody-hyperlinks"
    if capabilities['body-images']:
        print "\tbody-images"
    if capabilities['body-markup']:
        print "\tbody-markup"
    if capabilities['icon-multi']:
        print "\ticon-multi"
    if capabilities['icon-static']:
        print "\ticon-static"
    if capabilities['sound']:
        print "\tsound"
    if capabilities['image/svg+xml']:
        print "\timage/svg+xml"
    if capabilities['private-synchronous']:
        print "\tprivate-synchronous"
    if capabilities['append']:
        print "\tappend"
    if capabilities['private-icon-only']:
        print "\tprivate-icon-only"
    print "Notes:"
    if info["name"] == "notify-osd":
        print "\tx- and y-coordinates hints are ignored"
        print "\texpire-timeout is ignored"
        print "\tbody-markup is accepted but filtered"
    else:
        print "\tnone"
 
# init
pynotify.init('Getting Things GNOME! ' + PLUGIN_NAME)
initCaps()
# parse
if (len(sys.argv) < 7):
    print('version: ' + VERSION)
    print('usage: notify.py uuid title(base64) message(base64) icon(base64) timeout urgency args...(base64)')
    print('example: notify.py 00000000-0000-0000-0000-000000000000 IA== IA== IA== -1 -1 IA==')
    printCaps()
    sys.exit(1)
uuid = sys.argv[1]
title = base64.b64decode(sys.argv[2]) # 'IA==' as empty
message = base64.b64decode(sys.argv[3]) # 'IA==' as empty
icon = base64.b64decode(sys.argv[4]) # 'IA==' as empty
timeout = int(sys.argv[5])
urgency = int(sys.argv[6])
# notice
if (title == ' '):
    title = 'Getting Things GNOME!'
if (icon != ' '):
    notice = pynotify.Notification(title, message, icon)
else:
    notice = pynotify.Notification(title, message, '/usr/share/icons/hicolor/32x32/apps/gtg.png')
if (timeout != -1):
    notice.set_timeout(timeout)
if (urgency != -1):
    notice.set_urgency(timeout)
notice.show()
# command
if (len(sys.argv) == 8):
    arg = base64.b64decode(sys.argv[7])
    subprocess.Popen(arg, shell=True)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4:
