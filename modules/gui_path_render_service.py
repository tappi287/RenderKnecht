"""
gui_path_service - Path Render Service Tab

Copyright (C) 2017 Stefan Tapper, All rights reserved.

    This file is part of RenderKnecht Strink Kerker.

    RenderKnecht Strink Kerker is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    RenderKnecht Strink Kerker is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with RenderKnecht Strink Kerker.  If not, see <http://www.gnu.org/licenses/>.

"""
import pickle
import json
import re
from pathlib import Path
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QDesktopServices
from queue import Queue
from datetime import datetime, timedelta
from functools import partial

from modules.gui_set_path import SetDirectoryPath
from modules.knecht_animation import AnimatedButton
from modules.tree_overlay import InfoOverlay, Overlay
from modules.tree_context_menus import JobManagerContextMenu
from modules.knecht_threads import GetPfadAeffchenService
from modules.knecht_socket import Ncat
from modules.job import Job
from modules.knecht_log import init_logging
from modules.app_globals import SocketAddress
from modules.app_strings import Msg

# Initialize logging for this module
LOGGER = init_logging(__name__)


class PathRenderService(QtCore.QObject):
    job_idx = 0
    btn_connected = 'Status prüfen'
    btn_disconnected = 'Render Dienst im lokalen Netzwerk suchen'
    add_message = QtCore.pyqtSignal((str, bool))

    switch_btn_timer = QtCore.QTimer()
    switch_btn_timer.setSingleShot(True)
    switch_btn_timer.setInterval(3000)

    refresh_btn_timer = QtCore.QTimer()
    refresh_btn_timer.setSingleShot(True)
    refresh_btn_timer.setInterval(3000)

    update_job_manager_timer = QtCore.QTimer()
    update_job_manager_timer.setTimerType(QtCore.Qt.VeryCoarseTimer)
    update_job_manager_timer.setInterval(20000)

    update_job_alive_timer = QtCore.QTimer()
    update_job_alive_timer.setTimerType(QtCore.Qt.VeryCoarseTimer)
    update_job_alive_timer.setInterval(10000)

    keep_alive_timer = QtCore.QTimer()
    keep_alive_timer.setTimerType(QtCore.Qt.VeryCoarseTimer)
    keep_alive_timer.setInterval(150000)
    keep_alive_timer.setSingleShot(True)

    def __init__(self, app, ui):
        super(PathRenderService, self).__init__()
        self.app, self.ui = app, ui

        self.search_thread = GetPfadAeffchenService()
        self.search_thread.result.connect(self.search_service_result)

        # --------- Connect button ---------
        self.ui.pathConnectBtn.pressed.connect(self.switch_service_on_off)
        self.ui.pathConnectBtn.animation = AnimatedButton(self.ui.pathConnectBtn, 900)
        self.switch_btn_timer.timeout.connect(self.switch_button_timeout)

        # Highlight connect button on tab change/click
        self.ui.tabWidget.tabBarClicked.connect(self.tab_bar_clicked)

        # --------- Refresh button ------------
        self.ui.pathRefreshBtn.pressed.connect(self.request_job_queue)
        self.refresh_btn_timer.timeout.connect(self.refresh_btn_timeout)

        # --------- Validate Job Name ---------
        self.ui.pathJobNameLineEdit.editingFinished.connect(self.validate_job_name)

        # --------- Job Options ---------
        self.ui.checkBoxCsbIgnoreHidden.toggled.connect(self.update_csb_import_option)
        self.ui.checkBoxMayaDeleteHidden.toggled.connect(self.update_maya_delete_hidden_option)
        self.ui.checkBoxUseSceneSettings.toggled.connect(self.update_use_scene_settings)
        self.csb_ignore_hidden = '1'
        self.maya_delete_hidden = '1'
        self.use_scene_settings = '0'

        # --------- Set scene file ---------
        self.scene_file = Path('.')
        args = ('Szenendatei *.csb oder *.mb auswählen',  # title
                'DeltaGen CSB, Maya binary (*.csb;*.mb)',  # filter
                )
        self.file_dialog = SetDirectoryPath(
            app, ui, mode='file',
            line_edit=self.ui.pathSceneLineEdit, tool_button=self.ui.pathSceneBtn,
            dialog_args=args, reject_invalid_path_edits=True
            )
        self.file_dialog.path_changed.connect(self.update_scene_file)
        self.file_dialog.invalid_path_entered.connect(self.invalid_scene_path_entered)

        # --------- Set output dir ---------
        self.output_dir = Path('.')
        args = ('Ausgabe Verzeichnis auswählen',)
        self.dir_dialog = SetDirectoryPath(
            app, ui,
            line_edit=self.ui.pathOutputLineEdit, tool_button=self.ui.pathOutputBtn,
            dialog_args=args,
            )
        self.dir_dialog.path_changed.connect(self.update_output_dir)

        # --------- Add job button ---------
        self.ui.pathJobSendBtn.pressed.connect(self.create_job)
        self.ui.pathJobSendBtn.setEnabled(False)

        # --------- Help button ---------
        self.ui.pathBtnHelp.pressed.connect(self.open_help)

        # --------- Job Manager Tree Widget ------------
        self.ui.widgetJobManager.manager_open_item = self.manager_open_item
        self.ui.widgetJobManager.itemDoubleClicked.connect(self.manager_open_item)
        self.ui.widgetJobManager.manager_open_scene_btn = self.manager_open_scene_btn
        self.ui.widgetJobManager.manager_delete_render_file = self.manager_delete_render_file

        # --------- Job Manager Context Menu ------------
        self.context_menu = JobManagerContextMenu(self.ui.widgetJobManager, self.ui)
        self.context_menu.move_job.connect(self.manager_move_job)
        self.context_menu.cancel_job.connect(self.manager_cancel_job)
        self.context_menu.force_psd.connect(self.manager_force_psd_creation)

        # Sort Job Manager columns
        self.ui.label_PfadAeffchen.mouseDoubleClickEvent = self.manager_sort_header

        # Update job Manager
        self.update_job_manager_timer.timeout.connect(self.request_job_queue)
        self.update_job_alive_timer.timeout.connect(self.alive_blink)

        self.ui.widgetJobManager.overlay = InfoOverlay(self.ui.widgetJobManager)
        self.first_update = True
        self.ovr = self.ui.widgetJobManager.overlay

        # --------- Status Browser ------------
        self.text_browser = self.ui.renderServiceBrowser
        self.text_browser.ovr = Overlay(self.text_browser)

        # Set splitter size
        self.ui.jobStatusSplitter.setSizes([200, 100])

        # Prepare message sending
        # Service address
        self.service_host = None
        self.send_thread = None
        self.msg_queue = Queue(maxsize=64)
        self.keep_alive_timer.timeout.connect(self.end_send_thread)

        self.job_queue = None

        self.app.aboutToQuit.connect(self.quit_app)

    def quit_app(self):
        self.end_send_thread()

    def alive_blink(self):
        self.ui.led_ovr.led(2, 2, blink_count=2)

    def tab_bar_clicked(self, tab_index: int=0):
        if tab_index == 2:  # Path Render Service tab index
            if not self.service_host:
                # Highlight connect button
                self.ui.pathConnectBtn.animation.play_highlight()

    def switch_service_on_off(self):
        self.switch_btn_timer.start()
        self.ui.pathConnectBtn.setEnabled(False)

        if self.service_host:
            # Switch off
            self.ui.pathConnectBtn.animation.play_off()
            self.service_unavailable()
        else:
            self.ui.pathConnectBtn.animation.play_on()
            self.search_service()

    def switch_button_timeout(self):
        self.ui.pathConnectBtn.setEnabled(True)

    def refresh_btn_timeout(self):
        self.ui.pathRefreshBtn.setEnabled(True)

    def end_send_thread(self):
        if self.send_thread:
            if self.send_thread.isRunning() and self.msg_queue.empty():
                self.send_thread.requestInterruption()
                self.msg_queue.put(('EndThread', False))

                LOGGER.info('Path Render Service send thread shutting down.')
                self.send_thread.wait(msecs=15000)
                self.send_thread = None

    def search_service(self):
        if self.service_host:
            self.send_message('GET_STATUS')
            return

        self.ui.led_ovr.led(1, 2)
        self.ui.led_ovr.led(2, 2, timer=100)
        self.ui.led_ovr.yellow_on()

        if not self.search_thread.isRunning():
            self.ui.pathJobSendBtn.setEnabled(False)
            self.update_status('Suche nach Dienst im lokalen Netzwerk.', 2)
            self.search_thread.start()

            self.text_browser.ovr.load_start()

    def setup_renderer_box(self, renderer):
        self.ui.rendererBox.clear()
        self.ui.rendererBox.addItems(renderer)

    def search_service_result(self, result):
        LOGGER.info('Render path service search result: %s', result)
        self.text_browser.ovr.load_finished()

        self.ui.led_ovr.yellow_off()

        if result:
            self.update_status(f'Pfad Äffchen Render Dienst gefunden<br>IP: <i>{result}</i>', 2)
            self.enable_job_btn()
            self.update_job_manager_timer.start()
            self.update_job_alive_timer.start()
        else:
            self.ui.led_ovr.led(2, 2)
            self.ui.led_ovr.led(1, 2, timer=100)
            self.update_status(f'Kein Pfad Äffchen Render Dienst im lokalen Netzwerk gefunden', 2)
            self.service_unavailable()
            return

        self.service_host = result
        self.ovr.display('Render Service erfolgreich verbunden.', 2000)
        self.send_message('GREETINGS_2')
        self.send_message('GET_RENDERER')

    def update_scene_file(self, scene_path: Path):
        self.scene_file = scene_path
        self.update_status(f'Szenen Datei gesetzt:<br><i>{scene_path.as_posix()}</i>', 2)
        LOGGER.debug('Path service scene: %s', self.scene_file)

    def invalid_scene_path_entered(self):
        """ User entered non-existent path into line widget """
        msg = 'Ungültiger / Nicht existenter Szenen-Pfad angegeben.'
        scene_file_error = self.validate_scene_file_type(self.scene_file.as_posix())

        if not scene_file_error:
            # Restore last valid scene file
            self.ui.pathSceneLineEdit.setText(self.scene_file.as_posix())
            msg += ' Setze vorherigen Szenenpfad.'
            self.update_status(f'Vorherigen Szenenpfad gesetzt:<br><i>{self.scene_file.as_posix()}</i>', 2)
        else:
            # No path to restore
            self.update_status('Ungültigen Szenenpfad verworfen. Kein Szenen-Pfad gesetzt.', 2)

        self.ovr.display(msg, 5000)

    def update_output_dir(self, output_path):
        self.output_dir = output_path
        self.update_status(f'Ausgabeverzeichnis gesetzt:<br><i>{output_path.as_posix()}</i>', 2)
        LOGGER.debug('Path service output dir: %s', self.output_dir)

    def update_csb_import_option(self, ignore_hidden):
        """ Set CSB Import ignoreHiddenOption=1 or 0 """
        if ignore_hidden:
            self.csb_ignore_hidden = '1'
        else:
            self.csb_ignore_hidden = '0'
        self.update_status(f'CSB Import Option gesetzt: <i>ignoreHiddenObject={self.csb_ignore_hidden}</i>', 2)
        LOGGER.debug('Toggled CSB import option: %s, set value to %s', ignore_hidden, self.csb_ignore_hidden)

    def update_maya_delete_hidden_option(self, maya_delete_hidden):
        """ Set CSB Import ignoreHiddenOption=1 or 0 """
        if maya_delete_hidden:
            self.maya_delete_hidden = '1'
        else:
            self.maya_delete_hidden = '0'
        self.update_status(f'Maya Prozess Option gesetzt: <i>maya_delete_hidden={self.maya_delete_hidden}</i>', 2)
        LOGGER.debug('Toggled Maya delete hidden option: %s, set value to %s',
                     maya_delete_hidden, self.maya_delete_hidden)

    def update_use_scene_settings(self, use_scene_settings):
        if use_scene_settings:
            self.use_scene_settings = '1'
        else:
            self.use_scene_settings = '0'
        self.update_status(f'Maya Prozess Option gesetzt: <i>use_scene_settings={self.use_scene_settings}</i>', 2)
        LOGGER.debug('Toggled Maya use scene settings option: %s, set value to %s',
                     use_scene_settings, self.use_scene_settings)

    def create_job(self):
        self.ui.pathJobSendBtn.setEnabled(False)

        self.job_idx += 1
        job_title = self.ui.pathJobNameLineEdit.text() or f'Job_{self.job_idx:03d}'
        scene_file = self.scene_file.as_posix()
        render_dir = self.output_dir.as_posix()
        renderer = self.ui.rendererBox.currentText()

        validation_error = self.validate_settings(scene_file, render_dir, renderer)
        if validation_error:
            self.job_idx -= 1
            msg = '<b>Ungültige Job Daten:</b><br>' + validation_error
            self.ovr.display(msg, 2000)
            self.update_status(msg, 2)
            self.ui.pathJobSendBtn.setEnabled(True)
            return

        # Change to Job Manager tab
        self.ovr.display(f'{job_title} übertragen für {self.scene_file.stem}', 4000)

        msg = 'ADD_JOB '

        for __s in [job_title, scene_file, render_dir, renderer,
                    self.csb_ignore_hidden, self.maya_delete_hidden, self.use_scene_settings]:
            msg += __s + ';'

        # Remove trailing semicolon
        msg = msg[:-1]

        self.send_message(msg)

        self.request_job_queue()
        self.update_job_manager_timer.start()
        self.update_job_alive_timer.start()

    def get_job_from_item_index(self, item):
        idx = self.ui.widgetJobManager.indexOfTopLevelItem(item)

        if len(self.job_queue) > idx:
            job = self.job_queue[idx]
        else:
            return None

        return job

    def open_desktop_directory(self, directory: Path):
        """ Open directory with desktop explorer """
        if directory.exists():
            q = QtCore.QUrl.fromLocalFile(directory.as_posix())
            QDesktopServices.openUrl(q)
        else:
            self.ovr.display(f'Verzeichnis existiert nicht.<br>{directory.as_posix()}', 5000)

    def manager_open_item(self, item, column=None):
        """ Open Render directory on item double click """
        output_dir = Path(item.text(3))
        self.open_desktop_directory(output_dir)

    def manager_open_scene_btn(self, item):
        """ Open scene directory on button click """
        directory = Path(item.text(2))
        directory = directory.parent
        self.open_desktop_directory(directory)

    def manager_delete_render_file(self, item):
        job = self.get_job_from_item_index(item)

        if not job:
            return

        if job.status < 4:
            self.ovr.display('<b>Nachricht von Kapitän Offensichtlich:</b><br>'
                             '<i>Rendering Szenen laufender Jobs können nicht gelöscht werden!</i>', 7500)
            return

        # Path to scene file eg. C:/some_dir/some_file.csb
        scene_file = Path(job.file)
        # Create render file name some_file_render.mb
        render_file = Path(scene_file.stem + '_render.mb')
        # Create the path to the render file C:/some_dir/some_file_render.mb
        render_file = scene_file.with_name(render_file.name)

        if render_file.exists():
            # Delete the file
            try:
                render_file.unlink()
            except Exception as e:
                LOGGER.error('Error deleting render file %s', e)
                self.ovr.display(
                    f'Fehler: Datei {render_file.name} konnte nicht entfernt werden.\n{e}', 7500)
                return
        else:
            self.ovr.display(
                f'Datei {render_file.name} <b>existiert nicht mehr oder kann nicht gefunden werden.</b>', 7500)
            return

        self.ovr.display(f'Datei {render_file.name} wurde entfernt.', 7500)

    def manager_sort_header(self, click_event=None):
        """ Setup item column widths """
        header = self.ui.widgetJobManager.header()
        col_widths = [65, 90, 130, 130, 150, 140, 105, 50]

        for column in range(0, header.count() - 1):
            header.resizeSection(column, col_widths[column])

        # Set sorting order to ascending by column 0: order
        self.ui.widgetJobManager.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def manager_move_job(self, item, to_top):
        job = self.get_job_from_item_index(item)

        if not job:
            return

        if to_top:
            msg = f'MOVE_JOB_TOP {job.remote_index}'
        else:
            msg = f'MOVE_JOB_BACK {job.remote_index}'

        self.send_message(msg)

    def manager_cancel_job(self, item):
        job = self.get_job_from_item_index(item)

        if not job:
            return

        if job.status > 3:
            self.ovr.display('<b>Nachricht von Kapitän Offensichtlich:</b><br>'
                             '<i>Abgeschlossene Jobs können nicht mehr abgebrochen werden.</i>', 7500)
            return

        msg = f'CANCEL_JOB {job.remote_index}'

        self.send_message(msg)

    def manager_force_psd_creation(self, item):
        job = self.get_job_from_item_index(item)

        if not job:
            return

        msg = f'FORCE_PSD_CREATION {job.remote_index}'

        self.send_message(msg)
        self.ovr.display(f'<b>{job.title}</b><br>'
                         '<i>Die bereits ausgegebenen Bilddaten werden in einem PSD zusammengestellt '
                         'und der Job wird abgeschlossen. Dies kann wenige Minuten dauern.</i>', 7500)

    def request_job_queue(self):
        """ Request the remote job queue as pickled data """
        if not self.service_host:
            self.switch_service_on_off()
            return

        self.ui.pathRefreshBtn.setEnabled(False)
        self.refresh_btn_timer.start()

        self.send_message('GET_JOB_DATA', job_data=True, silent=True)
        self.ovr.display('Aktualisiere Job Daten ...', 1400)

    def legacy_pickle(self, data):
        try:
            self.job_queue = pickle.loads(data)
        except Exception as e:
            LOGGER.error('Error updating job data.')
            LOGGER.error(e)

    def update_job_data(self, data):
        """ Receives pickled job data """
        if data is None:
            self.update_job_manager_timer.stop()
            self.update_job_alive_timer.stop()
        elif b'Queue-Finished' in data:
            self.ovr.display('<b>Render Service Warteschlange fertiggestellt.</b><br>'
                             '<i>Automatische Job Manager Updates wurden ausgeschaltet.</i>', 12000)
            self.update_job_manager_timer.stop()
            self.update_job_alive_timer.stop()
            # Remove Queue finished data
            data = data[:data.find(b'Queue-Finished')]

        try:
            load_dict = json.loads(data, encoding='utf-8')
        except Exception as e:
            LOGGER.error(e)
            return

        self.job_queue = list()

        for d in load_dict.items():
            idx, job_dict = d
            # Create empty job instance
            job = Job('', '', '', '')
            # Update instance from loaded dict
            job.__dict__.update(job_dict)
            # Store in job queue
            self.job_queue.append(job)

        if not self.job_queue:
            return

        # Clear Job Manager widget and re-construct from received data
        self.ui.widgetJobManager.clear()

        for job in self.job_queue:
            update_job_manager_widget(job, self.ui.widgetJobManager)

        if self.first_update:
            self.manager_sort_header()
            self.first_update = False

    def enable_job_btn(self):
        """ Enabled if we receive a response from the render service """
        self.ui.pathJobSendBtn.setEnabled(True)
        self.ui.pathConnectBtn.setEnabled(True)
        self.ui.jobBox.setEnabled(True)

    def service_unavailable(self):
        self.ui.jobBox.setEnabled(False)
        self.ui.pathJobSendBtn.setEnabled(False)
        self.ui.pathConnectBtn.setEnabled(True)

        # Clear Job Manager
        self.update_job_manager_timer.stop()
        self.update_job_alive_timer.stop()
        self.ui.widgetJobManager.clear()

        # Clear renderer
        self.ui.rendererBox.clear()

        # Change to status tab
        msg = '<span style="color:red;"><b>Verbindung zum Render Dienst getrennt.</b></span>'
        self.ovr.display(msg, 6000)
        self.update_status(msg, 2)
        self.service_host = None

    def send_message(self, msg, job_data=False, silent=False):
        if not self.service_host:
            return

        address = (self.service_host, SocketAddress.service_port)

        if not self.send_thread:
            self.send_thread = SocketSendMessage(address, self.msg_queue)
            # Send result strings to status browser
            self.send_thread.result.connect(self.update_status)
            # Send result bytes data to update job method
            self.send_thread.job_data_result.connect(self.update_job_data)
            self.send_thread.enable_send_btn.connect(self.enable_job_btn)
            self.send_thread.not_responding.connect(self.service_unavailable)

            self.send_thread.green_on.connect(self.ui.led_ovr.green_on)
            self.send_thread.green_off.connect(self.ui.led_ovr.green_off)
            self.send_thread.yellow_on.connect(self.ui.led_ovr.yellow_on)
            self.send_thread.yellow_off.connect(self.ui.led_ovr.yellow_off)

            # Start send thread
            self.send_thread.start()

        if not silent:
            self.update_status(msg, 1)

        self.msg_queue.put((msg, job_data))
        LOGGER.info('Contacting path service at %s with message %s', address, msg)
        # Restart keep send thread alive timer after every send operation
        self.keep_alive_timer.start()

    def update_status(self, status_msg, is_response=0):
        """ Receive messages and update text browser """
        if status_msg.startswith('RENDERER'):
            socket_command = status_msg[len('RENDERER '):]

            renderer = list()
            for __r in socket_command.split(';'):
                renderer.append(__r)
            self.setup_renderer_box(renderer)

        current_time = datetime.now().strftime('(%H:%M:%S) ')
        if is_response == 0:
            is_response = 'Empfange: '
        elif is_response == 1:
            is_response = 'Sende   : '
        elif is_response == 2:
            is_response = ''

        self.text_browser.append(current_time + is_response + status_msg)

    def validate_job_name(self):
        job_name_text = self.ui.pathJobNameLineEdit.text()[:64]

        if not bool(re.compile(r'^[A-Za-z0-9-_]+\Z').match(job_name_text)):
            self.ui.pathJobNameLineEdit.clear()
            self.ui.pathJobNameLineEdit.setPlaceholderText(
                'Job Titel darf nur Buchstaben, Zahlen, Binde- oder _strich enthalten.'
                )

    @staticmethod
    def validate_scene_file_type(scene_file):
        if scene_file.casefold().endswith('.mb') or scene_file.casefold().endswith('.csb'):
            return False
        else:
            return 'No valid scene file *.mb or *.csb'

    @classmethod
    def validate_settings(cls, scene_file, render_dir, renderer):
        scene_file_error = cls.validate_scene_file_type(scene_file)
        if scene_file_error:
            return scene_file_error

        if not render_dir or render_dir == '.':
            return 'Rendering directory does not exist.'

        if not renderer:
            return 'No renderer set'

        return False

    @staticmethod
    def open_help():
        link = QtCore.QUrl(Msg.APP_PATH_HELP_LINK)
        QDesktopServices.openUrl(link)


