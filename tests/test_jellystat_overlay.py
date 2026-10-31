import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('jellystat_renderer', ROOT / 'stack_renderer.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class JellystatOverlayTests(unittest.TestCase):
    def test_opt_in_overlay_isolated_database_and_no_media_access(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'root'
            renderer.render(ROOT / 'templates', json.loads((ROOT / 'settings.example.json').read_text()), output)
            app = output / 'opt/home-network/torrent-services'
            command = ['docker', 'compose', '--env-file', str(output / 'etc/home-network/image-locks/torrent-services.env'),
                       '-f', str(app / 'compose.yaml'), '-f', str(app / 'compose.jellystat.yaml'),
                       '--profile', 'jellystat', 'config', '--no-env-resolution', '--no-path-resolution', '--format', 'json']
            config = json.loads(subprocess.check_output(command, text=True))
            database = config['services']['jellystat-db']
            self.assertNotIn('ports', database)
            self.assertEqual(set(database['networks']), {'jellystat-db'})
            self.assertTrue(config['networks']['jellystat-db']['internal'])
            app_config = config['services']['jellystat']
            self.assertNotIn('network_mode', app_config)
            mounts = json.dumps(app_config['volumes'])
            self.assertNotIn('docker.sock', mounts)
            self.assertNotIn('/mnt/library', mounts)
            self.assertEqual(app_config['environment']['REJECT_SELF_SIGNED_CERTIFICATES'], 'true')
            base = (app / 'compose.yaml').read_text()
            self.assertNotIn('jellystat:', base)
            self.assertNotIn(',3000', (output / 'usr/local/libexec/home-network/apply-torrent-services-ingress-policy').read_text())
