"""    Creates python resource module for PyQt5 with pyrcc5    executed from Visual Studio, base path is project"""import sysfrom pathlib import Pathfrom shlex import split as shell_syntaxfrom subprocess import runcurrent_interpreter_dir = Path(sys.executable)current_interpreter_dir = current_interpreter_dir.parentargs = current_interpreter_dir.as_posix() + r"/pyrcc5 -compress 9 -o preset_editor_rsc_rc.py res/preset_editor_rsc.qrc"print(shell_syntax(args))run(shell_syntax(args), shell=True)sys.exit()