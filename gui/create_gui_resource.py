"""    Creates python resource module for PyQt5 with pyrcc5    executed from Visual Studio, base path is project"""from shlex import split as shell_syntaxfrom subprocess import runfrom sys import exitargs = "pyrcc5 -compress 9 -o preset_editor_rsc_rc.py res/preset_editor_rsc.qrc"print (str(args))run(shell_syntax(args), shell=True)exit()