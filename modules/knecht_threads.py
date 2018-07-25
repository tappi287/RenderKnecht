"""
knecht_qthread for py_knecht.

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
import time
from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST, gethostname, gethostbyname_ex, timeout
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
from PyQt5 import QtWidgets
from modules.app_globals import Msg, FAKOM_READER_PR_FAM, SocketAddress
from modules.knecht_parse_excel import LoadVplus
from modules.gui_excel_dialog import VplusWindow
from modules.knecht_log import init_logging
from modules.knecht_legacy_variants import convertVariants
from modules.knecht_image import create_png_images

# Initialize logging for this module
LOGGER = init_logging(__name__)


class ExcelConversionThread(QObject):
    continue_thread = pyqtSignal(bool)

    def __init__(self, open_dialog, file, tree_widget, fakom_reader: bool=False, wizard: bool=False):
        super().__init__()
        self.open_dialog = open_dialog
        self.widget = tree_widget
        self.file = file
        self.xmlFile = False
        self.abort = False
        self.window = None
        self.obj = None

        # indicate thread is not running
        self.thread = False

        # FaKom Reader skips interaction
        self.fakom_reader = fakom_reader

        # Opened from wizard
        self.wizard = wizard

    def create_thread(self):
        if self.thread:
            try:
                if self.thread.isRunning():
                    QtWidgets.QMessageBox.information(self.open_dialog.ui,
                                                      Msg.MSG_EXC_BOX_TITLE,
                                                      Msg.EXC_THREAD_ERROR)
            except Exception as e:
                LOGGER.debug('Excel thread not running. %s', e)
                pass

        # Disable Open menu
        self.open_dialog.ui.enable_load_actions(False)

        self.obj = ExcelConversionWorker(self.file)

        self.thread = QThread()

        # 3 - Move the Worker object to the Thread object
        self.obj.moveToThread(self.thread)
        LOGGER.debug('Excel conv moved to thread.')
        self.obj.strReady.connect(self.conversion_xml_file)

        # Status messages
        self.obj.xls_msg.connect(self.display_status)
        self.obj.xls_err_msg.connect(self.display_error)

        # 4 - Connect Worker Signals to the Thread slots
        self.obj.finished.connect(self.thread.quit)

        # Start Excel Window if PR-Familys read
        self.obj.prFam_model.connect(self.excel_window)

        self.continue_thread.connect(self.obj.continue_excel_after_window)

        self.thread.started.connect(self.obj.convert)

        self.thread.finished.connect(self.conversion_finished)

        # 6 - Start the thread
        self.thread.start()

    def excel_window(self, pr_fam_list, model_list):
        self.window = VplusWindow(self, pr_fam_list, model_list,
                                  self.file, self.fakom_reader, self.wizard)

        # Exec window and wait for result
        if self.window.exec():
            self.abort = False
        else:
            self.abort = True

        if self.fakom_reader:
            # Overwrite user options if Fakom import is active
            LoadVplus.shorten_names = False
            LoadVplus.shorten_pkg_name = False
            LoadVplus.read_packages = False
            # Create optional PR-Codes presets and trimlines
            LoadVplus.read_options = True
            LoadVplus.read_trim = True
            # Create optional SIB/LUM/VOS packages
            LoadVplus.read_pkg_options = True
            # Set Fakom specific PR-Family Filter
            LoadVplus.pr_fam_filter = FAKOM_READER_PR_FAM

        self.continue_thread.emit(self.abort)

    def display_status(self, message):
        self.widget.info_overlay.display(
            message, duration=5500, immediate=True)

    def display_error(self, message):
        self.widget.info_overlay.display_confirm(
            message, ('[X]', None))

    def conversion_xml_file(self, file):
        self.xmlFile = file

    def conversion_finished(self):
        # Enable Open menu
        self.open_dialog.ui.enable_load_actions(True)

        # Stop load animation
        if not self.wizard:
            self.open_dialog.stop_load_overlay()

        # Conversion finished, parse Xml file
        if not self.abort:
            if self.xmlFile:
                LOGGER.info('XML file created: %s', self.xmlFile)
                self.open_dialog.parse_xml(self.xmlFile)
                return True
            else:
                LOGGER.error(
                    'Could not convert Excel file or conversion aborted: %s',
                    self.file)
                QtWidgets.QMessageBox.information(self.open_dialog.parent,
                                                  Msg.MSG_EXC_BOX_TITLE,
                                                  Msg.EXC_FILE_ERROR)
                if self.wizard:
                    self.open_dialog.abort_vplus()
                return False
        else:
            if self.wizard:
                self.open_dialog.abort_vplus()
            return False


class ExcelConversionWorker(QObject):
    finished = pyqtSignal()
    strReady = pyqtSignal(object)
    prFam_model = pyqtSignal(set, list)
    xls_msg = pyqtSignal(str)
    xls_err_msg = pyqtSignal(str)

    def __init__(self, file):
        super(QObject, self).__init__()
        self.file = file
        self._wb = None
        self._xls = None
        self.continue_excel_thread = False
        self.abort = False

    def convert(self):
        xml_file = None

        self._xls = LoadVplus(self.file)
        self._xls.status_msg.connect(self.report_status)
        self._xls.error_msg.connect(self.report_error)

        self._wb = self._xls.read_workbook()
        pr_fam_list = self._xls.read_pr_familys(self._wb)

        # Abort on error
        if not pr_fam_list:
            self.strReady.emit(xml_file)
            self.finished.emit()
            return

        model_list = self._xls.read_and_return_models(self._wb)

        self.prFam_model.emit(pr_fam_list, model_list)
        self.continue_excel_thread = False
        self.abort = False

        # Idle thread while user is selecting options in excel window
        while 1:
            time.sleep(1)
            QtWidgets.QApplication.processEvents()

            if self.continue_excel_thread:
                if self.abort:
                    self.finished.emit()
                    return
                break

        xml_file = self._xls.create_document(self._wb)
        self._wb.close()

        self.strReady.emit(xml_file)
        self.finished.emit()

    def continue_excel_after_window(self, abort):
        """ Receives continue or abort signal from V-Plus window """
        self.abort = abort
        self.continue_excel_thread = True

    def report_status(self, msg):
        self.xls_msg.emit(msg)

    def report_error(self, msg):
        self.xls_err_msg.emit(msg)


class ConvertLegacyVariants(QObject):

    def __init__(self, parseXmlClass, file, ui):
        super().__init__()
        self.parseXmlClass = parseXmlClass
        self.file = file
        self.ui = ui

    def create_thread(self):
        # Disable Open menu
        self.ui.enable_load_actions(False)
        self.obj = ConvertVariantsWorker(self.file)
        self.thread = QThread()

        # 2 - Connect Worker`s Signals to Form method slots to post data.
        self.obj.strReady.connect(self.conversion_xml_file)

        # 3 - Move the Worker object to the Thread object
        self.obj.moveToThread(self.thread)

        # 4 - Connect Worker Signals to the Thread slots
        self.obj.finished.connect(self.thread.quit)

        # 5 - Connect Thread started signal to Worker operational slot method
        self.thread.started.connect(self.obj.convert)

        # * - Thread finished signal will close the app if you want!
        self.thread.finished.connect(self.conversion_finished)

        # 6 - Start the thread
        self.thread.start()

    def conversion_xml_file(self, xmlFile):
        self.xmlFile = xmlFile

    def conversion_finished(self):
        if self.xmlFile:
            LOGGER.info('XML file created: %s', self.xmlFile)
            self.parseXmlClass.parse_xml(self.xmlFile)
        else:
            LOGGER.error('Could not convert XML File.')

        # Enable Open menu
        self.ui.enable_load_actions(True)

        # Stop load animation
        self.parseXmlClass.stop_load_overlay()


class ConvertVariantsWorker(QObject):
    finished = pyqtSignal()
    strReady = pyqtSignal(str)

    def __init__(self, file):
        super(QObject, self).__init__()
        self.file = file

    @pyqtSlot()
    def convert(self):  # A slot takes no params
        xmlFile = convertVariants(self.file)
        self.strReady.emit(xmlFile)
        self.finished.emit()


class PngConvertThread(QObject):

    def __init__(self, ui, action, img_list):
        super().__init__()
        self.img_list = img_list
        self.ui = ui
        self.action = action

        # Thread instances
        self.obj = PngWorker(self.img_list)
        self.thread = QThread()
        self.obj.moveToThread(self.thread)

        # Overlay Shortcut
        self.info_overlay = self.ui.treeWidget_SrcPreset.info_overlay.display
        self.info_overlay_btn = self.ui.treeWidget_SrcPreset.info_overlay.display_confirm

    def create_thread(self):
        # Disable GUI menu
        self.action.setEnabled(False)

        self.thread.started.connect(self.obj.convert)
        self.obj.return_msg.connect(self.png_info_box)
        self.obj.finished.connect(self.thread.quit)
        self.obj.progress_msg.connect(self.progress_status)

        LOGGER.debug('Creating PNG Worker thread.')
        self.info_overlay(
            'Starte Konvertierung zu PNG von {:=02d} Dateien'
            .format(len(self.img_list)),
            3500,
            immediate=True)
        self.thread.start()

    def png_info_box(self, return_message):
        # self.ui.info_box(msg.PNG_INFO_TITLE, 'PNG Konvertierung abgeschlossen')
        self.info_overlay_btn(
            return_message, ('[X]', None), immediate=True)
        LOGGER.debug('PNG Converter thread returned:\n%s', return_message)

        # Re-enable GUI menu
        self.action.setEnabled(True)
        LOGGER.debug('PNG Conversion thread finished.')

    def progress_status(self, progress_txt):
        self.info_overlay(progress_txt, 4500, immediate=True)


class PngWorker(QObject):
    finished = pyqtSignal()
    return_msg = pyqtSignal(str)
    progress_msg = pyqtSignal(str)

    def __init__(self, img_list):
        super(QObject, self).__init__()
        self.img_list = img_list

    def convert(self):
        LOGGER.debug('PNG Conversion thread started.')
        rtn_msg = ''

        for idx, img in enumerate(self.img_list):
            prg_msg = 'Konvertiere {:=03d}/{:=03d}: <b>{}</b><br>{}'\
                .format(idx+1, len(self.img_list), img.name, img.parent)

            self.progress_msg.emit(prg_msg)
            rtn_msg += create_png_images([img])

        self.return_msg.emit(rtn_msg)
        self.finished.emit()


def get_service_address():
    search_timeout = 20  # Search for x seconds
    socket_timeout = 2
    service_address, data = None, None

    s = socket(AF_INET, SOCK_DGRAM)  # create UDP socket
    s.settimeout(socket_timeout)
    s.bind(('', SocketAddress.service_port))
    LOGGER.debug('Listening to service announcement on %s', SocketAddress.service_port)

    s_time = time.time()

    while 1:
        try:
            data, addr = s.recvfrom(1024)  # wait for a packet
            data = data.decode(encoding='utf-8')
            LOGGER.debug('Service listener received: %s', data)
        except timeout:
            pass

        if data:
            if data.startswith(SocketAddress.service_magic):
                service_address = data[len(SocketAddress.service_magic):]
                LOGGER.debug('Received service announcement from %s', service_address)

        if (time.time() - s_time) > search_timeout or service_address:
            break

    s.close()
    return service_address


class GetPfadAeffchenService(QThread):
    result = pyqtSignal(object)
    service_address = None

    def __init__(self):
        super(GetPfadAeffchenService, self).__init__()

    def run(self):
        self.service_address = get_service_address()

        if self.service_address:
            self.result.emit(self.service_address)
        else:
            self.result.emit(False)
