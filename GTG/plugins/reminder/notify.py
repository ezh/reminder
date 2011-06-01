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
import gtk
import tempfile

# for example: notify.py 00000000-0000-0000-0000-000000000000 IA== IA== IA== -1 -1 echo 123 > /tmp/test.echo
PLUGIN_NAME = 'reminder'
VERSION = open(os.path.join(os.path.dirname(__file__), 'version')).readline()

uuid = ''

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

def callback_stop(notification=None, action=None, data=None):
    # load exists crontab
    p = subprocess.Popen('crontab -l', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = ''
    output_err = ''
    skip_line = 0
    while True:
        stdout, stderr = p.communicate()
        tmp = stdout
        for line in tmp.split('\n'):
            # filter crontab record
            print('111' + line)
            if (line.find(' task ' + uuid + ' ') != -1):
                print('!!!!!!!!!')
                skip_line = 1
            else:
                if (skip_line == 1):
                    skip_line = 0
                else:
                    output += line + '\n'
        output_err += stderr
        rc = p.poll()
        if rc is not None:
            break
    # overwrite
    if (rc == 0):
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(output)
        f.close()
    else:
        print(output_err)
    # add to cron
    p = subprocess.Popen('crontab ' + f.name, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = ''
    while True:
        stdout, stderr = p.communicate()
        output += stdout
        output += stderr
        rc = p.poll()
        if rc is not None:
            break
    if (rc != 0):
        print(output)
    gtk.main_quit()

def callback_closed(notification=None, action=None, data=None):
    gtk.main_quit()
 
def main():
    # init
    pynotify.init('Getting Things GNOME! ' + PLUGIN_NAME)
    initCaps()
    # parse
    if (len(sys.argv) < 8):
        print('version: ' + VERSION)
        print('usage: notify.py uuid title(base64) message(base64) icon(base64) timeout urgency args...(base64)')
        print('example: notify.py 00000000-0000-0000-0000-000000000000 IA== IA== IA== -1 -1 IA==')
        printCaps()
        sys.exit(1)
    cron = int(sys.argv[1])
    global uuid
    uuid = sys.argv[2]
    title = base64.b64decode(sys.argv[3]) # 'IA==' as empty
    message = base64.b64decode(sys.argv[4]) # 'IA==' as empty
    icon = base64.b64decode(sys.argv[5]) # 'IA==' as empty
    timeout = int(sys.argv[6])
    urgency = int(sys.argv[7])
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
    if (capabilities['actions'] and cron):
        notice.add_action("clicked","Stop notify", callback_stop, None)
        notice.connect("closed", callback_closed)
    notice.show()
    # command
    if (len(sys.argv) == 9):
        arg = base64.b64decode(sys.argv[8])
        subprocess.Popen(arg, shell=True)
    # wait for action
    if (capabilities['actions'] and cron):
        gtk.main()

if __name__ == '__main__':
    main()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4:
