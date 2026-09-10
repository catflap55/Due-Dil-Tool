Building a Windows executable
=============================

This is optional. Most people should use the Start file in the Mac, Windows, or Linux folder.

Prerequisites: Python 3.10+, `pip install -r requirements.txt`, then `pip install pyinstaller`.

From the unzipped folder:

    pyinstaller packaging/due_dil.spec

Output:

    dist/DueDiligenceTool/DueDiligenceTool.exe

The `web` folder is copied into the bundle. SQLite and exports use the application data directory when frozen.

macOS/Linux: same command; produces a folder/binary for that computer.