class SocketSendMessage(QtCore.QThread):
    result = QtCore.pyqtSignal(str)
    job_data_result = QtCore.pyqtSignal(object)
    enable_send_btn = QtCore.pyqtSignal()
    not_responding = QtCore.pyqtSignal()

    green_on = QtCore.pyqtSignal()
    green_off = QtCore.pyqtSignal()
    yellow_on = QtCore.pyqtSignal()
    yellow_off = QtCore.pyqtSignal()

    timeout = 10

    def __init__(self, address, message_queue):
        super(SocketSendMessage, self).__init__()
        self.address = address
        self.sock = None
        self.msg_queue = message_queue

    def run(self):
        while not self.isInterruptionRequested():
            msg, is_job_data = self.msg_queue.get()
            if msg == 'EndThread':
                break
            self.send_message(msg, is_job_data)

        LOGGER.debug('Send thread ended.')

    def send_message(self, data, is_job_data):
        # Socket was closed, re-connect
        host, port = self.address
        self.sock = Ncat(host, port, socket_timeout=self.timeout)
        # Connect NC signals to LED's
        self.sock.signals.send_start.connect(self.green_on)
        self.sock.signals.send_end.connect(self.green_off)
        self.sock.signals.recv_start.connect(self.yellow_on)
        self.sock.signals.recv_end.connect(self.yellow_off)
        self.sock.signals.connect_start.connect(self.green_on)
        self.sock.signals.connect_end.connect(self.green_off)

        self.sock.connect()

        self.sock.send(data)

        if is_job_data:
            # Receive JSON dict data or empty byte object
            response = self.sock.receive_job_data(timeout=self.timeout, end=b'End-Of-Job-Data')
        else:
            # Receive string or empty string
            response = self.sock.receive_short_timeout(timeout=self.timeout)

        # Close socket, server will only respond once
        self.sock.close()

        # Empty response means nothing received, None response means connection lost
        if response is None:
            self.not_responding.emit()
            return
        else:
            self.enable_send_btn.emit()

        if is_job_data:
            self.job_data_result.emit(response)
        else:
            self.result.emit(response)


