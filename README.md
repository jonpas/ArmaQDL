# ArmaQDL

[![CI - Test](https://github.com/jonpas/ArmaQDL/actions/workflows/test.yml/badge.svg)](https://github.com/jonpas/ArmaQDL/actions/workflows/test.yml)
[![CI - Build](https://github.com/jonpas/ArmaQDL/actions/workflows/build.yml/badge.svg)](https://github.com/jonpas/ArmaQDL/actions/workflows/build.yml)
[![PyPI - Version](https://img.shields.io/pypi/v/ArmaQDL.svg?logo=pypi&label=PyPI&logoColor=gold)](https://pypi.org/project/ArmaQDL)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ArmaQDL.svg?logo=python&label=Python&logoColor=gold)](https://pypi.org/project/ArmaQDL)

Python program for quick launching various mod developement configurations for Arma through a simple CLI.

Through easily-identifiable preset locations, this program can provide a fast and developer-friendly CLI with some additional optional features, such as building mods and opening the last log file. It is designed around easily modifiable location groups and build tools.

## Features

- Easy **mod launching** from different **preset locations**
- **Load mission** via mission name only or specifying profile name
- **Build** development **mods**
- Open the last log file
- Select the profile to start with
- Toggle file patching, script errors, signature check and windowed mode
- Mod location wildcards (`glob` pattern matching)
- Easy **dedicated server and headless client launching**
- Load mission on dedicated server (by manipulating `server.cfg`)
- Join server


## Installation

ArmaQDL is distributed on [PyPI](https://pypi.org/) as well as a Standalone executable (Windows only).
- Use Standalone if you are on Windows and don't have Python installed.
- Use PyPI if you have Python installed or are not using Windows.

PyPI provides easier updating of ArmaQDL, while Standalone requires manual updates.

#### Standalone

Download `armaqdl.exe` from [latest release](https://github.com/jonpas/ArmaQDL/releases/latest) and place it in a convenient location.

Open Command Prompt, PowerShell or any other terminal application, navigate to the location of `armaqdl.exe` and run it once to generate configuration files without launching Arma.

```sh
# Command Prompt
$ armaqdl
# PowerShell
$ .\armaqdl
```
_Note: Add `.exe` if `armaqdl` is not enough to find the executable._


#### PyPI

Installation as a user is recommended to avoid permission issues with CLI script installation.

```
$ pip install --user ArmaQDL
```
_Note: Add pip installation directory to `PATH` environmental variable to use it directly._

Run it once to generate configuration files without launching Arma.

```sh
# Directly (only works if in PATH)
$ armaqdl
# As a Python module
$ python -m armaqdl
```


## Setup

You should modify the [default settings](https://github.com/jonpas/ArmaQDL/blob/master/config/settings.toml) to your needs. Launching without setup may create a new profile and result in failed launches.

Settings file can be found in your operating system's standard configuration directory, usually:
- Windows: `%AppData%\ArmaQDL\settings.toml`
- Linux: `~/.config/ArmaQDL/settings.toml`

Settings are in [TOML](https://toml.io/en/) format and can be edited with any text editor.

### Dedicated Server

Loading a mission on dedicated server automatically requires `server.cfg` to be present next to `arma3_x64.exe` with at least the following entries mission and Headless Client entries.

```cpp
// Automatically load the first mission in rotation
class Missions {
    class Test {
        template = "mission.vr";
    };
};

// Allow Headless Clients from local machine
headlessClients[] = {"127.0.0.1"};
localClient[] = {"127.0.0.1"};

// Allow multiple connections, unsigned mods and file patching (as needed)
kickDuplicate = 0;
verifySignatures = 0;
allowedFilePatching = 2;
```

ArmaQDL copies the mission from used profile's missions folder and updates the mission name in `server.cfg` to make the server automatically load it.


## Usage

ArmaQDL is a CLI script, view all the options with the `--help` flag.

```sh
$ armaqdl -h
```
_Note: All examples use `armaqdl` to launch ArmaQDL, replace it appropriately depending on your install._

**Example 1:** _(launching and building mods)_

Launches Arma with CBA from main location, ACE3 from Workshop install and ACRE2 from local development folder. Additionally builds ACRE2 mod and opens the latest log file. Loads Arma directly into the editor using the specified mission from the "Soldier" profile.

```sh
$ armaqdl main:cba workshop:@ace dev:acre2:b -m Soldier:test.vr
```

Specific build tool can also be specified, such as HEMTT.

```sh
$ armaqdl main:cba workshop:@ace dev:acre2:bhemtt -m Soldier:test.vr
```

**Example 2:** _(server and mission handling)_

Launches Arma Server with CBA from local development folder and loads specified mission from default profile's missions folder, copying it to the server in the process.

```sh
$ armaqdl dev:cba -m test.vr -s
```

Launches Arma with CBA from local development folder and connects to the given server with the given password (`-j` defaults to the settings file).

```sh
$ armaqdl dev:cba -j 192.168.1.1:2302:test
```

**Example 3:** _(glob and skipping)_

Launches Arma with all mods in a folder `modpack` from main location, skipping ACE3 in the same folder and instead loading ACE3 from a local development folder. This is useful for replacing a subset of mods from a bigger modpack.

```sh
$ armaqdl main:modpack\* main:modpack\ace:s dev:ace
```

**Example 4:** _(launch types)_

Launches Arma with mods from local development folder, CBA using HEMTT release build, ACE3 using automatic launch type determination and ACRE2 using non-HEMTT build. Available launch types are `dev`, `build`, `release` for HEMTT or none for non-HEMTT `addons/`. Automatic determination uses HEMTT if `.hemttout` folder exists with launch type as specified in settings file, or `dev` if not specified.


```sh
$ armaqdl dev:cba:trelease dev:ace dev:acre2:t
```

Build type for HEMTT can also be specified using the same flag in addition to build flag.

```sh
$ armaqdl dev:cba:bhemtt:trelease dev:ace:b:tbuild
```


## Development

ArmaQDL uses [Hatchling](https://hatch.pypa.io/latest/) as a build backend and [flake8](https://flake8.pycqa.org/en/latest/) as a style guide.

```sh
$ pip install --user -e .
```

[Hatch](https://hatch.pypa.io/latest/) is the primary project manager of choice, but any project adhering to PEP 621 (`pyproject.toml` specification) can be used.

```sh
# Run development build
$ hatch run armaqdl
# Lint with flake8
$ hatch run lint
# Test with pytest
$ hatch run test
# Bundle with PyInstaller
$ hatch run static:bundle
```

Limited Linux support exists for testing purposes, but launching Arma or opening the last log file is not supported. Contributions are welcome!
