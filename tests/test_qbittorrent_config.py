import types
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / 'templates/usr/local/libexec/home-network/qbittorrent_runtime_config.py'
module = types.ModuleType('qbit_config')
exec(compile(PATH.read_text(), str(PATH), 'exec'), module.__dict__)


class ConfigTests(unittest.TestCase):
    OLD = '[Preferences]\nWebUI\\LocalHostAuth=false\nWebUI\\ServerDomains="client;gluetun"\n[BitTorrent]\nSession\\DiskIOType=SimplePreadPwrite\n'
    NEW = '[WebUI]\nLocalHostAuth=false\nServerDomains=\\"client;gluetun\\"\n[BitTorrent]\nSession\\DiskIOType=SimplePreadPwrite\n'

    def test_legacy_and_sectioned_formats_preserve_required_policy(self):
        for source in (self.OLD, self.NEW):
            module.validate(source)

    def test_authentication_and_io_policy_changes_are_rejected(self):
        for source in (self.NEW.replace('LocalHostAuth=false', 'LocalHostAuth=true'),
                       self.NEW.replace('SimplePreadPwrite', '0'),
                       self.NEW.replace('ServerDomains=\\"client;gluetun\\"', 'ServerDomains=client;gluetun'),
                       self.NEW + '[Preferences]\nWebUI\\LocalHostAuth=true\n',
                       '[DEFAULT]\nLocalHostAuth=false\n' + self.NEW.replace('LocalHostAuth=false\n', '')):
            with self.assertRaises(ValueError):
                module.validate(source)
