# Arma-QDL

Python program for quick launching various mod developement configurations for Arma through a simple CLI.

Through easily-identifiable preset locations, program is able to provide a fast and developer-friendly CLI with some additional optional features, such as building mods and opening last log file. It is designed around easily modifiable location groups and build tools.

## Features

- Easy mod launching from different preset locations
- Load mission via mission name only or specifying profile name
- Build development mods
- Open last log file
- Select profile to start with
- Toggle file patching, script errors, signature check and windowed mode

## Usage

Download `armaqdl.py` and modify `CONFIGURATION` section on top of the file to your needs.

It is advisable to add the program to `PATH` environmental variable to use it from anywhere.

**Example:**

Launches Arma with CBA from P-drive, ACE3 from Workshop install and ACRE2 from local development folder. Additionally builds ACRE2 mod and opens the latest log file. Loads Arma directly into editor using the specified mission from "Soldier" profile.

```
$ armaqdl.py p:x\cba workshop:@ace dev:acre2:b -m Soldier:test.vr
```
