#!/usr/bin/python3
"""Validate qBittorrent's pre/post-5.3 INI without exposing configuration."""
import configparser
from pathlib import Path
import sys


def validate(source):
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    try:
        parser.read_string(source)
    except configparser.Error:
        raise ValueError('invalid qBittorrent INI') from None

    if parser.defaults():
        raise ValueError('unsupported inherited INI defaults')

    def setting(section, key, legacy=None):
        values = []
        for name, option in [(section, key), *([('Preferences', legacy)] if legacy else [])]:
            if parser.has_section(name) and option in parser[name]:
                values.append(parser[name][option])
        if not values or len(set(values)) != 1:
            raise ValueError('missing or conflicting qBittorrent setting')
        return values[0]

    if setting('WebUI', 'LocalHostAuth', 'WebUI\\LocalHostAuth') != 'false':
        raise ValueError('loopback authentication bypass required')
    if setting('BitTorrent', 'Session\\DiskIOType') != 'SimplePreadPwrite':
        raise ValueError('NFS-safe disk I/O required')
    domains = setting('WebUI', 'ServerDomains', 'WebUI\\ServerDomains')
    if not any(domains.startswith(q) and domains.endswith(q) and len(domains) > 2*len(q)
               for q in ('"', '\\"')):
        raise ValueError('quoted server domains required')


if __name__ == '__main__':
    try:
        validate(Path(sys.argv[1]).read_text())
    except (OSError, ValueError, IndexError):
        print('qBittorrent loopback authentication, NFS I/O or quoted domains check failed', file=sys.stderr)
        raise SystemExit(69) from None
