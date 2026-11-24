#!/usr/bin/env python3
"""Update Scoop manifest version, download URL and hash in place (used by Publish CI workflow).

Usage: scoop_manifest.py <manifest.json> <version> <sha256>
"""
import json
import re
import sys

URL_VERSION = "$version"


def update(manifest, version, sha256):
    if not re.fullmatch(r"\d+\.\d+\.\d+([.\-+][0-9A-Za-z.\-+]*)?", version):
        raise ValueError(f"Invalid version: {version}")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", sha256):
        raise ValueError(f"Invalid SHA256 hash: {sha256}")

    # Rebuild to keep key order (hash right after url)
    updated = {}
    for key, value in manifest.items():
        if key == "hash":
            continue
        if key == "version":
            value = version
        updated[key] = value
        if key == "url":
            updated[key] = manifest["autoupdate"]["url"].replace(URL_VERSION, version)
            updated["hash"] = sha256.lower()
    return updated


def main(argv):
    if len(argv) != 4:
        print(__doc__.strip())
        return 2

    path, version, sha256 = argv[1:]
    with open(path, encoding="utf-8") as f:
        manifest = json.load(f)

    try:
        manifest = update(manifest, version, sha256)
    except ValueError as e:
        print(f"Error! {e}")
        return 1

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=4)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
