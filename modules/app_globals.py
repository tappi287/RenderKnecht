"""
app_globals for py_knecht. Initializes global variables and sets up paths.

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

import sys
import os
import time
import shutil
from pathlib import Path

from PyQt5 import QtCore

from modules.app_strings import *


class ItemColumn:
    # Column containing description
    DESC = 6
    # Column containing ID
    ID = 5
    # Column containing referenced ID
    REF = 4
    # Column containing type
    TYPE = 3
    # Column containing value
    VALUE = 2
    # Column containing name
    NAME = 1
    # Column containing order
    ORDER = 0
    # Type description
    TYPE_DESC = {
        1000: 'Preset',
        1001: 'Variante',
        1002: 'Referenz',
        1003: 'Render Preset',
        1004: 'Render Einstellung',
        1005: 'Separator',
        1006: 'Varianten Separator'}

    COLUMN_KEYS = ['order', 'name', 'value', 'type', 'reference', 'id', 'description']


"""
# Column containing description
DESC_COL = 6
# Column containing ID
ID_COL = 5
# Column containing referenced ID
REF_COL = 4
# Column containing type
TYPE_COL = 3
# Column containing value
VALUE_COL = 2
# Column containing name
NAME_COL = 1
# Column containing order
ORDER_COL = 0
"""
# Translated column names
COLUMN_NAMES = [
    'Order', 'Name', 'Wert', 'Typ', 'Referenz', 'Id', 'Beschreibung']

# Render Calculation
# 1280px x will be 1, 2560px x will be 2 @NeMo4:3
RENDER_RES_FACTOR = 0.00078125
# Machine with 72 cores @2,4GHz, 12 cores @4GHz would be 0,004
RENDER_MACHINE_FACTOR = 0.00105
# RenderTime would be
# render_time = (resolution_x * sampling) * RENDER_MACHINE_FACTOR * (resolution_x * RENDER_RES_FACTOR)

# Extra long render nc.receive(timeout)
_EXTRA_RENDER_RECEIVE_TIMEOUT = 3

# Default, read from source presets, do not search for references in them if they are in source widget(for performance)
DEFAULT_TYPES = [
    'trim_setup', 'options', 'package', 'reset', 'viewset', 'fakom_setup',
    'fakom_option']


class Itemstyle:
    """ Defines icon names and paths """
    # Preset_Type: icon_name
    TYPES = {
        'trim_setup': 'car',
        'fakom_setup': 'fakom_trim',
        'fakom_option': 'fakom',
        'options': 'options',
        'package': 'pkg',
        'reset': 'reset',
        'viewset': 'view',
        'viewset_mask': 'viewset_mask',
        'preset': 'preset',
        'preset_mask': 'preset_mask',
        'preset_ref': 'preset_ref',
        'OPT': 'img', 'COL': 'img',
        'RAD': 'img_free', 'SWL': 'img_free', 'SEA': 'img_free',
        'render_preset': 'render',
        'sampling': 'render',
        'file_extension': 'render',
        'resolution': 'render',
        'copy': 'copy',
        'checkmark': 'checkmark',
        'seperator': 'empty'}

    SEP_STRINGS = (' ', '-')

    # Column to style with type icons
    COLUMN = 0

    # Main icons
    MAIN = {
        'reset_state': 'reset_state',
        'close': 'close',
        'link_intact': 'link_intact',
        'link_broken': 'link_broken',
        'link_contained': 'link_contained',
        'sad': 'sad',
        'save': 'log_in',
        'update': 'update',
        'empty': 'empty',
        'trash': 'trash',
        'copy': 'clip_copy',
        'checkmark': 'checkmark',
        'paste': 'clip_paste',
        'cut': 'clip_cut',
        'color': 'color',
        'paint': 'paint-color',
        'folder': 'folder',
        'c_purple': 'c_purple',
        'c_yellow': 'c_yellow',
        'c_cyan': 'c_cyan',
        'c_grey': 'c_grey',
        'c_darkgrey': 'c_darkgrey',
        'qob': 'qob_icon',
        'qob_menu': ':/main/qob_menu.png',
        'qob_red': 'qob_icon_red'
        }

    # UI will load icons from this path
    # MAIN[name] = QIcon(icon_path)
    ICON_PATH = {
        # Type Icons
        'car': ':/type/car.png',
        'fakom': ':/type/fakom.png',
        'fakom_trim': ':/type/fakom_trim.png',
        'options': ':/type/options.png',
        'pkg': ':/type/pkg.png',
        'reset': ':/type/reset.png',
        'view': ':/type/viewset.png',
        'preset': ':/type/preset.png',
        'preset_mask': ':/type/preset_mask.png',
        'preset_ref': ':/type/preset_ref.png',
        'img': ':/type/img.png',
        'img_free': ':/type/img_free.png',
        'img_path': ':/type/img_path.png',
        'render': ':/type/render.png',
        'copy': ':/type/copy.png',
        'viewset_mask': ':/type/viewset_mask.png',
        'empty': None,
        # Main icons
        'link_intact': ':/main/link-intact.png',
        'link_broken': ':/main/link-broken.png',
        'link_contained': ':/main/link-contained.png',
        'coffee': ':/main/coffee.png',
        'send': ':/main/forward.png',
        'reset_state': ':/main/reset_state.png',
        'sad': ':/main/sad.png',
        'log_in': ':/main/log-in.png',
        'update': ':/main/update-ready.png',
        'color': ':/main/paint.png',
        'paint-color': ':/main/paint-color.png',
        'c_purple': ':/ovr/c_purple.png',
        'c_yellow': ':/ovr/c_yellow.png',
        'c_cyan': ':/ovr/c_cyan.png',
        'c_grey': ':/ovr/c_grey.png',
        'c_darkgrey': ':/ovr/c_darkgrey.png',
        'close': ':/main/close.png',
        'clip_copy': ':/main/clip_copy.png',
        'clip_paste': ':/main/clip_paste.png',
        'clip_cut': ':/main/clip_cut.png',
        'trash': ':/main/trash-a.png',
        'folder': ':/main/folder.png',
        # Wizard
        'checkmark': ':/type/checkmark.png',
        'qob_icon': ':/main/hal-icon.png',
        'qob_icon_red': ':/main/hal-icon_red.png',
        'qob_icon_sw': ':/main/hal-icon.png',
        'banner': ':/ovr/banner.png'}

    # Color Rgb values as tuples
    COLOR = {'GREEN': (226, 250, 202),
             'ORANGE': (253, 220, 204),
             'BLUE': (202, 226, 250),
             'YELLOW': (200, 200, 90),
             'PURPLE': (180, 80, 220),
             'CYAN': (80, 240, 240),
             'DARKGREY': (140, 140, 140),
             'GREY': (200, 200, 200)}

    # Fonts
    FONT = {'Inconsolata': ':/font/Inconsolata-Regular.ttf'}

    # Send to DG / Render button style
    DG_BTN_READY = '* {background: rgb(234, 234, 234); color: rgb(42, 42, 42);' \
                   'border: 2px solid rgb(134, 134, 134); ' \
                   'padding-left: 10px; padding-right: 10px;}\n*:hover {background: rgb(255,255,255)}'
    DG_BTN_BUSY = '* {background: rgb(234, 234, 234); color: rgb(70, 70, 70);' \
                  'border: 2px solid rgb(134, 134, 134); ' \
                  'padding-left: 10px; padding-right: 10px;}\n*:hover {background: rgb(50,50,50);}'


# DeltaGen address
TCP_IP = 'localhost'
TCP_PORT = 3333

INVALID_CHR = {
    'ä': 'ae',
    'ü': 'ue',
    'ö': 'oe',
    'ß': 'ss',
    'é': 'e',
    '@': '',
    '®': '',
    '~': '',
    '+': '',
    '€': '',
    ' ': '_',
    '\\': '',
    '/': '',
    ':': '',
    '*': '',
    '?': '',
    '"': '',
    '<': '',
    '>': '',
    '|': '',
    '^': '',
    '°': ''
}

# Helper Constants
EXE_NAME = 'RenderKnecht_String-Kerker.exe'
_UPDATER_NAME = 'py_knecht_exe_updater.exe'
VERSION_URL = 'https://github.com/tappi287/RenderKnecht/raw/master/dist/version.txt'
UPDATE_EXE_URL = 'https://github.com/tappi287/RenderKnecht/raw/master/dist/' + EXE_NAME
_HELPER_DIR_NAME = '_RenderKnecht-Work'
_GUI_DIR_NAME = 'gui'
_GUI_RES_NAME = 'gui/res'
_START_UP_FILE_NAME = 'Varianten_XML_1.xml'
_SAVE_CUR = 'current_file.txt'
_CONVERSION_FILE = 'Convert-Varianten-to-xml_v2.bat'
_TEMP_DIR = Path(os.getenv('TEMP') + '/RenderKnecht_tmp/')
_DOCS_DIR = Path('docs')

_SRC_TEMP_XML = 'current_default_presets.xml'
_DEST_TEMP_XML = 'current_user_presets.xml'

# Leading zeros, target is str().rjust(LEADING_ZEROS, '0')
_LEADING_ZEROS = 3

# Ui file names
_UI_LOG = 'RenderKnecht_Gui_Log_Window.ui'
_UI_PRESET_EDITOR = 'RenderKnecht_Gui_Preset_Editor.ui'
_UI_EXCEL = 'RenderKnecht_Excel_Reader.ui'
_UI_FAKOM = 'RenderKnecht_Fakom_Lutscher.ui'
_UI_ABOUT = 'RenderKnecht_Gui_About.ui'
_UI_PRESET_WIZARD = 'RenderKnecht_Image_Wizard.ui'
_UI_PRESET_WIZARD_PAGE_PRESET = 'RenderKnecht_Image_Wizard_Preset_Page.ui'
_UI_PRESET_WIZARD_PAGE_FAKOM = 'RenderKnecht_Image_Wizard_Fakom_Page.ui'
_UI_PRESET_WIZARD_PAGE_SOURCE = 'RenderKnecht_Image_Wizard_Source_Page.ui'
_UI_PRESET_WIZARD_PAGE_RESULT = 'RenderKnecht_Image_Wizard_Result_Page.ui'
_UI_UPDATER = 'RenderKnecht_Updater.ui'
_UI_SEARCH = 'RenderKnecht_Gui_Search_Replace.ui'
_UI_POS_WIN = 'POS_Schnuffi.ui'
_UI_POS_FILE = 'POS_Schnuffi_File_Dialog.ui'
_UI_SPLASH_SCREEN = 'Splash_Screen.gif'
_UI_DARK_STYLE_SHEET = 'rk_fusion_dark.qss'
_DOC_FILE = 'RenderKnecht Dokumentation.chm'

# Log file names
_LOG_FILE = 'RenderKnecht_log_file'


class SocketAddress:
    """ Pfad Aeffchen socket addresses """
    main = ('localhost', 9005)
    watcher = ('localhost', 9006)
    time_out = 20

    # Service broadcast
    service_magic = 'paln3s'
    service_port = 52121

    # List of valid IP subnet's
    valid_subnet_patterns = ['192.168.178', '192.168.13']


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS',
                        os.path.dirname(os.path.abspath(__file__ + '/..')))
    return os.path.join(base_path, relative_path)


def create_work_files(src, dest):
    """ Create files in HELPER_DIR """
    # Source folder in temp directory
    src = src / _HELPER_DIR_NAME

    # Work folder in executable directory
    dest = dest / _HELPER_DIR_NAME

    # Create Helper dir
    if not os.path.exists(dest):
        os.mkdir(dest)

    # Copy files
    if not os.path.exists(dest / _CONVERSION_FILE):
        try:
            shutil.copy(src / _CONVERSION_FILE, dest / _CONVERSION_FILE)
        except Exception as e:
            print(e)

    if os.path.exists(dest / _UPDATER_NAME):
        try:
            os.remove(dest / _UPDATER_NAME)
        except Exception as e:
            print(e)

    if not os.path.exists(dest / _UPDATER_NAME):
        try:
            shutil.copy(src / _UPDATER_NAME, dest / _UPDATER_NAME)
        except Exception as e:
            print(e)


# Frozen or Debugger
if getattr(sys, 'frozen', False):
    # running in a bundle
    run_in_ide = False

    # Application Path - use absolute paths in frozen
    script_dir = Path(resource_path(''))
    executable_dir = Path()

    create_work_files(script_dir, executable_dir)

    # FreeImg Libary for imageIo
    lib_name = 'freeimage-3.15.1-win64.dll'
    rel_lib = Path('modules/' + lib_name)
    os.environ['IMAGEIO_FREEIMAGE_LIB'] = str(script_dir / rel_lib)

    # Info Msg
    InfoMessage.ENV = '<br>Anwendung läuft in pyinstaller bundle. Benutze Standard Log Konfiguration.<br>'

    _DOCS_DIR = script_dir
    print('BASEPATH: ', script_dir)
else:
    # running live DEV
    run_in_ide = True

    # Application Path - use relative paths in dev
    script_dir = Path()
    executable_dir = script_dir

    # FreeImg Libary for imageIo
    lib_name = 'freeimage-3.15.1-win64.dll'
    rel_lib = Path('modules/' + lib_name)
    os.environ['IMAGEIO_FREEIMAGE_LIB'] = str(script_dir / rel_lib)

    # Info msg
    InfoMessage.ENV = '<br>Anwendung läuft in Dev. Benutze _LOG_CONF_DEV<br>'

print('BASEPATH: ', script_dir)

# Global Paths
HELPER_DIR = executable_dir / _HELPER_DIR_NAME
RENDER_BASE_PATH = executable_dir
GUI_DIR = script_dir / _GUI_DIR_NAME
GUI_RES_DIR = script_dir / _GUI_RES_NAME
TEMP_DIR = script_dir

# Conversion Script file
convertVariantsScript = HELPER_DIR / _CONVERSION_FILE


# Save last log file on application exit
def save_last_log():
    global _LOG_FILE, LOG_FILE
    last_filename = Path(LOG_FILE).stem + '_last.log'
    last_log = HELPER_DIR / last_filename

    # overwrite
    try:
        if Path(LOG_FILE).exists():
            Path(LOG_FILE).replace(last_log)
        else:
            shutil.copy(LOG_FILE, last_log)
            os.remove(LOG_FILE)
    except Exception as e:
        print(e)


# Remove old log file on startup
try:
    for log_file in Path(HELPER_DIR).glob(_LOG_FILE + '*last.log'):
        if Path(log_file).exists():
            # Rename/Replace exisiting log
            os.remove(log_file)
            break
except Exception as e:
    print(e)

# Log files
log_file_name = _LOG_FILE + '_' + str(time.time()) + '.log'
LOG_FILE = HELPER_DIR / log_file_name

# Ui files
UI_FILE_LOG_WINDOW = GUI_DIR / _UI_LOG
UI_FILE_PRESET_EDITOR = GUI_DIR / _UI_PRESET_EDITOR
UI_FILE_EXCEL_WINDOW = GUI_DIR / _UI_EXCEL
UI_FILE_FAKOM_WINDOW = GUI_DIR / _UI_FAKOM
UI_FILE_ABOUT_WINDOW = GUI_DIR / _UI_ABOUT
UI_FILE_PRESET_WIZARD = GUI_DIR / _UI_PRESET_WIZARD
UI_POS_WIN = GUI_DIR / _UI_POS_WIN
UI_POS_FILE = GUI_DIR / _UI_POS_FILE
WIZARD_PAGE_PRESET = GUI_DIR / _UI_PRESET_WIZARD_PAGE_PRESET
WIZARD_PAGE_FAKOM = GUI_DIR / _UI_PRESET_WIZARD_PAGE_FAKOM
WIZARD_PAGE_SOURCE = GUI_DIR / _UI_PRESET_WIZARD_PAGE_SOURCE
WIZARD_PAGE_RESULT = GUI_DIR / _UI_PRESET_WIZARD_PAGE_RESULT
UI_FILE_UPDATER = GUI_DIR / _UI_UPDATER
UI_FILE_SEARCH_DIALOG = GUI_DIR / _UI_SEARCH
UI_SPLASH_FILE = GUI_DIR / _UI_SPLASH_SCREEN
UI_DARK_STYLE_SHEET = GUI_DIR / _UI_DARK_STYLE_SHEET
UI_SIZE = (150, 150, 1600, 1024)

# User Documentation
DOC_FILE = _DOCS_DIR / _DOC_FILE

# Xml Temp Files
SRC_XML = HELPER_DIR / _SRC_TEMP_XML
DEST_XML = HELPER_DIR / _DEST_TEMP_XML

InfoMessage.START_INFO = '<br>Beim Start geladen:<br>' + 'Nüscht.' + '<br>'

# System version info
sys_version_info = '<br>Python %s<br>Platform %s<br>' % (sys.version,
                                                         sys.platform)
InfoMessage.START_INFO += sys_version_info

# Global Settings
LEAD_ZEROS = (_LEADING_ZEROS, '0')
SHOW_SPLASH = True

# PR-Family Filter
PR_FAM_NON = [
    'AAU', 'ABR', 'AED', 'AGM', 'ASG', 'AWV', 'BAT', 'BGK', 'BLB', 'BOW', 'BTA',
    'COC', 'COZ', 'CWV', 'EBB', 'ESI', 'FAD', 'FGS', 'FVS', 'FZS', 'GEN', 'GKH',
    'GKV', 'GMO', 'GSP', 'HAG', 'HER', 'KAR', 'KBV', 'KRM', 'KRQ', 'KRR', 'KRS',
    'KSA', 'KUH', 'LAC', 'LDG', 'LEN', 'LRV', 'MKU', 'MOT', 'PAM', 'QUA', 'RCO',
    'REI', 'REL', 'RER', 'SAH', 'SCR', 'SEA', 'SGK', 'SIZ', 'SNH', 'SNR', 'SVO',
    'SZL', 'TPL', 'TRF', 'TSP', 'TWL', 'TWU', 'VBK', 'WAR', 'WSA', 'ZBR', 'ZSS',
    'ZUH'
]

PR_FAM_INT = [
    'AFH', 'AIB', 'ALG', 'APP', 'ASE', 'ASL', 'ASR', 'ASY', 'ATA', 'AUD', 'BBO',
    'BDH', 'BFA', 'BLE', 'BRS', 'BSV', 'CDR', 'CHA', 'CHR', 'DAE', 'DAT', 'DEI',
    'DEK', 'DFO', 'ECO', 'EIH', 'EMM', 'EPH', 'FEH', 'FHW', 'FIT', 'FLS', 'FSB',
    'GEF', 'GRA', 'GRT', 'GSP', 'GWA', 'HGD', 'HIM', 'HIS', 'HKA', 'HSW', 'HUD',
    'IND', 'INS', 'IRS', 'KAR', 'KAS', 'KLT', 'KOH', 'KOV', 'KMP', 'KMS', 'KSI',
    'LCP', 'LEA', 'LEL', 'LER', 'LIA', 'LOR', 'LRA', 'LSE', 'LSS', 'LUM', 'LWR',
    'MAS', 'MDS', 'MFA', 'MIK', 'NAC', 'NAV', 'PAM', 'QGM', 'RAO', 'RDK', 'RSV',
    'SAB', 'SAG', 'SDH', 'SHM', 'SIB', 'SIE', 'SIH', 'SLM', 'SNA', 'SON', 'SPR',
    'SPU', 'SRH', 'SSH', 'SSR', 'SWS', 'THE', 'TKV', 'TUE', 'TVE', 'VBK', 'VHS',
    'VOS', 'VRH', 'VTV', 'WIN', 'WSS', 'ZAB', 'ZFM', 'ZKV', 'HBV', 'RAU', 'KZV',
    ]

PR_FAM_EXT = [
    'AAU', 'ABO', 'AER', 'AGS', 'AHV', 'ASL', 'ASR', 'ATA', 'AWV', 'BAH', 'BAV',
    'BBO', 'DAR', 'DEI', 'DFO', 'EPH', 'FSP', 'GRA', 'GWA', 'HEB', 'HES', 'HEW',
    'HSW', 'KAR', 'KSU', 'KZV', 'LIA', 'NEL', 'NES', 'RAD', 'SBR', 'SFS', 'SPU',
    'SSH', 'STF', 'SWR', 'SZU', 'TKV', 'TYZ', 'VTV', 'WAL', 'ZIE', 'ZKS',
    ]

PACKAGE_FILTER = ['Argentinien', 'Australien', 'Balkan', 'Baltikum', 'Belgien', 'China', 'Dänemark', 'Export',
                  'Finnland', 'Frankreich', 'GB', 'GUS', 'Great Britain', 'Griechenland', 'Großbritannien',
                  'Großkunden', 'Irland', 'Italien', 'Kroatien', 'Luxemburg', 'Niederlande', 'Norwegen',
                  'Osteuropa', 'Polen', 'Portugal', 'Rumänien', 'Russland', 'Schweden', 'Schweiz',
                  'Singapur', 'Slowakei', 'Slowenien', 'Spanien', 'Tschechien', 'Türkei', 'Ukraine',
                  'Ungarn', 'Österreich']

# PR-Familys read by FaKom Lutscher
FAKOM_READER_PR_FAM = {'SIB', 'LUM', 'VOS'}

# Detail Img Prefixes
DETAIL_PRESET_PREFIXS = {'OPT', 'RAD', 'SWL', 'SEA', 'COL'}

ENABLED_ITEM_FLAGS = (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled |
                      QtCore.Qt.ItemIsDropEnabled)

DISABLED_ITEM_FLAGS = (QtCore.Qt.ItemIsDropEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled)

FAKOM_GRP_ITEM_FLAGS = (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDragEnabled)