# Arma-QDL

Python program for quick launching various mod developement configurations for Arma through a simple CLI.

## Features

- Easy mod launching from different preset locations
- Load mission via mission name only or specifying profile name
- Build development mods
- Open last log file
- Select profile to start with
- Toggle file patching, script errors, signature check and windowed mode

**Example:**

Launches Arma with CBA from P-drive, ACE3 from Workshop install and ACRE2 from local development folder. Additionally builds mods from P-drive and local development folder and opens the latest log file. Loads Arma directly into editor using the specified mission from "Soldier" profile.

```
$ armaqdl.py -m p:x\cba workshop:@ace dev:acre2 -b -l -m Soldier:test.vr
```

## Usage

Download `armaqdl.py` and modify `CONFIGURATION` section on top of the file to your needs.

```
$ armaqdl.py -h
usage: armaqdl.py [-h] [-m [MOD [MOD ...]]] [-e EDITOR] [-p PROFILE] [-nfp]
                  [-ne] [-s] [-f] [-b] [-l] [-v]

Quick development Arma 3 launcher

optional arguments:
  -h, --help            show this help message and exit
  -m [MOD [MOD ...]], --mod [MOD [MOD ...]]
                        path to mod folder
  -e EDITOR, --editor EDITOR
                        mission to load
  -p PROFILE, --profile PROFILE
                        profile name
  -nfp, --no-filepatching
                        disable file patching
  -ne, --no-errors      hide script errors
  -s, --signatures      check signatures
  -f, --fullscreen
  -b, --build           build development mods
  -l, --log             log output
  -v, --verbose         verbose output
```
