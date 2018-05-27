@echo off
REM Konvertiert RenderKnecht Varianten*.cmd zu XML Daten und gibt Pfad inkl Dateinamen aus.
REM Zur ausfuehrung durch Python Script gedacht
TITLE Varianten Konverter
setlocal ENABLEEXTENSIONS EnableDelayedExpansion
set Script_Location=%~dp0
set "Preset_Location=%1"
set "filename_out=Varianten_XML"
set /a filename_count=1
set "xmlfile=%Script_Location%%filename_out%_%filename_count%.xml"
REM Default Settings
REM SafeSwitch=false usePresetWindow=false "VIEWER_SIZE=1280 960" "FileExtension=.hdr" /a baseResolutionX=640 /a baseResolutionY=480

call :check-filename
REM echo Variantenkonverter wird folgende Datei erstellen:
if exist "%Preset_Location%" (
	REM echo Reading from %Preset_Location%
	call :Preset-Reader "%Preset_Location%"
) else (
	call :Preset-Reader "%Script_Location%"
)
call :create-xml-presets

echo | set /p "dummyVar=%xmlfile%"

REM Return Filename
REM if EXIST "%Script_Location%current_XML_temp.txt" del "%Script_Location%current_XML_temp.txt"
REM > "%Script_Location%current_XML_temp.txt" echo %xmlfile%

goto :exit-label

:create-xml-presets
	>> %xmlfile% echo ^<?xml version^="1.0" encoding="UTF-8"?^>
	
	>> %xmlfile% echo ^<^^!--Created by RenderKnecht Variantconverter on !DATE! - !TIME!--^>
	>> %xmlfile% echo:
	
	>> %xmlfile% echo ^<renderknecht_varianten^>

		>> %xmlfile% echo 	^<origin^>
			if exist "%Preset_Location%" (
				FOR /f "tokens=*" %%G IN ('dir /b %Preset_Location%\VARIANTEN*.cmd') DO (
					>> %xmlfile% echo 		^<file name="%%~nG" extension="%%~xG" last_modified="%%~tG" location_drive="%%~dG"^>%Preset_Location%%%G^</file^>
				)
			) else (
				FOR /f "tokens=*" %%G IN ('dir /b %Script_Location%\VARIANTEN*.cmd') DO (
					>> %xmlfile% echo 		^<file name="%%~nG" extension="%%~xG" last_modified="%%~tG" location_drive="%%~dG"^>%Script_Location%%%G^</file^>
				)
			)
		>> %xmlfile% echo 	^</origin^>
		>> %xmlfile% echo:
		
		>> %xmlfile% echo 	^<renderknecht_settings^>
			if DEFINED SafeSwitch (
				if "%SafeSwitch%"=="true" set SafeSwitch=True
				if "%SafeSwitch%"=="false" set SafeSwitch=False
				>> %xmlfile% echo 		^<setting name^="safeSwitch" type^="boolean"^>!SafeSwitch!^</setting^>
			)
			if DEFINED VIEWER_SIZE (
				>> %xmlfile% echo 		^<setting name^="viewerSize" type^="string"^>%VIEWER_SIZE%^</setting^>
			)
			if DEFINED FileExtension (
				>> %xmlfile% echo 		^<setting name^="fileExtension" type^="string"^>%FileExtension%^</setting^>
			)
			if DEFINED baseResolutionX (
				>> %xmlfile% echo 		^<setting name^="baseResolutionX" type^="integer"^>%baseResolutionX%^</setting^>
			)
			if DEFINED baseResolutionY (
				>> %xmlfile% echo 		^<setting name^="baseResolutionY" type^="integer"^>%baseResolutionY%^</setting^>
			)
			if DEFINED nameFormat (
				>> %xmlfile% echo 		^<setting name^="nameFormat" type^="integer"^>%nameFormat%^</setting^>
			)
			if DEFINED FeedbackTimeOut (
				>> %xmlfile% echo 		^<setting name^="FeedbackTimeOut" type^="integer"^>%FeedbackTimeOut%^</setting^>
			)
			if DEFINED FeedbackTimeOutMaximum (
				>> %xmlfile% echo 		^<setting name^="FeedbackTimeOutMaximum" type^="integer"^>%FeedbackTimeOutMaximum%^</setting^>
			)
			if DEFINED FeedbackContent (
				>> %xmlfile% echo 		^<setting name^="FeedbackContent" type^="string"^>%FeedbackContent%^</setting^>
			)
		>> %xmlfile% echo 	^</renderknecht_settings^>
		>> %xmlfile% echo:
	
		>> %xmlfile% echo 	^<variant_presets^>
			set /a numOrder=0
			set /a numViewset=0
			:viewset-loop
			IF NOT "!viewset[%numViewset%]!" == "" (
				REM echo %numViewset% - !viewset[%numViewset%]!
				>> %xmlfile% echo 		^<preset order^="!numOrder!" name^="Viewset_!viewset[%numViewset%]!" type^="viewset"^>
				>> %xmlfile% echo 			^<variant  order^="0" name^="!viewset!" value^="!viewset[%numViewset%]!" /^>
				>> %xmlfile% echo 		^</preset^>
				set /a numOrder+=1
				set /a numViewset+=1
				goto viewset-loop
			)
			
			if DEFINED reset_conf (
				>> %xmlfile% echo 		^<preset order^="!numOrder!" name^="reset_conf" type^="reset"^>
				call :switch-conf "!reset_conf!"
				>> %xmlfile% echo 		^</preset^>
				set /a numOrder+=1
			)
			for /L %%p in (1,1,!numPresets!) do (
				>> %xmlfile% echo 		^<preset order^="!numOrder!" name^="!PresetName[%%p]!" type^="preset"^>
				call :switch-conf "!Preset[%%p]!"
				>> %xmlfile% echo 		^</preset^>
				set /a numOrder+=1
			)
		>> %xmlfile% echo 	^</variant_presets^>
	>> %xmlfile% echo ^</renderknecht_varianten^>
GOTO :eof

:switch-conf
	set /a variantPosition=0
	set "forStr=%1"
	set forStr=%forStr:"=%
	FOR %%F in ("%forStr:;=" "%") DO (
		if not %%F=="" (
			call :switch-write-xml %%F !variantPosition!
			set /a variantPosition+=1
		)
	)
GOTO :eof

:switch-write-xml
	set "forStr=%1"
	set position=%2
	set forStr=%forStr:"=%
	
	for /F "tokens=1,2 delims= " %%A in ("%forStr%") do (
		>> %xmlfile% echo 			^<variant  order^="!position!" name^="%%A" value^="%%B" /^>
	)
GOTO :eof

:Preset-Reader preset-folder
	REM Liest alle Varianten*.cmd aus Hilfsverzeichnis
	call :Preset-Clear
	set /a preNum=0
	FOR /f "tokens=*" %%G IN ('dir /b %1\VARIANTEN*.cmd') DO (
		call %1\%%G
	)

	REM Liest Anzahl der Presets
	call :Preset-Count false
	REM echo !numPresets! gefundene Konfigurationen.
GOTO :eof

:Preset-Count
	set drawText=%1
	set /a pNum = 1
	set /a pNumStr=10001

	:Preset-Count-Loop
	if DEFINED Preset[%pNum%] (
		REM echo !pNumStr:~-2! - !PresetName[%pNum%]!
		set /a pNum += 1
		set /a pNumStr += 1
		goto :Preset-Count-Loop
	) else (
		set /a pNum -= 1
	)
	set numPresets=%pNum%
GOTO :eof

:Preset-Clear
	set /a clearNum = 1

	:Preset-Clear-Loop
	if DEFINED Preset[%clearNum%] (
		set Preset[%clearNum%]=
		set /a clearNum += 1
		goto :Preset-Clear-Loop
	)
GOTO :eof

:check-filename
	if EXIST "%Script_Location%%filename_out%_%filename_count%.xml" (
		set /a filename_count += 1
		goto :check-filename
	)
	
	set "xmlfile=%Script_Location%%filename_out%_%filename_count%.xml"
GOTO :eof

:exit-label

exit