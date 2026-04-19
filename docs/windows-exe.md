# Windows Desktop EXE

This repo can now be packaged as a Windows desktop `.exe` program.

## What The EXE Does

- Shows a desktop control window instead of requiring the user to work from the browser directly
- Lets the user configure:
  - Wazuh webhook secret
  - Velociraptor mode
  - Velociraptor base URL
  - Velociraptor API key
- Starts and stops the Docker stack
- Posts the sample Wazuh alert
- Opens the workspace in a native desktop window through `pywebview`

## Build

```bat
build-exe.bat
```

Output:

- `dist\CyberRed\CyberRed.exe`

To build a Windows installer:

```bat
build-installer.bat
```

Output:

- `dist\CyberRedSetup.exe`

## Use

1. Double-click `dist\CyberRed\CyberRed.exe` or install with `CyberRedSetup.exe`
2. Set integration values in the `Integrations` tab
3. Click `Start Stack`
4. Click `Open Desktop Workspace`

## Why This Opens Faster

- The launcher now uses PyInstaller `--onedir` instead of `--onefile`
- Windows no longer has to unpack the whole app into a temp folder on every launch
- The build excludes unused GUI backends and extra packages we do not use in CyberRed

## Important Note

The main product UI is still the existing Next.js app, but the user experience is now desktop-first because the `.exe` is the entry point and the workspace opens inside a native application window instead of asking the user to manage the stack manually from a browser.
