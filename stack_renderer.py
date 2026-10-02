"""Literal, offline rendering of reviewed templates; never deploys or overwrites."""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile

TOKEN = re.compile(r'@@([A-Z][A-Z0-9_]*)@@')


def render(templates, settings, output):
    templates, output = Path(templates), Path(output)
    values = settings.get('values', {})
    comments = settings.get('comments', {})
    if 'INDEXER_POLICY' in values and not isinstance(json.loads(values['INDEXER_POLICY']), list):
        raise ValueError('indexer policy must be a JSON array')
    files = {p.relative_to(templates).as_posix(): p for p in templates.rglob('*') if p.is_file()}
    if any(p.is_symlink() for p in templates.rglob('*')):
        raise ValueError('symlinks are not templates')
    if set(comments) - set(files):
        raise ValueError('comment metadata must name an existing template')
    rendered = {}
    for relative, path in files.items():
        text = path.read_text()
        missing = set(TOKEN.findall(text)) - set(values)
        if missing:
            raise ValueError('missing settings: ' + ', '.join(sorted(missing)))
        text = TOKEN.sub(lambda m: str(values[m.group(1)]), text)
        # Site-specific commentary can be restored without maintaining a second
        # implementation. The public example contains no household annotations.
        lines = text.splitlines(keepends=True)
        for index, line in comments.get(relative, []):
            if not isinstance(index, int) or index < 0 or index > len(lines):
                raise ValueError('invalid annotation position')
            if not isinstance(line, str) or '\r' in line or len(line.splitlines()) != 1:
                raise ValueError('annotation must be exactly one comment line')
            prefixes = ('#', ';') if relative.endswith('qBittorrent.conf') else ('#',)
            if not line.lstrip().startswith(prefixes):
                raise ValueError('annotations may only contain comment lines')
            lines.insert(index, line)
        rendered[relative] = (''.join(lines), path.stat().st_mode & 0o777)
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.render-', dir=output.parent))
    try:
        for relative, (text, mode) in rendered.items():
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
            target.chmod(mode)
        temporary.rename(output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--settings', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    render(Path(__file__).parent / 'templates', json.loads(args.settings.read_text()), args.output)


if __name__ == '__main__':
    main()
