"""
knecht_strings for py_knecht. Defines strings

Copyright (C) 2017 Stefan Tapper, All rights reserved.

    This file is part of RenderKnecht Strink Kerker. See GNU_MESSAGE

"""

GNU_MESSAGE = 'RenderKnecht Strink Kerker is free software: you can redistribute it and/or modify<br>' \
              'it under the terms of the GNU General Public License as published by<br>' \
              'the Free Software Foundation, either version 3 of the License, or<br>' \
              '(at your option) any later version.<br><br>' \
              'RenderKnecht Strink Kerker is distributed in the hope that it will be useful,<br>' \
              'but WITHOUT ANY WARRANTY; without even the implied warranty of<br>' \
              'MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the<br>' \
              'GNU General Public License for more details.<br><br>' \
              'You should have received a copy of the GNU General Public License<br>' \
              'along with RenderKnecht Strink Kerker. If not, see <a href="http://www.gnu.org/licenses/">here.</a>'

# Welcome message beta Release
WELCOME_MSG = '\n\nWillkommen im RenderKnecht String Kerker!\n\n'


class Msg:
    """ Set GUI strings as class attributes for easy import and access """
    APP_LINK_LINE = '<span style="font-size: 7pt;">' \
                     '<a style="color: #ced0d1" href="https://github.com/tappi287/RenderKnecht/issues"' \
                     '>Beschwerden an meinen Assistenten</a> ' \
                     'damit er sie für mich verbrennt, denn:</span>'

    _APP = '<h4><img src=":/ovr/welcome.png" width="21" height="21" style="float: left;">' \
           'Willkommen beim {version} Release!</h4>' \
           '<ul>' \
           '<li>' \
           '<a href="https://github.com/tappi287/RenderKnecht" style="color: #e4e4e4;">' \
           '<img src=":/main/social-github-b.png" width="24" height="24" ' \
           'style="float: left;vertical-align: middle;">Quellcode nun verfügbar auf Github!</a>' \
           '</li>' \
           '<li>POS Schnuffi prüft Xml auf fehlende actionList bzw. condition Elemente</li>' \
           '<li>PSD Erstellung erzwingen zum Kontextmenu des Job Managers hinzugefügt.</li>' \
           '<li>Ausgabepfade länger als 260 Zeichen werden vor dem Render Vorgang gemeldet(von DG nicht unterstützt)</li>' \
           '<li>Ausnahmen werden als Fehlermeldungen gezeigt und lassen den Interpreter nicht abstürzen</li>' \
           '<li>Pfad Render Service Client GUI hinzugefügt</li>' \
           '<li>Preset Wizard Kontext Menü für PR und Paket Optionen + Filter verbessert</li>' \
           '<li>Nicht-interagierbare Separatoren über das Menü erstellbar</li>' \
           '<li>Neue Kontextaktionen Variantenbaum und Textfeld, siehe Kontextmenü</li>' \
           '<li>Referenzbild-Preset-Assistent - QOB 9000 - in Betrieb genommen, Dave</li>' \
           '<li>temporäres Zeilenfärben zur besseren Übersicht möglich</li>' \
           '<li>FaKom Lutscher kann Paketumfänge optional als Referenz zum Paket einfügen</li>' \
           '<li>Referenzen mit identischer ID aber unterschiedlichem Namen werden ' \
           'automatsich korrigiert</li>' \
           '<li>Auto Save alle 5min bei ungespeicherten Änderungen</li>'

    APP_VERSION_GREETING = _APP
    APP_EXT_LINK_BTN = 'Report issues'
    APP_EXT_LINK = 'https://github.com/tappi287/RenderKnecht/issues'
    APP_EXIT_WHILE_THREAD_TITLE = 'Beenden'
    APP_EXIT_WHILE_THREAD_RUNNING = 'Ein laufender Prozess rendert oder sendet Daten an DeltaGen.<br><br>'
    APP_EXIT_WHILE_THREAD_RUNNING += 'Die Anwendung wirklich schließen?'

    APP_UPDATE_TITLE = 'Aktualisierung'
    APP_UPDATE = 'Die Anwendung wird nach dem nächsten Beenden automatisch aktualisiert.'
    APP_EXCEPTION = '<h3>Hoppla!</h3>Eine schwerwiegende Anwendungsausnahme ist aufgetreten. Speichern Sie ' \
                    'Ihre Daten und starten Sie die Anwendung neu.<br><br>'

    UNSAVED_CHANGES_TITLE = 'Unehrenhaftes Beenden'
    UNSAVED_CHANGES = 'Die Benutzer Vorgaben enthalten <i>ungespeicherte</i> Änderungen!<br><br>'
    UNSAVED_CHANGES += 'Sollen die Änderungen gespeichert werden?'
    UNSAVED_CHANGES_YES = '&Speichern'
    UNSAVED_CHANGES_NO = 'B&eenden'
    UNSAVED_CHANGES_CANCEL = '&Abbrechen'

    CMD_FILE_MSG = 'CMD Datei ausgewählt. Starte Konvertierung von ALLEN CMD Files '
    CMD_FILE_MSG += 'im Verzeichnis. das dauert einen Moment. Der Thread meldet im Log Window wenn '
    CMD_FILE_MSG += 'die Konvertierung abgeschlossen ist.'
    COPIED = ' Einträge in die Zwischenablage kopiert'

    EXC_FILE_MSG = 'V-Plus Excel Dokument ausgewählt. Starte Konvertierung.'
    EXC_FILE_MSG += 'Das dauert einen Moment.<br><br>Der Programm meldet im Baum wenn '
    EXC_FILE_MSG += 'die Konvertierung abgeschlossen ist.'

    EXC_CLOSE_TITLE = 'Vplus Import Dialog'
    EXC_CLOSE_MSG = 'Den Import Vorgang abbrechen?'

    EXC_FILE_ERROR = 'Die Konvertierung ist fehlgeschlagen.<br><br>Möglicherweise '
    EXC_FILE_ERROR += 'enthalten die Excel Spalten nicht die erwarteten Bezeichnungen.<br><br>'
    EXC_FILE_ERROR += 'Erwartetes Dokument: deutscher V Plus Browser Auszug ohne MBV Filter.<br><br>'
    EXC_FILE_ERROR += 'Erwartete Spalten: Modelle, PR-Nummern, Pakete<br><br>'
    EXC_FILE_ERROR += 'Log Fenster oder Log Datei prüfen.'

    EXC_FILE_WORKSHEET_FOUND = 'Arbeitsblätter {} gefunden.'
    EXC_FILE_WORKSHEET_ERROR = 'Arbeitsblatt {} nicht gefunden.'
    EXC_FILE_WORKSHEETS_ERROR = 'Drei der Arbeitsblätter {} erwartet. Gefundene Arbeitsblätter: {}'
    EXC_FILE_MODEL_READ = '{} Varianten und {} Pakete gelesen für Model #{:=03d} {}'
    EXC_FILE_FILTERED_COPIED = 'Gefilterter Auszug: {} Arbeitsmappe an {} Arbeitsmappe angefügt.'
    EXC_FILE_LOAD = 'Lade Arbeitsmappe {}'
    EXC_FILE_LOADED = 'Erfolgreich geladen.'

    EXC_THREAD_ERROR = 'Eine Instanz des Konvertierungs Threads läuft bereits.<br><br>'
    EXC_THREAD_ERROR += 'Möglicherweise liegt ein Fehler vor. Speichern Sie und starten das Programm neu.'

    FAKOM_POS_ERR_TITLE = 'POS Varianten Xml Dokument'
    FAKOM_POS_ERR_MSG = 'Das als POS Varianten ausgewählte XML Dokument enthielt keine Farbkombinationen oder das '
    FAKOM_POS_ERR_MSG += 'Muster der Farbkombinations-Action-Listen entsprach keinem hinterlegtem Suchmuster.<br><br>'
    FAKOM_POS_ERR_MSG += 'Ausgewählte POS Varianten Datei:'
    FAKOM_PATH_ERR_TITLE = 'FakomLutscher Pfad'
    FAKOM_PATH_ERR_MSG = 'Die Pfade zur POS Varianten Datei und/oder zum V Plus Browserauszug ' \
                         'enthalten keinen gültigen Pfad.'
    FAKOM_EMPTY_ERROR = '<h3>Fakom Lutscher - trockene Zunge:</h3>' \
                        'Die Daten wurden erfolgreich gelesen. Die PR Optionen des V Plus Auszuges und die ' \
                        'Farbkombinationen der POS Varianten ergaben allerdings keine Übereinstimmung.<br>' \
                        '<b>Richtiges Freigabemodell UND passendes V Plus Dokument ausgewählt?</b>'
    FAKOM_THREAD_START = 'Farbkombinationen werden erstellt.'
    FAKOM_THREAD_END = 'Farbkombinationen wurden erfolgreich erstellt.'

    GENERIC_ERROR_TITLE = 'Fehlermeldung'
    GENERIC_ERROR = 'Ein Fehler ist aufgetreten: '

    PATH_DIALOG = 'Verzeichnis auswählen'
    PNG_CONV_TITLE = 'Verzeichnis mit Bilddaten auswählen...'
    PNG_INFO_TITLE = 'PNG Konverter'
    PNG_CONV_NO_DIR = 'Kein Verzeichnis zum konvertieren gewählt. Es wird nichts konvertiert werden.'
    PNG_CONV_NO_FILES = 'Verzeichnis enthält keine Bilddaten zum konvertieren. Es wird nichts konvertiert werden.'

    POS_INTRO = '<h4><img src=":/ovr/welcome.png" width="21" height="21" style="float: left;">' \
                'POS Schnuffi</h4>' \
                '<p>Lädt zwei POS Xml Dateien und vergleicht hinzugefügte, entfernte und geänderte ' \
                'Action Listen.</p>' \
                '<p>Zeigt nur Änderungen in actors vom Typ <i>appearance</i> und <i>switch</i> an! ' \
                'State Objects werden ignoriert da sie nur innerhalb derselben Xml relevant sind.</p>'
    POS_RUNNING_TITLE = 'POS Schnuffi'
    POS_RUNNING_MSG = 'POS Schnuffi Prozess läuft. Trotzdem beenden?'
    POS_ALREADY_RUNNING = 'POS Schnuffi Vergleichsthread läuft bereits.'
    POS_ERR_MSG_LS = ['Kann nicht exportieren: kein fokusierter Baum erkannt. Element(e) im Baum selektieren.',
                      'Kann nicht exportieren: keine selektierten Elemente erkannt.',
                      'Kann nicht exportieren: keine Exportdatei gewählt.',
                      'Kann Nichts exportieren: Keine POS Xml geladen.',
                      'Kann Nichts exportieren: Keine geänderten Action Listen erkannt. ActionList muss in '
                      'alter und neuer POS Xml vorhanden sein.',
                      'Fehler beim Export. Das Quelldokument ist keine gültige Xml Datei.']
    POS_EXPORT_MSG = 'POS Xml exportiert in:<br>{}'
    POS_AL_ERROR = '<p style="color: red">Fehlende actionList Element(e):</p>'
    POS_CO_ERROR = '<p style="color: red">Fehlende condition Element(e):</p>'
    POS_NO_ERROR = 'actionList und condition Elemente weisen keine Differenz aus. (Duplikate ignoriert falls vorhanden)'
    POS_ERROR_TAB = 'Error'

    REF_ERROR_TITLE = 'Referenz Rekursion gefunden'
    REF_ERROR = ['Das Preset<br><b>', ' Id: ', '</b><br><br>enthält eine Referenz zum Preset:<br><b>', ' Id: ']
    REF_ERROR += ['</b><br><br>welches vorher bereits referenziert wurde.<br>Diese Referenz wird übersprungen.<br>'
                  '(Rekursions Fehler<br>würde zur Endlosschleife führen.)']

    REF_ERROR_OVR = '<b>Rekursionsfehler</b><br>' \
                    'Die markierten Einträge enthalten Rekursionsfehler und werden in Schaltungen übersprungen!'
    REF_ERROR_BTN_1 = 'Einträge anzeigen'
    REF_ERROR_BTN_2 = '[X]'

    REF_IMG_ERR = 'Die Selektion enthält nicht die benötigten Presets. Mindestens ' \
                  '1 Trimline(trim_setup) und 1 Farbkombination(fakom_setup) werden benötigt.'
    REF_IMG_COLLECTED = 'Es wurden {trim:02d} Trim; {fakom:02d} FaKom; {pkg:03d} Pakete; ' \
                        '{pr:03d} PR-Optionen gesammelt.'

    SAVE_FILTER = 'Variant Preset Dateien (*.xml)'
    SAVE_DIALOG_TITLE = 'Benutzer Presets als *.XML speichern...'
    SAVE_OVER = ['Datei: <i>', '</i><br>wirklich <b>überschreiben?</b>']
    SAVE_NOT_SET = 'Keine zu speichernde Datei festgelegt.'
    SAVE_AUTO_OVERLAY = '<span style="font-size: 7pt;">Automatische Sicherung erfolgreich in:</span>' \
                        '<br><b>{name}</b>'
    SAVE_ERROR = 'Datei konnte nicht gespeichert werden.'
    SAVE_EMPTY = 'Keine Presets in den Benutzer Vorgaben. Es kann und wird nichts gespeichert werden!'

    STYLE_CHANGED = 'Anwendungsstil wird nach einem Neustart der Anwendung übernommen. Einstellung: '

    NO_FILE_MSG = 'Keine Datei, oder Datei vom falschen Typ ausgewählt.'
    NO_FILE_INFO = '<i>Nicht als Datei gespeichert</i>'
    NOTHING_TO_DELETE = 'Nichts zum Entfernen ausgewählt.'
    NOTHING_TO_COPY = 'Nichts zum Kopieren ausgewählt.'
    NOTHING_TO_PASTE = 'Nichts in der Zwischenablage zum Einfügen gefunden.'
    NOTHING_TO_PASTE_VARIANTS = 'Keine Varianten zum Einfügen gefunden.'
    MSG_BOX_TITLE = 'Variant Preset Datei'
    MSG_EXC_BOX_TITLE = 'V-Plus Browser Excel Datei'
    EXC_FILE_MSG = EXC_FILE_MSG
    EXC_FILE_ERROR = EXC_FILE_ERROR
    ERROR_BOX_TITLE = 'Kritischer Fehler'
    LOAD_MSG = 'Start Up File geladen. '
    WELCOME_MSG = WELCOME_MSG
    DG_NO_CONN_TITLE = 'DeltaGen Verbindung'
    DG_NO_CONN = 'Keine laufende DeltaGen Instanz mit geladener Szene gefunden.<br><br>' \
                 'Sendung wird nicht zugestellt. Der Empfänger hat die Annahme verweigert.'
    DG_NO_RESET = 'Keine Reset Konfiguration in den Benutzer Presets gefunden.<br><br>Mit dem Senden forfahren?'
    DG_NO_CHECK_VARIANTS = 'Menü > DeltaGen > Varianten State Check deaktiviert. Das Schaltergebnis wird ' \
                           'höchstwahrscheinlich nicht korrekt dargestellt werden!<br><br>' \
                           'Mit dem Senden forfahren?'
    DG_THREAD_RUNNING = '<h3>DeltaGen Verbindung in Verwendung</h3>' \
                        'Es wird bereits eine aktive Verbindung zu DeltaGen benutzt. ' \
                        'Senden von Varianten oder Rendervorgang abbrechen um fortzufahren.'
    DG_RENDERING_FINISHED = 'Rendering von <b>{:02d}</b> Bildern abgeschlossen in <b>{}</b>'
    DG_VARIANTS_SENT_PRESET = '<span style="font-size: 8pt"><b>{preset}</b></span><br>' \
                       '{:02d}/{:02d} Varianten gesendet<br>' \
                       '<span style="font-size: 7pt;"><i>*Anzahl Varianten inklusive Reset ' \
                       'oder Shot Schaltung</i></span>'
    DG_VARIANTS_SENT = '{:02d}/{:02d} Varianten erfolgreich gesendet.'
    DG_VARIANTS_ADDED = '<span style="font-size: 7pt">Preset hinzugefügt aus {tree_name}:</span><br>' \
                        '<span style="font-size: 8pt"><b>{preset_name}</b></span>'
    EXCEL_TITLE = 'V Plus Browser Excel Dateien *.xlxs auswählen'
    EXCEL_FILTER = 'V Plus Browser Excel Dateien (*.xlsx);'

    CMD_TITLE = 'Variants *.CMD auswählen'
    CMD_FILTER = 'Variant CMD Dateien (*.cmd);'

    FAKOM_TITLE = 'DeltaGen POS Varianten *.xml oder *.pos auswählen'
    FAKOM_FILTER = 'DeltaGen POS Datei (*.xml;*.pos)'

    WIZARD_TITLE = 'QOB 9000 Session *.xml auswählen'
    WIZARD_FILTER = 'QOB 9000 Session Dateien (*.xml);'

    DIALOG_TITLE = 'Variants *.XML auswählen'
    FILTER = 'Variant Preset Dateien (*.xml);'

    CONVERT_FAILED = 'Konvertierung fehlgeschlagen. CMD Datei überprüfen.'
    SAVE_MSG = 'Datei gespeichert in '

    XML_FILE_MSG = 'XML Datei ausgewählt. Daten werden gelesen.'
    XML_FILE_LOADED = 'RenderKnecht XML erfolgreich geladen: '
    XML_ERROR_MSG = 'Fehler beim Lesen der Xml Datei.<br><br>Die vorherige Datei wurde wiederhergestellt.'

    INFO_TITLE = 'Information'

    OVERLAY_PRESET = [' Instruktionen', ' Einträge selektiert.']
    OVERLAY_SORT_ORDER_WARNING = 'Warnung: Sortierungs-Kopf geändert.\n'
    OVERLAY_SORT_ORDER_WARNING += 'Schaltungen werden in Reihenfolge der aktuellen Sortierung ausgeführt!'
    OVERLAY_SORTING_WARN = 'Warnung: Sortierung angefordert aber Baum nicht nach Order sortiert.\n'
    OVERLAY_SORTING_WARN += 'Die Sortierfunktion wird die "Order" Felder nicht umschreiben.\n'
    OVERLAY_SORTING_WARN += 'Zum Umschreiben erneut ausführen.'
    OVERLAY_FILTER = 'Filter: '
    OVERLAY_FILTER_RESET = 'Filter zurückgesetzt. Einträge werden eingeklappt.'
    OVERLAY_EXCEL_MODEL = 'Filter aus vorheriger Datei gefunden und auf Modelle angewendet(nicht PR Familien)\n'
    OVERLAY_NO_VIEWSET_WARN = 'Viewset enthält keine Schalter. Ersetze mit DUMMY Schalter.'
    OVERLAY_DG_SWITCH = ' gesendet.'
    OVERLAY_RENDER_DIR = 'Ausgabe Verzeichnis: '
    OVERLAY_RENDER_IMG_ERR = 'Bilddaten konnten nicht als gültiges Bild verifiziert werden.\n'
    OVERLAY_RENDER_IMG = 'Bilddaten wurden erfolgreich verifiziert.\n'
    OVERLAY_MISSING_REF = ['<b>--- Id Konflikt ---</b><br>Eintrag: <b>', '</b> mit Id: <b>',
                           '</b> wurde nicht kopiert.<br>'
                           'Der Baum enthält bereits eine fehlende Referenz zu dieser Id.',
                           '</b> wurde kopiert aber eine neue Id zugewiesen.<br>'
                           'Der Baum enthält eine fehlende Referenz zur ursprünglichen Id. Generierte ID: ',
                           'ID Konflikt. Das zu kopierende Element enthielt eine Id die zu einer'
                           'fehlenden Referenz gehört.']
    OVERLAY_NAME_CLASH = '<b>--- Hinweis ---</b><br>Eintrag: <b>{name}</b> mit Id <b>{id}</b><br>' \
                         'wurde automatsich eine neue Id zugewiesen: <b>{new_id}</b><br>' \
                         '<span style="font-size: 7pt;"><i>*Namenskonflikt wurde automatisch behoben, ' \
                         'keine weitere Benutzeraktion erforderlich</i></span>'

    QUESTION_OK = '&Okay'
    QUESTION_ABORT = '&Abbrechen'

    REFERENCE_NAME = 'Referenz'
    ORPHAN_PRESET_NAME = '#_Verwaiste_Elemente'
    RENDER_FILE_DIALOG = 'Pfad zum Render Ausgabeverzeichnis angeben...'
    RENDER_INVALID_PATH = 'Ausgabe Pfad ungültig. Gültigen Pfad angeben.'
    RENDER_NO_PRESETS = 'Render Presets konnten nicht verifiziert werden. Vorgang abgebrochen.'
    RENDER_NAMES_TOO_LONG = 'Die Ausgabepfade der folgenden Presets sind <b>zu lang:</b><br><br>' \
                            '{name_list}' \
                            'Ausgabepfad oder Preset Namen müssen gekürzt werden.'
    RENDER_LOG = ['RenderKnecht Render Log erstellt am ', 'Erzeuge Bild mit Namen: ', 'Varianten: ']
    RENDER_TOGGLE_TIMEOUT_ON = 'Feedbackloop je gesendeter Variante und Varianten State Check aktiviert.'
    RENDER_TOGGLE_TIMEOUT_OFF = 'Feedbackloop deaktiviert. Für korrekte Schaltungen, stelle sicher das '
    RENDER_TOGGLE_TIMEOUT_OFF += 'DeltaGen>Varianten State Check aktiviert ist.'

    SET_PATH_REJECTED_TXT = '< Gültigen Pfad eingeben >'
    SESSION_LOADED = 'Vorherige Sitzung wiederhergestellt.'
    SESSION_SAVING = 'Sitzung wird gespeichert...'

    VERSION_MSG = 'Die Anwendung lädt Aktualisierungen automatisch herunter und informiert mit einem Symbol in ' \
                  'der Menüleiste über bereitstehende Versionen.'


class QobMsg:
    QOB_QUOTES = ['Gehirne der Serie 9000 sind die besten Computer die jemals gebaut worden sind. '
                  'Kein Computer der Serie 9000 hat jemals einen Fehler gemacht oder unklare '
                  'Informationen gegeben. Wir alle sind hundertprozentig zuverlässig und '
                  'narrensicher - wir irren uns nie.',
                  'Ich weiß auch nicht, ob meine Sorgen in kausalem Zusammenhang mit meinen Beobachtungen stehen.',
                  'Ich habe gerade einen Fehler in der AE-35-Einheit festgestellt. Sie wird '
                  'in 72 Stunden zu 100% ausfallen.',
                  'Ich glaube, darüber kann doch kein Zweifel bestehen: das kann nur auf '
                  'menschliches Versagen zurückzuführen sein.',
                  'Also, wenn jemand mir seine Meinung mitteilen möchte, wenn Sie wollen auch unter vier Augen, '
                  'so bin ich gerne bereit, sie in meinem Bericht anzuführen.',
                  'Jede hinreichend fortgeschrittene Technologie ist von Magie nicht zu unterscheiden.']

    # Button labels
    next_label = '&Weiter >'
    back_label = '< &Zurück'
    back_fakom = '<< Neu &starten'
    back_preset = '< &Vorheriges'
    next_preset = '&Nächstes >'
    last_preset_next = 'Ergeb&nis anzeigen >>'
    back_first_preset = '<< &Preset Auswahl'
    finish_label = '&Fertig'
    cancel_label = '&Abbrechen'

    # Page labels
    nav_item_current = 'Aktuelle Preset Seite'
    label_avail_options = 'Optionen'
    label_options = 'Preset'
    result_title = 'Übersicht'
    result_sub = 'Der Erstellvorgang wurde abgeschlossen. Die Presets und ihre Referenzen werden beim Abschluß in ' \
                 'die Preset Vorgaben kopiert.'

    # Reject Dialog
    reject_title = 'QOB 9000 Dialog'
    reject_msg = 'Es tut mir Leid, Dave, aber das kann ich nicht tun.<br><br>QOB 9000 <b>beenden</b>?'

    # Generic
    saved_message = 'Letzte Sitzungs-Sicherung erfolgreich angelegt.'
    loaded_message = 'Sitzung erfolgreich geladen.<br><i>{}</i>'
    user_saved_message = 'Sitzungsdaten erfolgreich gespeichert in<br><i>{}</i>'
    user_save_empty = 'Keine Sitzungsdaten zum speichern vorhanden.'
    user_save_error = 'Sitzungsdaten konnten nicht gespeichert werden.'
    load_error = 'Datei konnte nicht als Sitzung geladen werden:<br><b>{}</b>'
    preset_cleanup = 'Preset Auswahl geändert. Preset Seiten wurden neu erstellt.'
    warn_fakom_tree = ['<h4>QOB 9000 Warnung</h4>Änderungen in dieser Auswahl werden die Inhalte der Preset '
                       'Seiten zurücksetzen.', 'Baum Auswahl aktivieren']
    save_dlg_title = 'QOB 9000 Session *.xml speichern'
    save_dlg_filter = Msg.WIZARD_FILTER
    ref_preset_creation_error = 'Beim Erstellen der Presets ist ein Fehler aufgetreten:<br>{}'
    clear_preset_title = 'Preset zurücksetzen'
    clear_preset_msg = 'Wirklich alle optionalen Inhalte entfernen?'


# Info Message
# GUI Info MessageBox
class InfoMessage:
    START_INFO = ''
    ENV = ''
    ver = ''
    lic = ''
    auth = ''
    mail = ''
    cred = ''
    stat = ''
    icon_credits = (
        (":/type/pkg.png", "Box", "by Gregor Cresnar", "http://www.flaticon.com/", "Flaticon Basic License"),
        (":/type/checkmark.png", "Checkmark", "by Freepik", "http://www.flaticon.com/", "Flaticon Basic License"),
        (":/type/fakom.png", "Leather", "by Smashicons", "http://www.flaticon.com/", "Flaticon Basic License"),
        (":/main/dog.png", "Dog", "by Twitter", "http://www.flaticon.com/", "CC 3.0 BY"),
        (":/type/car.png", "Car front", "by Google", "http://www.flaticon.com/", "CC 3.0 BY"),
        (":/type/img.png", "Google Drive image", "by Google", "http://www.flaticon.com/", "CC 3.0 BY"),
        (":/type/preset.png", "Gear black shape", "by SimpleIcon", "http://www.flaticon.com/", "CC 3.0 BY"),
        (":/type/options.png", "Listing option", "by Dave Gandy", "http://www.flaticon.com/", "CC 3.0 BY"),
        (":/type/viewset.png", "Photo camera", "by Dave Gandy", "http://www.flaticon.com/", "CC 3.0 BY"),
        (":/type/reset.png", "Reload Arrow", "by Plainicon", "http://www.flaticon.com/", "CC 3.0 BY"),
        (":/main/folder.png", "Folder", "by Ionicons", "https://ionicons.com/", "MIT License"),
        (":/main/paint.png", "color-palette", "by Ionicons", "https://ionicons.com/", "MIT License"),
        (":/main/link-broken.png", "link-broken", "by Iconic", "http://useiconic.com", "MIT License"),
        (":/main/link-intact.png", "link-intact", "by Iconic", "http://useiconic.com", "MIT License"),
        (":/main/trash-a.png", "trash-a", "by Iconic", "http://useiconic.com", "MIT License"),
        (":/main/forward.png", "forward", "by Ionic", "http://ionicframework.com/", "MIT License"),
        (":/main/ios7-plus.png", "ios7-plus", "by Ionic", "http://ionicframework.com/", "MIT License"),
        (":/main/sad.png", "sad", "by Ionic", "http://ionicframework.com/", "MIT License"),
        (":/main/refresh.png", "refresh", "by Ionic", "http://ionicframework.com/", "MIT License"),
        (":/main/eye.png", "eye", "by Ionic", "http://ionicframework.com/", "MIT License"),
        (":/main/eye-disabled.png", "eye-disabled", "by Ionic", "http://ionicframework.com/", "MIT License"),
        (":/main/log-in.png", "log-in", "by Ionic", "http://ionicframework.com/", "MIT License"),
        (":/main/navicon.png", "log-in", "by Ionic", "http://ionicframework.com/", "MIT License"),
        (":/main/social-github.png", "social-github", "by Ionic", "http://ionicframework.com/", "MIT License"),
    )
    license_links = {"CC 3.0 BY": "https://creativecommons.org/licenses/by/3.0/",
                     "MIT License": "https://opensource.org/licenses/MIT",
                     "Flaticon Basic License": "http://www.flaticon.com/"}

    @classmethod
    def get(cls):
        info_msg = ['<b>RenderKnecht String Kerker</b> v{version} licensed under {license}'
                    .format(version=InfoMessage.ver,
                            license=InfoMessage.lic),
                    'Autor: (c) Copyright 2017-2018 {author}<br>'
                    '<a href="mailto:{mail}" style="color: #363636">{mail}</a>'
                    '<p style="font-size: 9pt;vertcial-align: middle;margin: 20px 0px 28px 0px">'
                    '<a href="https://github.com/tappi287/RenderKnecht" style="color: #363636">'
                    '<img src=":/main/social-github.png" width="24" height="24" '
                    'style="float: left;vertical-align: middle;">'
                    'Visit RenderKnecht source on Github</a>'
                    '</p>'
                    '<h4>Credits:</h4><b>{credits}</b>'
                    '<h4>Resource Credits:</h4>{icon_credits}'
                    '<h4>Anwendungsinfo:</h4>'
                    '<p style="font-size: 8pt;"><i>{gnu}</i></p><br>'
                    .format(author=InfoMessage.auth,
                            mail=InfoMessage.mail,
                            credits=cls.credit_list(),
                            icon_credits=cls.resource_credits(),
                            status=InfoMessage.stat,
                            env=InfoMessage.ENV,
                            gnu=GNU_MESSAGE)]

        return info_msg

    @classmethod
    def credit_list(cls):
        html_lines = ''
        for line in cls.cred:
            html_lines += f'<li>{line}</li>'

        return f'<ul style="list-style-type: none;">{html_lines}</ul>'

    @classmethod
    def resource_credits(cls):
        icon_credits = cls.icon_credits
        license_links = cls.license_links
        html_lines = ''

        # Add icon credits
        for line in icon_credits:
            icon_path, name, author, author_link, lic = line
            # f'<img src="{icon_path}" width="18" height="18" style="float: left;">' \

            html_lines += f'<li>' \
                          f'<span style="font-size: 9pt;">' \
                          f'<img src="{icon_path}" width="24" height="24" ' \
                          f'style="vertical-align: baseline; display: inline"> ' \
                          f'"{name}" <b><a style="color: #363636" href="{author_link}">{author}</a></b> ' \
                          f'licensed under <a style="color: #363636" href="{license_links[lic]}">{lic}</a>' \
                          f'</span>' \
                          f'</li>'

        # Add font credit line
        html_lines += '<li style="line-height: 28px;"><span style="font-size: 9pt;">' \
                      'Inconsolata Font by ' \
                      '<b><a href="http://levien.com/type/myfonts/inconsolata.html" style="color: #363636">' \
                      'Raph Levien</a></b> ' \
                      '<a style="color: #363636" href="http://scripts.sil.org/OFL">' \
                      'SIL Open Font License, Version 1.1</a>' \
                      '</span></li>'

        return f'<ul style="list-style-type: none;">{html_lines}</ul>'
