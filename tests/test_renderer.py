import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('renderer', Path(__file__).resolve().parents[1] / 'stack_renderer.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)

class RendererTests(unittest.TestCase):
    def test_missing_parameter_and_path_escape_fail_without_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'templates'; source.mkdir()
            (source / 'compose.yaml').write_text('bind=@@ADDRESS@@\n')
            with self.assertRaises(ValueError):
                renderer.render(source, {'values': {}}, root / 'output')
            self.assertFalse((root / 'output').exists())
            with self.assertRaises(ValueError):
                renderer.render(source, {'values': {'ADDRESS': 'x'}, 'comments': {'../escape': []}}, root / 'output')

    def test_literal_replacement_does_not_evaluate_shell_or_gluetun_tokens(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'templates'; source.mkdir()
            (source / 'compose.yaml').write_text('@@PATH@@ {{PORT}} ${IMAGE}\n')
            renderer.render(source, {'values': {'PATH': '$(touch /bad)'}}, root / 'output')
            self.assertEqual((root / 'output/compose.yaml').read_text(), '$(touch /bad) {{PORT}} ${IMAGE}\n')

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'templates'; source.mkdir()
            (source / 'compose.yaml').write_text('new')
            out = root / 'output'; out.mkdir()
            (out / 'compose.yaml').write_text('original')
            with self.assertRaises(FileExistsError):
                renderer.render(source, {'values': {}}, out)
            self.assertEqual((out / 'compose.yaml').read_text(), 'original')

class AnnotationBoundaryTests(unittest.TestCase):
    def test_multiline_annotation_cannot_inject_executable_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'templates';source.mkdir()
            (source/'helper').write_text('#!/bin/sh\necho safe\n')
            with self.assertRaises(ValueError):
                renderer.render(source,{'values':{},'comments':{'helper':[[1,'# comment\necho unsafe\n']]}},root/'output')
            self.assertFalse((root/'output').exists())
