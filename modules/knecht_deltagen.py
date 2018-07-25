"""

knecht_send_to_dg thread for DeltaGen sending and rendering.

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
from math import log as math_log
from pathlib import Path

from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, QThread, QUrl, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QBrush, QColor, QDesktopServices
from imageio import imread

from modules.knecht_image import create_png_images
from modules.app_globals import HELPER_DIR, INVALID_CHR, ItemColumn, Itemstyle, Msg, RENDER_MACHINE_FACTOR, \
    RENDER_RES_FACTOR, TCP_IP, TCP_PORT
from modules.knecht_log import init_logging
from modules.knecht_socket import Ncat

# Initialize logging for this module
LOGGER = init_logging(__name__)


def time_string(time_f):
    """ Converts time in float seconds to h:mm:ss """
    m, s = divmod(time_f, 60)
    h, m = divmod(m, 60)

    if h < 1:
        return '{:=02.0f}min:{:=02.0f}sec'.format(m, s)
    else:
        return '{:=01.0f}h:{:=02.0f}min:{:=02.0f}sec'.format(h, m, s)


class SendToDeltaGen(QObject):
    """ Sends variants to DeltaGen in a seperate thread """
    reset = True
    viewer = True
    viewer_size = '1280 720'
    viewer_bgr_color = ''
    set_viewer_bgr = False
    # Enter receive loop after Variant sent and report Variant Status
    check_variants = True
    # User defined render path
    render_user_path = False
    convert_to_png = True
    create_render_preset_dir = False
    long_render_timeout = False
    last_preset_added = None

    def __init__(self, app, btn, abort_btn, widget, perform_rendering=False):
        super().__init__()
        self.obj = None
        self.btn = btn
        self.abort_btn = abort_btn
        self.app = app
        self.widget = widget
        self.perform_rendering = perform_rendering
        self.render_presets = dict()
        self.sending_msg = '..wird gesendet.'
        self.finished_msg = self.btn.text()
        self.start_time = time.time()
        self.num_variants_sent = 0
        self.variants_list = []
        self.find_reference = app.ui.find_reference_items

        # Indicate running thread
        self.thread = False

        # No reset conf and user choosed to abort
        self.abort_variant_send = False

        # Make sure we ask only once
        self.asked_about_reset = False
        self.asked_about_check_variants = False

        # Reset progress bar
        self.update_progress_bar(0)

        self.btn.setStyleSheet(Itemstyle.DG_BTN_READY)

    def end_thread(self):
        if self.thread:
            if self.thread_running():
                LOGGER.info('Shutting down DeltaGen communication thread.')
                try:
                    self.thread.exit_thread()
                except AttributeError:
                    pass

            self.thread.exit()
            self.thread.wait(msecs=20000)
            LOGGER.info('DeltaGen communication thread shut down.')

    def resize_viewer(self):
        nc = Ncat(TCP_IP, TCP_PORT)
        nc.connect()
        try:
            nc.send('SIZE VIEWER ' + self.viewer_size + '; UNFREEZE VIEWER;')
        except:
            LOGGER.error('Sending viewer size command failed.')

        nc.close()

    def set_viewer_color(self):
        if self.set_viewer_bgr:
            color = QColor(self.viewer_bgr_color)
            c = (color.redF(), color.greenF(), color.blueF(), color.alphaF())

            nc = Ncat(TCP_IP, TCP_PORT)
            nc.connect()
            try:
                # BACKGROUND VIEWER f f f f
                nc.send('BACKGROUND VIEWER {:.4f} {:.4f} {:.4f} {:.4f};'.format(*c))
            except Exception as e:
                LOGGER.error('Sending viewer size command failed.\n%s', e)

            nc.close()

    def thread_running(self):
        if self.thread:
            return self.thread.isRunning()
        return False

    def create_thread(self):
        if self.thread_running():
            self.widget.info_overlay.display_confirm(Msg.DG_THREAD_RUNNING, ('Okay', None), immediate=True)
            return

        self.abort_variant_send = False
        variant_str_list = []

        # Reset item backgrounds
        for context in self.app.ui.context_menus:
            context.reset_variants()

        if self.perform_rendering:
            # Collect render settings and variants
            self.render_presets = self.collect_render_settings()
            if not self.validate_render_settings(self.render_presets):
                self.display_message(Msg.RENDER_NO_PRESETS, duration=8000)
                return
            LOGGER.info('Render Presets collected \n%s', self.render_presets)
        else:
            # Collect variants from tree widgets
            self.collect_variants()

            if self.abort_variant_send:
                return

            # Create variant string list
            for variant in self.variants_list:
                variant_str_list.append('VARIANT ' + variant.text(1) + ' ' + variant.text(2) + ';')

        # No reset conf, user choosed abort
        if self.abort_variant_send:
            return

        # Disable sent button
        self.btn.setEnabled(False)
        self.btn.setText(self.sending_msg)
        self.btn.setStyleSheet(Itemstyle.DG_BTN_BUSY)
        self.btn.setIcon(self.app.ui.icon['coffee'])

        self.obj = send_to_dg_worker(variant_str_list, self.viewer, self.check_variants, self.render_presets,
                                     self.render_user_path, self.convert_to_png, self.long_render_timeout,
                                     self.create_render_preset_dir)
        self.thread = QThread()

        # 2 - Connect Worker`s Signals to Form method slots to post data.
        self.obj.strReady.connect(self.on_variant_sent)
        self.obj.no_connection.connect(self.no_connection)
        self.obj.status.connect(self.status_changed)
        self.obj.display_msg.connect(self.display_message)
        self.obj.render_progress.connect(self.update_progress_bar)
        self.obj.green_on.connect(self.green_on)
        self.obj.green_off.connect(self.green_off)
        self.obj.yellow_on.connect(self.yellow_on)
        self.obj.yellow_off.connect(self.yellow_off)

        # 3 - Move the Worker object to the Thread object
        self.obj.moveToThread(self.thread)

        # Abort button
        self.abort_btn.setEnabled(True)
        self.abort_btn.pressed.connect(self.obj.abort_signal)

        # 4 - Connect Worker Signals to the Thread slots
        self.obj.finished.connect(self.thread.quit)

        # 5 - Connect Thread started signal to Worker operational slot method
        self.thread.started.connect(self.obj.send_variants)

        # * - Thread finished signal will close the app if you want!
        self.thread.finished.connect(self.on_send_complete)

        # Clear widget info overlay and prepare info messages
        self.widget.info_overlay.display_exit()
        self.start_time = time.time()
        self.num_variants_sent = 0

        # 6 - Start the thread
        self.thread.start()

    def collect_variants(self, render_variants=False):
        """ Collects variants from Variants Widget """
        # Variants collector list
        variant_items = []

        # Reset Configuration
        if self.reset:
            # Collect reset variants
            reset_presets = self.app.ui.treeWidget_DestPreset.findItems('reset', Qt.MatchExactly, 3)
            LOGGER.debug('Reset presets: %s', reset_presets)

            if reset_presets:
                for reset_preset in reset_presets:
                    for c in range(0, reset_preset.childCount()):
                        variant_items.append(reset_preset.child(c))
                if render_variants:
                    # Append pseudo variant to enter render viewset at this point later
                    # variant_items.append('')
                    pass
            else:
                if not self.asked_about_reset:
                    # No reset configuration found, ask to continue
                    self.asked_about_reset = True

                    if self.app.ui.question_box(Msg.DG_NO_CONN_TITLE, Msg.DG_NO_RESET):
                        self.abort_variant_send = True
                        return

        # Check Variants disabled, ask to continue
        if not self.asked_about_check_variants and not self.check_variants:
            self.asked_about_check_variants = True

            if self.app.ui.question_box(Msg.DG_NO_CONN_TITLE, Msg.DG_NO_CHECK_VARIANTS):
                self.abort_variant_send = True
                return

        if render_variants:
            variant_items += render_variants
        else:
            # Collect all items in variants list
            variant_items += self.widget.findItems('*', Qt.MatchWildcard)

        self.variants_list = []

        # Collect variants and references recursively
        for variant in variant_items:
            # Collect references
            if variant.UserType == 1002:
                LOGGER.debug('Collecting reference: %s Id %s', variant.text(1), variant.text(4))
                reference_items, ref_msg = self.find_reference.search(variant)

                # Report recursion error
                if ref_msg:
                    QtWidgets.QMessageBox.information(self.widget, Msg.REF_ERROR_TITLE, ref_msg)

                # Append references to variant_list
                if reference_items is not None:
                    for reference in reference_items:
                        if reference.UserType == 1001:
                            self.variants_list.append(reference)

            # Add variants
            if variant.UserType == 1001:
                self.variants_list.append(variant)

    def collect_render_settings(self, skip_variants=False):
        """
            Collect Render Presets
        """

        def ask_abort_viewset():
            if self.app.ui.question_box('Viewset', Msg.OVERLAY_NO_VIEWSET_WARN):
                self.abort_variant_send = True
                return

        def collect_viewset(id):
            viewset_list = self.app.ui.treeWidget_DestPreset.findItems(id, Qt.MatchExactly, ItemColumn.ID)
            if viewset_list:
                # Split Viewset values "Name Value;"
                try:
                    value = 'VARIANT ' + viewset_list[0].child(0).text(ItemColumn.NAME)
                    value += ' ' + viewset_list[0].child(0).text(ItemColumn.VALUE) + ';'
                    return value
                except AttributeError:
                    LOGGER.error('Viewset empty. Returning dummy value.')
                    self.widget.info_overlay.display(Msg.OVERLAY_NO_VIEWSET_WARN, 3000, True)
                    ask_abort_viewset()
                    return 'VARIANT DUMMY EMPTY_VIEWSET;'
            else:
                LOGGER.error('Can not read empty viewset. Returning dummy value.')
                self.widget.info_overlay.display(Msg.OVERLAY_NO_VIEWSET_WARN, 3000, True)
                ask_abort_viewset()
                return 'VARIANT DUMMY EMPTY_VIEWSET;'

        render_presets_list = []
        render_preset_dict = dict()

        # Collect Render Preset's
        for idx, item in enumerate(self.widget.findItems('*', Qt.MatchWildcard)):
            if item.UserType == 1003:
                name = item.text(ItemColumn.NAME)
                render_presets_list.append(item)
                render_preset_dict[idx] = dict(render_preset_name=name)

        # Render time calculation
        # List of tuples (num_views, num_presets, samples, res_x), list lenght = num_render_presets
        render_time_calc = []

        # Collect Render Preset's contents
        for idx, render_preset in enumerate(render_presets_list):
            render_preset_dict[idx]['viewsets'] = []
            render_preset_dict[idx]['preset'] = dict()
            num_views, preset_count, samples, res_x = 0, 0, 1, 1280

            for c in range(0, render_preset.childCount()):
                item = render_preset.child(c)

                if item.UserType == 1002 and item.text(ItemColumn.TYPE) == 'viewset':
                    # Collect Viewset's in Render-Preset
                    viewset = collect_viewset(item.text(ItemColumn.REF))
                    render_preset_dict[idx]['viewsets'].append(viewset)
                    # Render time calc
                    num_views += 1

                if item.UserType == 1002 and item.text(ItemColumn.TYPE) != 'viewset':
                    # grab referenced presets
                    preset_count += 1

                    # Collect variants
                    # Skipping is just for render time calculation
                    if not skip_variants:
                        self.collect_variants([item])
                        if self.abort_variant_send: return

                        variant_str_list = []
                        for variant in self.variants_list:
                            variant_str_list.append('VARIANT ' + variant.text(1) + ' ' + variant.text(2) + ';')

                        # Append to render presets
                        render_preset_dict[idx]['preset'][preset_count] = dict(name=item.text(1),
                                                                               variants=variant_str_list)

                # Grab settings
                if item.UserType == 1004:
                    # Anti Aliasing
                    if item.text(ItemColumn.TYPE) == 'sampling':
                        # Reverse power of two
                        sample_pow = math_log(max(1, int(item.text(2)))) / math_log(2)
                        # Clamp 0 - 12
                        sampling = max(1, min(12, sample_pow))
                        render_preset_dict[idx]['sampling'] = str(int(sampling))
                        """
                            # 2 ** Setting Exponent
                            sampling = 2**item.text(2)
                        """
                        # Render time calc
                        samples = int(item.text(2))
                    # File Extension
                    elif item.text(ItemColumn.TYPE) == 'file_extension':
                        render_preset_dict[idx]['file_extension'] = item.text(2)
                    # Resolution
                    elif item.text(ItemColumn.TYPE) == 'resolution':
                        res = item.text(2).split(' ', 2)
                        if len(res) == 2:
                            if res[0].isdigit() and res[1].isdigit():
                                render_preset_dict[idx]['resolution'] = res[0] + ' ' + res[1]
                                # Render time calc
                                res_x = int(res[0])

            render_time_calc.append((num_views, preset_count, samples, res_x))

        self.estimate_render_time(render_time_calc)
        return render_preset_dict

    def validate_render_settings(self, render_preset_dict):
        # Check render path
        if not self.render_user_path or self.render_user_path == Path('.'):
            QtWidgets.QMessageBox.critical(self.widget, Msg.GENERIC_ERROR_TITLE, Msg.RENDER_INVALID_PATH)
            return False

        # Check if all settings are available
        if render_preset_dict:
            for idx in range(0, len(render_preset_dict)):
                for k in ['resolution', 'sampling', 'file_extension']:
                    if not k in render_preset_dict[idx].keys():
                        LOGGER.error('Render Preset #%s is invalid. Setting: %s is missing', idx, k)
                        render_msg = 'Render preset #' + str(idx + 1) + ' has no setting:<br><b>' + k
                        render_msg += '</b><br><br>Can not start render process.'
                        QtWidgets.QMessageBox.critical(self.widget, 'Render Preset', render_msg)
                        render_preset_dict.pop(idx)
                        return False
        else:
            return False

        return True

    def estimate_render_time(self, render_time_calc):
        render_time = 0
        images = 0
        images_sum = 0

        for render_preset in render_time_calc:
            num_views, preset_count, samples, res_x = render_preset
            if num_views == 0: num_views = 1
            images = num_views * preset_count
            images_sum += images

            # Calculate render_preset render time
            sampling_factor = res_x * samples
            resolution_factor = res_x * RENDER_RES_FACTOR
            render_preset_time = sampling_factor * RENDER_MACHINE_FACTOR * resolution_factor
            render_preset_time = render_preset_time * images
            render_time += render_preset_time

        # h:mm:ss
        display_time_str = time_string(render_time)
        LOGGER.debug('Estimated render time: %s', display_time_str)
        render_display_string = '{time} ({img_num} Bilder)'.format(time=display_time_str, img_num=images_sum)

        """
        render_display = divmod(int(render_time), 60)
        render_display_string = str(render_display[0]).rjust(2, '0') + 'min : '
        render_display_string += str(render_display[1]).rjust(2, '0') + 'sec'
        # to hours, minutes, seconds
        if render_display[0] >= 60:
            render_hour = divmod(render_display[0], 60)
            render_display = (render_hour[0], render_hour[1], render_display[1])
            render_display_string = str(render_display[0]).rjust(2,
                                                                 '0') + 'hrs : '
            render_display_string += str(render_display[1]).rjust(
                2, '0') + 'min : '
            render_display_string += str(render_display[2]).rjust(2,
                                                                  '0') + 'sec'
        if images_sum > 1:
            render_display_string += ' (' + str(images_sum) + ' Bilder)'
        """
        # Display estimation
        self.app.ui.label_renderTime.setText(render_display_string)

    def on_variant_sent(self, variant_idx, set, val):
        """
            Receives variant_state feedback
            variant_idx: Item index
            set: column as integer or bool
            val: column as integer or bool
        """
        green = QBrush(QColor(*Itemstyle.COLOR['GREEN']), Qt.SolidPattern)
        orange = QBrush(QColor(*Itemstyle.COLOR['ORANGE']), Qt.SolidPattern)
        self.num_variants_sent += 1

        try:
            current_item = self.variants_list[variant_idx]
        except IndexError:
            LOGGER.error('Switched Item could not be highlighted. It may be deleted or changed position. Index: %s',
                         variant_idx)
            return

        overlay_txt = current_item.text(ItemColumn.NAME) + ' ' + current_item.text(ItemColumn.VALUE)
        overlay_txt += Msg.OVERLAY_DG_SWITCH
        self.widget.info_overlay.display(overlay_txt, 1200, True)

        # Highlight switched Items
        if variant_idx >= 0 and self.check_variants:
            if set:
                current_item.setBackground(set, green)
            else:
                current_item.setBackground(ItemColumn.NAME, orange)

            if val:
                current_item.setBackground(val, green)
            else:
                current_item.setBackground(ItemColumn.VALUE, orange)

            if current_item.parent():
                if self.app.ui.actionTreeStateCheck.isChecked():
                    current_item.parent().setExpanded(True)

    def no_connection(self):
        QtWidgets.QMessageBox.critical(self.widget, Msg.DG_NO_CONN_TITLE, Msg.DG_NO_CONN)
        return

    def status_changed(self, msg):
        self.btn.setText(msg)

    def green_on(self):
        self.app.ui.led_ovr.green_on()

    def green_off(self):
        self.app.ui.led_ovr.green_off()

    def yellow_on(self):
        self.app.ui.led_ovr.yellow_on()

    def yellow_off(self):
        self.app.ui.led_ovr.yellow_off()

    def display_message(self, msg, *btns, duration: int = 4000):
        if len(btns) >= 1:
            if btns[0]:
                self.widget.info_overlay.display_confirm(msg, *btns)
                return

        self.widget.info_overlay.display(msg, duration, immediate=True)

    def update_progress_bar(self, progress):
        self.app.ui.progressBar_render.setValue(progress)

    def rendering_finished_overlay(self):
        try:
            img_path = str(self.obj.initial_out_dir.resolve())

            def open_image_folder_btn():
                q = QUrl.fromLocalFile(img_path)
                QDesktopServices.openUrl(q)

            render_time = time_string(time.time() - self.start_time)

            # Message num_images + render_time
            msg = Msg.DG_RENDERING_FINISHED.format(len(self.obj.img_list), render_time)

            self.display_message(msg, ('Ordner öffnen', open_image_folder_btn), ('[X]', None))

        except Exception as e:
            LOGGER.error('Could not create Rendering Finished overlay:\n%s', e)

    def variants_sent_overlay(self):
        if self.last_preset_added:
            try:
                # Button Method
                def select_src_preset():
                    if self.last_preset_added.treeWidget():
                        self.last_preset_added.treeWidget().clearSelection()

                        if self.last_preset_added:
                            self.last_preset_added.setSelected(True)

                msg = Msg.DG_VARIANTS_SENT_PRESET.format(self.num_variants_sent, len(self.variants_list),
                                                         preset=self.last_preset_added.text(ItemColumn.NAME))

                self.display_message(msg, ('Auswählen', select_src_preset), ('[X]', None))

            except Exception as e:
                LOGGER.error('Could not create Variants Sent finished overlay:\n%s', e)
        else:
            msg = Msg.DG_VARIANTS_SENT.format(self.num_variants_sent, len(self.variants_list))

            self.display_message(msg, ('[X]', None))

    def on_send_complete(self):
        LOGGER.debug('Sent Thread finished.')

        # Display finished message
        if self.perform_rendering:
            self.rendering_finished_overlay()
        else:
            self.variants_sent_overlay()

        # Disable abort button
        self.abort_btn.setEnabled(False)

        # Reset progress bar
        self.app.ui.progressBar_render.setValue(0)

        # Enable send button
        self.btn.setEnabled(True)
        self.btn.setText(self.finished_msg)
        self.btn.setStyleSheet(Itemstyle.DG_BTN_READY)
        self.btn.setIcon(self.app.ui.icon['send'])


class send_to_dg_worker(QObject):
    finished = pyqtSignal()
    no_connection = pyqtSignal()
    status = pyqtSignal(str)
    display_msg = pyqtSignal(str, object)
    strReady = pyqtSignal(object, object, object)
    render_progress = pyqtSignal(int)

    green_on = pyqtSignal()
    green_off = pyqtSignal()
    yellow_on = pyqtSignal()
    yellow_off = pyqtSignal()

    def __init__(self, variants_list, viewer, check_variants, render_dict=dict(), render_user_path=False,
                 convert_to_png=True, long_render_timeout=False, create_render_preset_dir=False):
        super(QObject, self).__init__()
        self.variants_list = variants_list
        self.render_dict = render_dict
        # Freeze viewer during send *bool
        self.viewer = viewer
        self.viewer_size = SendToDeltaGen.viewer_size
        self.check_variants = check_variants
        self.convert_to_png = convert_to_png
        self.abort_connection = False
        self.render_user_path = render_user_path
        self.long_render_timeout = long_render_timeout
        self.create_render_preset_dir = create_render_preset_dir
        self.nc = Ncat(TCP_IP, TCP_PORT)

        # Connect NC signals to LED's
        self.nc.signals.send_start.connect(self.green_on)
        self.nc.signals.send_end.connect(self.green_off)
        self.nc.signals.recv_start.connect(self.yellow_on)
        self.nc.signals.recv_end.connect(self.yellow_off)
        self.nc.signals.connect_start.connect(self.yellow_on)
        self.nc.signals.connect_end.connect(self.yellow_off)

    @pyqtSlot()
    def abort_signal(self):
        self.abort_connection = True
        LOGGER.info('Abort Signal triggered. Telling send thread to abort.')

    def exit_thread(self):
        if self.viewer:
            self.restore_viewer()

        self.abort_connection = True
        self.nc.close()
        self.finished.emit()

    def connect_to_deltagen(self, timeout=3, num_tries=5):
        """ Tries to establish connection to DeltaGen in num_tries with increasing timeout """
        self.nc.connect()

        for c in range(0, num_tries):
            dg_connected = self.nc.deltagen_is_alive(timeout)

            if dg_connected:
                self.display_msg.emit('DeltaGen Verbindung erfolgreich verifiziert.', ())
                return True

            # Next try with slightly longer timeout
            timeout += c * 2

            LOGGER.error('Send to DeltaGen thread could not establish a connection after %s seconds.', timeout)

            if c == num_tries - 1:
                break

            for d in range(6, 0, -1):
                # Check abort signal
                QtWidgets.QApplication.processEvents()
                if self.abort_connection:
                    return False

                self.display_msg.emit(
                    'DeltaGen Verbindungsversuch ({!s}/{!s}) in <b>{!s}</b> Sekunden...'.format(c + 1, num_tries - 1,
                                                                                                d - 1), ())

                time.sleep(1)

        # No DeltaGen connection, abort
        self.display_msg.emit('Konnt keine Verbindung zu einer DeltaGen Instanz mit geladener Szene herstellen.',
                              ('Tja', None))

        self.nc.close()

        return False

    @pyqtSlot()
    def send_variants(self):  # A slot takes no params
        # Connection check timeout, can take a while when GI or RT is active
        timeout = 3
        if self.render_dict:
            timeout = 20

        self.status.emit('Prüfe Verbindung...')

        if not self.connect_to_deltagen(timeout):
            if self.abort_connection:
                self.exit_thread()
                return

            self.no_connection.emit()
            self.finished.emit()
            return

        if self.viewer:
            self.status.emit('Viewer freeze...')
            try:
                self.nc.send('SIZE VIEWER 320 240; FREEZE VIEWER;')
            except:
                LOGGER.error('Sending viewer freeze command failed.')

        # Subscribe to variant states
        self.nc.send('SUBSCRIBE VARIANT_STATE;')

        if self.render_dict:
            self.status.emit('Beginne Rendering...')
            self.render_loop()

            # Abort signal
            QtWidgets.QApplication.processEvents()
            if self.abort_connection:
                self.exit_thread()
                return
        else:
            # Abort signal
            QtWidgets.QApplication.processEvents()
            if self.abort_connection:
                self.exit_thread()
                return

            # Send variants
            for idx, variant in enumerate(self.variants_list):
                time.sleep(0.001)
                self.send_and_check_variant(variant, idx)

                # Abort signal
                QtWidgets.QApplication.processEvents()
                if self.abort_connection:
                    self.exit_thread()
                    return

        self.exit_thread()

    def restore_viewer(self):
        try:
            self.nc.send('SIZE VIEWER ' + self.viewer_size + '; UNFREEZE VIEWER;')
        except:
            LOGGER.error('Sending viewer freeze command failed.')

    def send_and_check_variant(self, variant, idx):
        """
            Send variant switch command and wait for variant_state EVENT
            variant: VARIANT SET STATE; as string
            idx: List index as integer, identifies the corresponding item in self.variants_list in thread class
        """
        self.status.emit('Schaltung wird gesendet...')

        # Extract variant set and value
        var_split = variant.split(' ', 2)
        if len(var_split) == 3:
            variant_set = var_split[1]
            variant_value = var_split[2]
        else:
            LOGGER.error('Invalid variant will be skipped: %s Index: %s', variant, idx)
            return

        # Index of Item in variants_list
        var_idx = idx

        # Extra feedbackloop
        if self.long_render_timeout:
            self.nc.deltagen_is_alive(20)

        # Send variant command
        self.nc.send(variant)

        # Check variant state y/n
        if self.check_variants:
            if self.long_render_timeout:
                recv_str = self.nc.receive(2)
            else:
                # Receive Variant State Feedback
                recv_str = self.nc.receive()
        else:
            recv_str = None

        if recv_str is None:
            recv_str = ''

        # Feedback should be: 'EVENT variant_state loaded_scene_name variant_idx'
        if recv_str:
            # Split into: ['EVENT variant_state scene2 ', 'variant_set', ' ', 'variant_state', '']
            recv_str = recv_str.split('"', 4)
            if len(recv_str) >= 4:
                variant_recv_set = recv_str[1]
                variant_recv_val = recv_str[3]
            else:
                variant_recv_set = ''
                variant_recv_val = ''

            # Compare if Feedback matches desired variant state
            if variant_recv_set in variant_set:
                # Set column to set to green
                variant_set = 1
            else:
                variant_set = False

            if variant_recv_val in variant_value:
                # Set column to set to green
                variant_value = 2
            else:
                variant_value = False
        else:
            variant_set, variant_value = False, False

        # Signal results: -index in list-, set column, value column
        self.strReady.emit(var_idx, variant_set, variant_value)

    @staticmethod
    def return_time(only_minutes=False):
        date_msg = time.strftime('%Y-%m-%d')
        time_msg = time.strftime('%H:%M:%S')

        if only_minutes:
            return time_msg
        else:
            return date_msg + ' ' + time_msg

    def create_directory(self, dir, fallback_name):
        dir = Path(dir)

        if not dir.exists():
            try:
                dir.mkdir(parents=True)
            except:
                LOGGER.critical('Could not create rendering directory! Rendering to executable path.')
                dir = HELPER_DIR.parents[0] / fallback_name
                dir = dir.absolute()

        return dir

    def init_render_log(self):
        self.render_log_name = 'RenderKnecht_Log_' + str(time.time()) + '.log'
        self.render_log = ''
        self.render_log += Msg.RENDER_LOG[0] + self.return_time() + '\n\n'

    def render_loop(self):
        """ Render Loop """
        # List of paths to rendered img files
        self.img_list = []
        img_count = 0
        self.init_render_log()

        # Render Path
        out_dir_name = 'out_' + str(time.time())
        self.out_dir = HELPER_DIR.parents[0] / out_dir_name

        if self.render_user_path:
            self.out_dir = self.render_user_path / out_dir_name

        self.out_dir = self.out_dir.absolute()
        self.out_dir = self.create_directory(self.out_dir, out_dir_name)
        self.initial_out_dir = self.out_dir
        LOGGER.info('Output Directory: %s', self.out_dir)

        # Display render path in overlay
        self.strReady.emit(-1, Msg.OVERLAY_RENDER_DIR, str(self.out_dir))

        # Iterate Render Presets's
        for r in range(0, len(self.render_dict.items())):
            sampling = self.render_dict[r].get('sampling')
            resolution = self.render_dict[r].get('resolution')
            file_extension = self.render_dict[r].get('file_extension')
            render_preset_name = self.render_dict[r]['render_preset_name']

            # Create Render Preset Output Directory
            if self.create_render_preset_dir:
                # Replace invalid file name characters
                for k, v in INVALID_CHR.items():
                    render_preset_name = render_preset_name.replace(k, v)

                new_out_dir = self.initial_out_dir / render_preset_name
                self.out_dir = self.create_directory(new_out_dir, out_dir_name)
                LOGGER.debug('Created Render Preset directory: %s', self.out_dir.name)

            try:
                samples = str(2 ** int(sampling))
                self.render_log += render_preset_name + ' Einstellungen - '
                self.render_log += 'Sampling: 2^' + sampling + ' ' + samples + ' - Res: '
                self.render_log += resolution.replace(' ', 'x') + 'px - Ext: ' + file_extension + '\n\n'
            except:
                pass

            # Make sure we render even if no viewset supplied
            if self.render_dict[r]['viewsets'] == []:
                self.render_dict[r]['viewsets'].append('Dummy')

            self.render_start_time = time.time()

            # Render Preset preset's / reference's (one image per reference)
            for preset in self.render_dict[r]['preset'].items():
                # unpack tuple
                idx, preset = preset

                # Iterate Render Preset viewset's
                for viewset in self.render_dict[r]['viewsets']:
                    # Ascend image number for all images in all Render Preset's
                    img_count += 1

                    # Call render method
                    self.render_preset(img_count, preset, viewset, sampling, resolution, file_extension)

                    # Abort signal
                    QtWidgets.QApplication.processEvents()
                    if self.abort_connection: return

            if self.create_render_preset_dir:
                try:
                    with open(self.out_dir / self.render_log_name, 'w') as e:
                        print(self.render_log, file=e)
                    self.init_render_log()
                except:
                    pass

        # Convert rendered images
        self.status.emit('Konvertiere Bilddaten...')
        if self.convert_to_png and self.img_list:
            self.render_log += create_png_images(self.img_list, self.create_render_preset_dir)

        # Create log file after rendering complete
        try:
            with open(self.initial_out_dir / self.render_log_name, 'w') as e:
                print(self.render_log, file=e)
        except Exception as e:
            LOGGER.error('Error saving render log file: %s', e)

    def render_preset(self, img_count, preset, viewset, sampling, resolution, file_extension):
        """ Sub loop, switch variants and render current preset """
        # Make sure we are not assigning objects with +=
        name = preset.get('name')
        variant_list = []
        variant_list += preset.get('variants')

        # Viewset name if supplied as "Variant Viewset View;"
        viewset_name = viewset.split(' ', 2)
        if len(viewset_name) >= 2:
            # VARIANT #_Shot Shot;
            viewset_name = '_' + viewset_name[2].replace(';', '')
            variant_list.append(viewset)
        else:
            viewset_name = ''

        # Output Image Name
        img_name = '{:03d}_{name}{viewset}{ext}'.format(img_count, name=name, viewset=viewset_name, ext=file_extension)

        # Replace invalid file name characters
        for k, v in INVALID_CHR.items():
            img_name = img_name.replace(k, v)

        LOGGER.info('Rendering: %s\nAA: %s RES: %s EXT: %s', img_name, sampling, resolution, file_extension)
        self.render_log += self.return_time() + ' ' + Msg.RENDER_LOG[1] + img_name + '\n' + Msg.RENDER_LOG[2]

        # Send variants
        for idx, variant in enumerate(variant_list):
            time.sleep(0.001)
            self.send_and_check_variant(variant, idx)

            self.render_log += variant.replace('VARIANT ', '')

            # Abort signal
            QtWidgets.QApplication.processEvents()
            if self.abort_connection: return

        self.render_log += '\n\n'

        time.sleep(0.1)
        # Send settings command
        self.nc.send('IMAGE_SAA_QUALITY VIEWER ' + sampling)

        # Rendering command
        time.sleep(0.1)
        img_file_path = self.out_dir / img_name

        # Build img list for conversion
        self.img_list.append(img_file_path)

        # Feedbackloop before render command
        if self.long_render_timeout:
            self.nc.close()
            time.sleep(1)
            # Subscribe to variant states
            self.nc.send('SUBSCRIBE VARIANT_STATE;')
            time.sleep(1)

        self.nc.deltagen_is_alive(20)

        # Render command
        self.nc.send('IMAGE "' + str(img_file_path) + '" ' + str(resolution) + ';')

        # Calculate render time
        if img_count == 1: self.render_start_time = time.time()
        render_time, image_num = self.calc_render_time(self.render_dict)

        # Wait until image was created
        while not img_file_path.exists():
            time.sleep(1)
            render_display = self.calculate_remaining(render_time, img_count, image_num)
            self.status.emit('Rendering ' + render_display)

            QtWidgets.QApplication.processEvents()
            if self.abort_connection: return

        # Verify a valid image file was created
        self.status.emit('Prüfe Bilddaten...')
        self.verify_rendered_image(img_file_path)

        # Image created
        self.status.emit('Rendering erzeugt.')
        time.sleep(0.5)

        # Wait 5 seconds for DeltaGen to recover
        for count in range(2, 0, -1):
            self.status.emit('Erzeuge nächstes Bild in ' + str(count) + '...')
            time.sleep(1)

    def verify_rendered_image(self, img_path, timeout=3300):
        """ Read rendered image with ImageIO to verify as valid image or break after 55mins/3300secs """
        begin = time.time()
        img = False
        exception_message = ''

        if self.long_render_timeout:
            # Long render timeout eg. A3 can take up to 40min to write an image
            # wait for 30min / 1800sec
            timeout = 1800

        while 1:
            QtWidgets.QApplication.processEvents()
            if self.abort_connection: return

            try:
                # Try to read image
                img = imread(str(img_path))
                img = True
            except ValueError or OSError as exception_message:
                """ Value error if format not found or file incomplete; OSError on non-existent file """
                if time.time() - begin < 11:
                    LOGGER.debug('Rendered image could not be verified. Verification loop %s sec.\n%s', timeout,
                                 exception_message)

                # Display image verification in Overlay
                try:
                    msg = Msg.OVERLAY_RENDER_IMG_ERR + str(img_path.name)
                    self.display_msg.emit(msg, ())
                except Exception as e:
                    LOGGER.error('Tried to send overlay message. But:\n%s', e)

                QtWidgets.QApplication.processEvents()
                # Wait 10 seconds
                time.sleep(10)

            if img:
                del img
                LOGGER.debug('Rendered image was verified as valid image file.')

                # Display image verification in Overlay
                try:
                    msg = Msg.OVERLAY_RENDER_IMG + str(img_path.name)
                    self.display_msg.emit(msg, ())
                except Exception as e:
                    LOGGER.error('Tried to send overlay error message. But:\n%s', e)

                break

            # Timeout
            if time.time() - begin > timeout:
                LOGGER.error('Rendered image could not be verified as valid image file after %s seconds.', timeout)
                self.render_log += '\nDatei konnte nicht als gültige Bilddatei verfiziert werden: ' + str(
                    img_path) + '\n'

                try:
                    if exception_message:
                        self.render_log += exception_message + '\n'
                except UnboundLocalError:
                    # exception_message not defined
                    pass

                break

    def calculate_remaining(self, render_time, img_count, image_num):
        """ Returns remaining time in hh: mm: ss """
        # If image rendered faster than estimated, show progress in progress bar
        elapsed_delta = 0
        render_time = int(render_time)

        if img_count > 1:
            elapsed_delta = (render_time / max(1, image_num)) * (img_count - 1)

        # Render time passed by
        render_seconds_elapsed = int(time.time() - self.render_start_time)
        # Remaining time in seconds
        render_seconds_remaining = max(0, render_time - render_seconds_elapsed)

        # Update Progress bar
        progress = max(render_seconds_elapsed, elapsed_delta) * 100 / max(1, render_time)
        progress = min(100, max(1, progress))
        self.render_progress.emit(int(progress))

        # 0h:00min:00sec
        return time_string(render_seconds_remaining)

    @staticmethod
    def calc_render_time(render_dict):
        """ Calculate render time in seconds """
        render_time = 0
        image_num_all = 0

        for r in range(0, len(render_dict.items())):
            # Sampling
            sampling = 2 ** int(render_dict[r].get('sampling'))

            # Resolution X
            resolution = render_dict[r].get('resolution')
            res_x = 0
            if len(resolution.split(' ')) >= 1:
                res_x = int(resolution.split(' ')[0])

            # Number of viewsets
            if render_dict[r]['viewsets'] == []:
                viewset_num = 1
            else:
                viewset_num = 0
                for viewset in render_dict[r]['viewsets']:
                    viewset_num += 1

            # Number of presets
            preset_num = 0
            for idx, preset in render_dict[r]['preset'].items():
                preset_num += 1
            preset_num = max(1, preset_num)
            image_num = viewset_num * preset_num
            image_num_all += image_num

            sampling_factor = res_x * sampling
            resolution_factor = res_x * RENDER_RES_FACTOR
            render_preset_time = sampling_factor * RENDER_MACHINE_FACTOR * resolution_factor
            render_preset_time = render_preset_time * image_num
            render_time += render_preset_time

        return render_time, image_num_all
