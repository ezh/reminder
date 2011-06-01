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

import gtk
import os
import re
import subprocess
import pynotify
import base64
import tempfile

from GTG import _

#import rpdb2;
#rpdb2.start_embedded_debugger('test', fAllowRemote = True)

class Reminder:
    PLUGIN_NAME = 'reminder'
    VERSION = open(os.path.join(os.path.dirname(__file__), 'version')).readline()
    NOTIFY = os.path.join(os.path.dirname(__file__), 'notify.py')
    DEFAULT_PREFERENCES = {
            'ask_on_task_close': False,
            'command_open': '/usr/bin/mplayer',
            'command_at': '/usr/bin/at',
            'command_crontab': '/usr/bin/crontab'
            }

    kn = gtk.gdk.keyval_from_name
    key_Return = kn("Return")
    key_Escape = kn("Escape")

    def __init__(self):
        pynotify.init('Getting Things GNOME! ' + self.PLUGIN_NAME)
        self.ask_on_task_close = self.DEFAULT_PREFERENCES['ask_on_task_close']
        self.command_open = self.DEFAULT_PREFERENCES['command_open']
        self.command_at = self.DEFAULT_PREFERENCES['command_at']
        self.command_crontab = self.DEFAULT_PREFERENCES['command_crontab']
        self.reminders = {}

    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self.logger = self.plugin_api.get_logger()
        #Load the preferences
        self.preference_init()
        self.logger.debug('the plugin v' + self.VERSION + ' is initialized')

    def onTaskOpened(self, plugin_api):
        self.textview = plugin_api.get_textview()
        self.logger.debug('a task was opened')

    # Convert note 'special tags' to remind events
    def onTaskClosed(self, plugin_api):
        textview = plugin_api.get_textview()
        # we get the text
        textview_start = textview.buff.get_start_iter()
        textview_end = textview.buff.get_end_iter()
        texte = textview.buff.serialize(textview.buff, 'application/x-gtg-task', textview_start, textview_end)
        texte = re.sub(r'<[^>]+>', '', texte)
        tags = map((lambda x: x.get_name().lstrip('@')), plugin_api.get_tags())
        alarms = list(set(tags) & set(self.get_tag_names()))
        if (len(alarms) == 0):
            return
        alarms_parsed = []
        success_at = []
        unsuccess_at = []
        success_cron = []
        unsuccess_cron = []
        for alarm in alarms:
            arr = texte.split('\n@' + alarm + ' ')
            arr.pop(0) # remove title
            for i in range(len(arr)):
                m = re.search('\s*(#*[a-zA-Z+-:,\* /,-?#]+).*', arr[i])
                if (m != None):
                    arr[i] = m.group(1)
            for time in arr:
                if (plugin_api.get_task().get_uuid() + time.strip() in self.reminders):
                    self.logger.debug('reminder "' + time.strip() + '" already exists for task ' + plugin_api.get_task().get_uuid())
                    continue
                if (time[0] == '#'):
                    # cron job
                    (flag, message) = self.add_cron_job(plugin_api.get_task(), alarm, time[1:].strip())
                    if (flag):
                        success_cron.append([alarm, message])
                        self.reminders[plugin_api.get_task().get_uuid() + time.strip()] = True
                    else:
                        unsuccess_cron.append([alarm, message])
                else:
                    # at job
                    (flag, message) = self.add_at_job(plugin_api.get_task(), alarm, time.strip())
                    if (flag):
                        success_at.append([alarm, message])
                        self.reminders[plugin_api.get_task().get_uuid() + time.strip()] = True
                    else:
                        unsuccess_at.append([alarm, message])
        # generate notice message
        notice_message = ''
        error = False
        if (len(success_at) > 0 or len(success_cron) > 0):
            notice_message = _('Notification successfully updated.')
        if (len(unsuccess_at) > 0 or len(unsuccess_cron) > 0):
            error = True
            notice_message = _('Some notification successfully updated.')
        if (len(success_at) == 0 and len(success_cron) == 0 and (len(unsuccess_at) > 0 or len(unsuccess_cron) > 0)):
            error = True
            notice_message = _('Notification failed.')
        if (len(success_at) > 0 or len(unsuccess_at) > 0):
            notice_message = notice_message + _('\n ─── AT (atq for view) ───')
        for job in success_at:
            notice_message = notice_message + '\n@' + job[0] + ' at ' + job[1]
        for job in unsuccess_at:
            notice_message = notice_message + '\n@' + job[0] + ' - ' + job[1]
        if (len(success_cron) > 0 or len(unsuccess_cron) > 0):
            notice_message = notice_message + _('\n ─── CRON (crontab -l for view) ───')
        for job in success_cron:
            notice_message = notice_message + '\n@' + job[0] + ' at ' + job[1]
        for job in unsuccess_cron:
            notice_message = notice_message + '\n@' + job[0] + ' - ' + job[1]
        # fire notification
        if (notice_message != ''):
            icon = '/usr/share/icons/gnome/48x48/status/stock_appointment-reminder.png'
            notice = pynotify.Notification(plugin_api.get_task().get_title(), notice_message, icon)
            if (error):
                notice.set_timeout(0)
            notice.show()
        self.plugin_api.save_configuration_object(self.PLUGIN_NAME, 'reminders', self.reminders)
        self.logger.debug('a task was closed')

    def deactivate(self, plugin_api):
        self.logger.debug('the plugin was deactivated')

    def add_cron_job(self, task, alarm, time):
        self.logger.debug('add cron job for task ' + task.get_uuid() + ' for alarm @' + alarm + ' at <' + time + '>')
        # load exists crontab
        p = subprocess.Popen(self.command_crontab + ' -l', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = ''
        output_err = ''
        while True:
            stdout, stderr = p.communicate()
            output += stdout
            output_err += stderr
            rc = p.poll()
            if rc is not None:
                break
        if (rc == 0):
            crontab = output
        else:
            self.logger.debug(output_err)
            crontab = ''
        # add command to crontab
        command = ''
        title = ' '
        message = ' '
        icon = ' '
        timeout = -1
        urgency = -1
        if self.alarmtags[alarm][1] == 0:
            # message
            if (self.alarmtags[alarm][2].strip() != ''):
                title = task.get_title()
                message = self.alarmtags[alarm][2]
            else:
                message = task.get_title()
        elif self.alarmtags[alarm][1] == 1:
            # resource
            message = task.get_title()
            command = self.command_open + ' ' + self.alarmtags[alarm][2] + ' &\n'
        elif self.alarmtags[alarm][1] == 2:
            # command
            message = task.get_title()
            command = self.alarmtags[alarm][2] + '\n'
        if (title == ''):
            title = ' '
        if (message == ''):
            message = ' '
        if (icon == ''):
            icon = ' '
        arg = 'python ' + self.NOTIFY + ' 1 ' + \
            task.get_uuid() + ' ' + \
            base64.b64encode(title) + ' ' + \
            base64.b64encode(message) + ' ' + \
            base64.b64encode(icon) + ' ' + \
            str(timeout) + ' ' + str(urgency) + ' ' + base64.b64encode(command)
        crontab = crontab + '\n# gtg tag @' + alarm + ' task ' + task.get_uuid() + ' ' + task.get_title()
        crontab = crontab + '\n' + time + ' ' + arg + '\n'
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(crontab)
        f.close()
        # add to cron
        p = subprocess.Popen(self.command_crontab + ' ' + f.name, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = ''
        while True:
            stdout, stderr = p.communicate()
            output += stdout
            output += stderr
            rc = p.poll()
            if rc is not None:
                break
        if (rc != 0):
            self.logger.debug(output)
        else:
            output = time
        return ((rc == 0),  output)

    def add_at_job(self, task, alarm, time):
        self.logger.debug('add at job for task ' + task.get_uuid() + ' for alarm @' + alarm + ' at <' + time + '>')
        p = subprocess.Popen(self.command_at + ' -v ' + time, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        command = ''
        title = ' '
        message = ' '
        icon = ' '
        timeout = 0
        urgency = -1
        if self.alarmtags[alarm][1] == 0:
            # message
            if (self.alarmtags[alarm][2].strip() != ''):
                title = task.get_title()
                message = self.alarmtags[alarm][2]
            else:
                message = task.get_title()
        elif self.alarmtags[alarm][1] == 1:
            # resource
            message = task.get_title()
            command = self.command_open + ' ' + self.alarmtags[alarm][2] + ' &\n'
        elif self.alarmtags[alarm][1] == 2:
            # command
            message = task.get_title()
            command = self.alarmtags[alarm][2] + '\n'
        if (title == ''):
            title = ' '
        if (message == ''):
            message = ' '
        if (icon == ''):
            icon = ' '
        arg = 'python ' + self.NOTIFY + ' 0 ' + \
            task.get_uuid() + ' ' + \
            base64.b64encode(title) + ' ' + \
            base64.b64encode(message) + ' ' + \
            base64.b64encode(icon) + ' ' + \
            str(timeout) + ' ' + str(urgency) + ' ' + base64.b64encode(command)
        output = ''
        while True:
            stdout, stderr = p.communicate(arg)
            output += stdout
            output += stderr
            rc = p.poll()
            if rc is not None:
                break 
        self.logger.debug('execute at for tag @' + alarm + ' with rc:' + str(rc) + ' and result: ' + output)
        return ((rc == 0),  output[:output.index('\n')])

    def is_configurable(self):
        '''A configurable plugin should have this method and return True'''
        return True
    
    def configure_dialog(self, plugin_apis, manager_dialog):
        '''Callback for configuring a plugin'''
        self.on_grid_stop_editing()
        self.preferences_dialog.set_transient_for(manager_dialog)
        self.preferences_dialog.show_all()

    #############################################
    # Preferences methods
    
    def preference_init(self): 
        self.preferences_load()
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.dirname(os.path.abspath(__file__)) + '/reminder.ui')
        self.preferences_dialog = self.builder.get_object('preferences_dialog')
        self.treeview = self.builder.get_object('treeview')
        self.liststore = self.builder.get_object('liststore')
        self.liststoretype = self.builder.get_object('liststoretype')
        self.button_apply = self.builder.get_object('button2')
        self.button_add = self.builder.get_object('add')
        self.button_delete = self.builder.get_object('delete')
        self.button_find = self.builder.get_object('find')
        self.button_cancel = self.builder.get_object('button1')
        self.button_link = self.builder.get_object('linkbutton1')
        self.button_command_open = self.builder.get_object('filechooserbutton1')
        self.accelgroup = self.builder.get_object('accelgroup1')
        self.builder.get_object('typecol').set_cell_data_func(self.builder.get_object('typeimage'), self.set_grid_status_icon)
        SIGNAL_CONNECTIONS_DIC = {
            'on_preferences_dialog_delete_event':
                self.on_toolbar_cancel,
            'on_btn_preferences_cancel_clicked':
                self.on_toolbar_cancel,
            'on_btn_preferences_ok_clicked':
                self.on_toolbar_ok,
            'on_btn_preferences_add_clicked':
                self.on_toolbar_add,
            'on_btn_preferences_del_clicked':
                self.on_toolbar_del,
            'on_btn_preferences_find_clicked':
                self.on_toolbar_find,
            'on_tag_name_changed':
                self.on_grid_name_changed,
            'on_tag_name_changing':
                self.on_grid_name_changing,
            'on_tag_type_changed':
                self.on_grid_type_changed,
            'on_tag_type_changing':
                self.on_grid_type_changing,
            'on_tag_arg_changed':
                self.on_grid_arg_changed,
            'on_tag_arg_changing':
                self.on_grid_arg_changing,
            'on_grid_stop_editing':
                self.on_grid_stop_editing
        }
        self.builder.connect_signals(SIGNAL_CONNECTIONS_DIC)
        (key, mod) = gtk.accelerator_parse("Escape")
        self.accelgroup.connect_group(key, mod, gtk.ACCEL_VISIBLE, self.on_accel_cancel)
        (key, mod) = gtk.accelerator_parse("Return")
        self.accelgroup.connect_group(key, mod, gtk.ACCEL_VISIBLE, self.on_accel_apply)
        if self.preferences.has_key('alarmtags'):
            self.liststore.clear()
            for row in self.preferences['alarmtags']:
                self.liststore.append(row)
        self.preferences_apply()
        self.button_command_open.set_filename(self.command_open)

    def preferences_apply(self):
        self.ask_on_task_close = self.preferences['ask_on_task_close']
        self.command_open = self.preferences['command_open']
        self.command_at = self.preferences['command_at']
        self.command_crontab = self.preferences['command_crontab']
        self.alarmtags = {}
        self.preferences['alarmtags'] = []
        for row in self.liststore:
            (tag_name, tag_type, tag_arg) = row
            self.alarmtags[row[0]] = [tag_name, tag_type, tag_arg]
            self.preferences['alarmtags'].append([tag_name, tag_type, tag_arg])

    def preferences_load(self):
        data = self.plugin_api.load_configuration_object(self.PLUGIN_NAME, 'preferences')
        if data == None or type(data) != type (dict()):
            self.preferences = self.DEFAULT_PREFERENCES
        else:
            self.preferences = data
        for key in self.DEFAULT_PREFERENCES:
            if not key in self.preferences:
                self.preferences[key] = self.DEFAULT_PREFERENCES[key]
        if self.preferences.has_key('alarmtags'):
            self.alarmtags = {}
            for row in self.preferences['alarmtags']:
                (tag_name, tag_type, tag_arg) = row
                self.alarmtags[row[0]] = [tag_name, tag_type, tag_arg]
        self.reminders = self.plugin_api.load_configuration_object(self.PLUGIN_NAME, 'reminders')
        if self.reminders == None or type(self.reminders) != type (dict()):
            self.reminders = {}

    def preferences_store(self):
        self.plugin_api.save_configuration_object(self.PLUGIN_NAME, 'preferences', self.preferences)

    # grid routine

    def set_grid_status_icon(self, column, cell, model, iter, *data):
        value = model.get_value(iter, 1)
        if value == 0:
            cell.set_property ('stock-id', gtk.STOCK_INFO)
        elif value == 1:
            cell.set_property ('stock-id', gtk.STOCK_FILE)
        elif value == 2:
            cell.set_property ('stock-id', gtk.STOCK_EXECUTE)
    
    def on_grid_start_editing(self, cellrenderer = None):
        self.editing = True
        self.button_apply.set_sensitive(False)
        self.button_add.set_sensitive(False)
        self.button_delete.set_sensitive(False)
        self.button_find.set_sensitive(False)
        self.button_cancel.set_sensitive(False)
        self.button_link.set_sensitive(False)
    
    def on_grid_stop_editing(self, cellrenderer = None, data1 = None, data2 = None):
        self.editing = False
        self.button_apply.set_sensitive(True)
        self.button_add.set_sensitive(True)
        self.button_delete.set_sensitive(True)
        self.button_find.set_sensitive(True)
        self.button_cancel.set_sensitive(True)
        self.button_link.set_sensitive(True)

    def on_grid_name_changing(self, renderer, path, data = None):
        self.on_grid_start_editing()

    def on_grid_name_changed(self, renderer, path, new_name):
        self.on_grid_stop_editing()
        treeiter = self.liststore.get_iter(path)
        old_name = self.liststore.get_value(treeiter, 0)
        if new_name == old_name:
            return
        collections = [r[0] for r in self.liststore]
        if not new_name in collections:
            if new_name.strip != '':
                self.liststore.set(treeiter, 0, new_name)
        else:
            md = gtk.MessageDialog(self.preferences_dialog, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE, 'An entity with the same tag alreaty exists')
            md.run()
            md.destroy()

    def on_grid_type_changing(self, renderer, path, data = None):
        pass

    def on_grid_type_changed(self, renderer, path, new_iter):
        self.on_grid_stop_editing()
        value = self.liststoretype.get_value(new_iter, 0)
        treeiter = self.liststore.get_iter(path)
        if value == 'message':
            self.liststore.set(treeiter, 1, 0)
        elif value == 'resource':
            self.liststore.set(treeiter, 1, 1)
        elif value == 'command':
            self.liststore.set(treeiter, 1, 2)

    def on_grid_arg_changing(self, renderer, path, data = None):
        self.on_grid_start_editing()

    def on_grid_arg_changed(self, renderer, path, new_arg):
        self.on_grid_stop_editing()
        treeiter = self.liststore.get_iter(path)
        old_arg = self.liststore.get_value(treeiter, 2)
        if new_arg == old_arg:
            return
        self.liststore.set(treeiter, 2, new_arg)

    # toolbar routine

    def on_toolbar_cancel(self, widget = None, data = None):
        for i in range(len(self.preferences['alarmtags'])):
            self.liststore[i] = self.preferences['alarmtags'][i]
        self.preferences_dialog.hide()
        return True

    def on_toolbar_ok(self, widget = None, data = None):
        #self.preferences['ask_on_task_close'] = self.chbox_minimized.get_active()
        self.preferences['command_open'] = self.button_command_open.get_filename()
        self.preferences_apply()
        self.preferences_store()
        self.preferences_dialog.hide()
    
    def on_toolbar_add(self, widget = None, data = None):
        for row in self.liststore:
            if row[0] == '':
                md = gtk.MessageDialog(self.preferences_dialog, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE, 'Plain empty tag alreaty exists')
                md.run()
                md.destroy()
                return
        if len(self.liststore) == 0:
            self.treeview.set_property('can-focus', True)
        self.liststore.append(['', 0 , ''])

    def on_toolbar_del(self, widget = None, data = None):
        (dummy, selection) = self.treeview.get_selection().get_selected()
        if not selection:
            md = gtk.MessageDialog(self.preferences_dialog, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE, 'Please, select tag')
            md.run()
            md.destroy()
            return
        '''
        Confirm dialog if the user actually wishes to delete an activity.
        '''
        md = gtk.MessageDialog(self.preferences_dialog, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, 'Are you sure?')
        result = md.run()
        md.destroy()
        if result == gtk.RESPONSE_YES:
            '''Remove the row from the TreeView.'''
            self.liststore.remove(selection)
            if len(self.liststore) == 0:
                self.treeview.set_property('can-focus', False)
    
    def on_toolbar_find(self, widget = None, data = None):
        (dummy, selection) = self.treeview.get_selection().get_selected()
        if not selection:
            md = gtk.MessageDialog(self.preferences_dialog, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE, 'Please, select tag')
            md.run()
            md.destroy()
            return
        ''' Find file '''
        chooser = gtk.FileChooserDialog('Find file', self.preferences_dialog, gtk.FILE_CHOOSER_ACTION_OPEN,
                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        chooser.set_default_response(gtk.RESPONSE_OK)
        res = chooser.run()
        if res == gtk.RESPONSE_OK:
            filename = chooser.get_filename()
            try:
                f = open(filename, 'r')
                f.close()
                self.logger.debug('file ' + filename + ' open')
            except:
                md = gtk.MessageDialog(self.preferences_dialog, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE,
                        ('Unable to open %s\n' % (filename)))
                md.run()
                md.destroy()
            old_arg = self.liststore.get_value(selection, 2)
            self.liststore.set(selection, 2, old_arg + filename)
        chooser.destroy()

    # common dialog
    def on_accel_cancel(self, accelgroup, acceleratable, accel_key, accel_mods):
        if (self.editing == False):
            self.on_toolbar_cancel()
        else:
            self.on_grid_stop_editing()

    def on_accel_apply(self, accelgroup, acceleratable, accel_key, accel_mods):
        if (self.editing == False):
            self.on_toolbar_ok()
        else:
            self.on_grid_stop_editing()

    def get_tag_names(self):
        '''Return a list of the first-column treeview row values.'''
        return [r[0] for r in self.preferences['alarmtags']]

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4:
