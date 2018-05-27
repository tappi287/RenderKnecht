# RenderKnecht
Windows GUI erstellt schalt- und renderbare Presets aus OEM Informationen für 3DExcite DeltaGen und stellt Batch Rendering und Remote Pfad Rendering zur Verfügung.

[![GitHub license](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](http://www.gnu.org/licenses/gpl) [![Download latest](https://img.shields.io/badge/download-latest-green.svg)](https://github.com/tappi287/RenderKnecht/blob/master/dist/RenderKnecht_String-Kerker.exe)

### Bekomme gestartet
 1. Downloade die [späteste Veröffentlichung](https://github.com/tappi287/RenderKnecht/blob/master/dist/RenderKnecht_String-Kerker.exe)
 2. Kopiere ``RenderKnecht_String-Kerker.exe`` an einen Ort an den der Benutzer Schreibrechte hat
 3. Starte ``RenderKnecht_String-Kerker.exe``
### Einführung
Der RenderKnecht bietet eine in Python und PyQt 5 entwickelte Benutzerumgebung um aus OEM Informationen, DeltaGen POS Xml Daten und Daten älterer RenderKnecht Versionen Presets zu erstellen und zu bearbeiten.

Die Daten können anschließend verwendet werden um:
-   Ausstattungen in DeltaGen POS Modellen zu schalten
-   Referenzbildpresets aller renderrelevanten Umfänge ohne Dubletten mittels Preset-Assistenten erstellen
-   Modelle auf ihre POS Umfänge zu überprüfen
-   Stapel-Render-Vorgänge zu erstellen
-   Ausstattungen nach renderrelevanten Umfängen zu filtern
-   DeltaGen Viewer Größe und Hintergrund zu steuern

Die Anwendung wird als portable, ausführbare Datei: ``RenderKnecht_String-Kerker.exe``  ausgeliefert. Bei Ausführung werden benötigte Laufzeit Bibliotheken in einen temporären Ordner des Systems entpackt. Neben der ausführbaren Datei wird ein Hilfsverzeichnis _RenderKnecht-Work erzeugt in dem sich die Log Dateien, automatische Sicherungsdateien und der Pfad zur zuletzt geöffneten Datei befinden.

Die Anwendung unterstützt eine automatische Aktualisierung. Wenn eine aktualisierte Version bereitsteht wird diese in das Hilfsverzeichnis geladen und beim Beenden der Anwendung durch die aktualisierte Version ersetzt.

### Systemanforderungen
##### Betriebssystem
 - [x] Windows 7/8.x/10, für die automatische Bildkonvertierung ist zwingend eine 64bit Version erforderlich

##### Anzeige
 - [x] minimale Auflösung der Benotzeroberfläche: 1600x1024px
 - [x] mindestens Full HD 1920x1080px empfohlen

##### Speicherplatz
- [x] mindestens 130MB freier Festplattenspeicher auf dem Systemlaufwerk in %TEMP%
- [x] mindestens 120MB freier Festplattenspeicher auf dem Laufwerk auf dem die ausführbare Datei ausgeführt wird

##### Software
 - [x] DeltaGen 10.x oder neuere Versionen
 - [x] geöffneter DeltaGen Kommandoport: 3333
