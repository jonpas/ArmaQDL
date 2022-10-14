# ArmaQDL

[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/jonpas/ArmaQDL/Python)](https://github.com/jonpas/ArmaQDL/actions?query=workflow%3A%22Python%22)
[![PyPI](https://img.shields.io/pypi/v/ArmaQDL)](https://pypi.org/project/ArmaQDL)

Python program for quick launching various mod developement configurations for Arma through a simple CLI.

Through easily-identifiable preset locations, program is able to provide a fast and developer-friendly CLI with some additional optional features, such as building mods and opening last log file. It is designed around easily modifiable location groups and build tools.

## Features

- Easy mod launching from different preset locations
- Load mission via mission name only or specifying profile name
- Build development mods
- Open last log file
- Select profile to start with
- Toggle file patching, script errors, signature check and windowed mode
- Mod location wildcards (`glob` pattern matching)
- Easy dedicated server launching
- Load mission on dedicated server (by manipulating `server.cfg`)
- Join server


## Installation

ArmaQDL is distributed on [PyPI](https://pypi.org/). Installation as a user is recommended to avoid permission issues with CLI script installation.

```
$ pip install --user ArmaQDL
```
_Note: Add pip installation directory to `PATH` environmental variable to use it directly._

Run it once to generate configuration files.

```
$ armaqdl -h
$ python -m armaqdl -h
```

Modify settings to your needs. Settings file can be found in your operating system's standard configuration directory, usually:
- Windows: `%AppData%\ArmaQDL\settings.toml`
- Linux: `~/.config/ArmaQDL/settings.toml`

Settings are in [TOML](https://toml.io/en/) format and can be edited with any text editor.


## Usage

ArmaQDL will install a CLI script _(requires it to be in `PATH`)_, but it can also be used as a Python module.

```
$ armaqdl -h
$ python -m armaqdl -h
```

**Example 1:**

Launches Arma with CBA from P-drive, ACE3 from Workshop install and ACRE2 from local development folder. Additionally builds ACRE2 mod and opens the latest log file. Loads Arma directly into editor using the specified mission from "Soldier" profile.

```
$ armaqdl p:x\cba workshop:@ace dev:acre2:b -m Soldier:test.vr
```

Specific build tool can also be specified, such as HEMTT:
```
$ armaqdl p:x\cba workshop:@ace dev:acre2:hemtt -m Soldier:test.vr
```

**Example 2:**

Launches Arma Server with CBA from P-drive and loads specified mission from root `MPMissions` folder.

```
$ armaqdl p:x\cba -m test.vr -s
```

Launches Arma with CBA from P-drive and connects to the given server with given password (`-j` defaults to `localhost:2302:test`).

```
$ armaqdl p:x\cba -j 192.168.1.1:2302:test
```


## Development

ArmaQDL uses [Hatchling](https://hatch.pypa.io/latest/) as a build bakcned and [flake8](https://flake8.pycqa.org/en/latest/) as a style guide.

```
$ pip install -e .
```

[Hatch](https://hatch.pypa.io/latest/) is the primary project manager of choice, but any project adhering to PEP 621 (`pyproject.toml` specification)  can be used.

```
$ hatch shell
```

Limited Linux support exists for testing purposes, but launching Arma or opening last log file are not supported. Contributions are welcome!
