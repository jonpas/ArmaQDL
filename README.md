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
- Mod location wildcards (`glob` pattern matching)
- Easy dedicated server launching
- Load mission on dedicated server (by manipulating `server.cfg`)
- Join server

## Usage

Download `armaqdl.py` and modify `CONFIGURATION` section on top of the file to your needs.

It is advisable to add the program to `PATH` environmental variable to use it from anywhere.

**Example 1:**

Launches Arma with CBA from P-drive, ACE3 from Workshop install and ACRE2 from local development folder. Additionally builds ACRE2 mod and opens the latest log file. Loads Arma directly into editor using the specified mission from "Soldier" profile.

```
$ armaqdl.py p:x\cba workshop:@ace dev:acre2:b -m Soldier:test.vr
```

**Example 2:**

Launches Arma Server with CBA from P-drive and loads specified mission from root `MPMissions` folder.

```
$ armaqdl.py p:x\cba -m test.vr -s
```

Launches Arma with CBA from P-drive and connects to the given server with given password (`-j` defaults to `localhost:2302:test`).

```
$ armaqdl.py p:x\cba -j 192.168.1.1:2302:test
```
