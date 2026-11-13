# Dependencies

The application code is MIT licensed. Dependencies retain their own licenses.

- Telethon: MIT — https://github.com/LonamiWebs/Telethon
- PySide6 / Shiboken / Qt: LGPLv3 / GPLv3 / commercial, as applicable — https://doc.qt.io/qtforpython-6/licenses.html
- qasync: BSD-2-Clause — https://github.com/CabbageDevelopment/qasync
- keyring: MIT — https://github.com/jaraco/keyring
- platformdirs: MIT — https://github.com/tox-dev/platformdirs
- PyInstaller (build tool): GPL with bundling exception — https://pyinstaller.org/en/stable/license.html

Keep the license files bundled by PyInstaller with the release. Qt libraries
are dynamically loaded in the directory distribution; do not remove them or
prevent replacement with compatible modified libraries. Before publishing a
binary release, review the exact included Qt modules and their licenses,
include applicable license texts and satisfy source availability obligations.
This file is an inventory, not a substitute for dependency license texts.