def update_job_manager_widget(job, widget):
    """ Add a job to the JobManager widget """
    # Display remaining hours, minutes until job expires
    expire_date = datetime.fromtimestamp(job.created) + timedelta(hours=24)
    delta = expire_date - datetime.now()
    m, s = divmod(delta.seconds, 60)
    h, m = divmod(m, 60)
    if expire_date > datetime.now():
        expires = f'{h:02d}h:{m:02d}min'
    else:
        expires = 'Abgelaufen.'

    # Creation time string
    creation_date = datetime.fromtimestamp(job.created)
    creation_date = creation_date.strftime('%d.%m.%Y %H:%M')

    # Create widget item
    item_values = ['00', job.title, job.file, job.render_dir, job.status_name,
                   creation_date, expires, job.client, str(job.remote_index)]
    item = QtWidgets.QTreeWidgetItem(widget, item_values)
    item.setText(0, f'{widget.topLevelItemCount():02d}')

    progress_bar = QtWidgets.QProgressBar(parent=widget)
    progress_bar.setAlignment(QtCore.Qt.AlignCenter)

    # Open scene directory button
    scene_btn = QtWidgets.QPushButton('Pfad öffnen', widget)
    scene_btn.setContentsMargins(2, 2, 2, 2)
    scene_btn.pressed.connect(partial(widget.manager_open_scene_btn, item))
    widget.setItemWidget(item, 2, scene_btn)

    # Open output directory button
    dir_btn = QtWidgets.QPushButton('Ausgabe öffnen', widget)
    dir_btn.setContentsMargins(2, 2, 2, 2)
    dir_btn.pressed.connect(partial(widget.manager_open_item, item))
    widget.setItemWidget(item, 3, dir_btn)

    job.update_progress()
    progress_bar.setFormat(job.status_name)
    progress_bar.setValue(job.progress)

    widget.setItemWidget(item, 4, progress_bar)
