#!/usr/bin/env python3
"""Disable anonymous analytics in an *arr host-config API resource."""

import json
import sys


def analytics_disabled(config):
    if not isinstance(config, dict):
        raise ValueError("host configuration must be a JSON object")
    updated = dict(config)
    updated["analyticsEnabled"] = False
    return updated


def main():
    config = json.load(sys.stdin)
    json.dump(analytics_disabled(config), sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
