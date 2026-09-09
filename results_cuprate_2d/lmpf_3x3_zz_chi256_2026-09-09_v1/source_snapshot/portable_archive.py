"""Result-local, lossless archive compatible with the existing safe restorer."""
from pathlib import Path
import argparse, gzip, hashlib, json, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.restore_archives import digest, safe_path, run as restore_run


def pack(root, paths, part_bytes=9_000_000):
    root = Path(root).resolve()
    if not 1 <= part_bytes < 10_000_000:
        raise ValueError('Archive parts must be smaller than 10 MB')
    if not paths or len(paths) != len(set(paths)):
        raise ValueError('Provide a nonempty unique source list')
    archive = root / 'archive'
    if archive.exists():
        raise FileExistsError('Preserve prior archive')
    sources = [(name, safe_path(root, name)) for name in paths]
    for name, path in sources:
        if not path.is_file() or path.stat().st_size > 64 * 1024**2:
            raise ValueError('Missing or oversized archive source: ' + name)
    (archive / 'objects').mkdir(parents=True)
    objects = {}
    originals = []
    for name, path in sources:
        original_hash = digest(path)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != original_hash:
            raise ValueError('Source changed during packing')
        originals.append({'path': name, 'bytes': len(data), 'sha256': original_hash})
        if original_hash not in objects:
            compressed = gzip.compress(data, compresslevel=1, mtime=0)
            parts = []
            for index, offset in enumerate(range(0, len(compressed), part_bytes)):
                chunk = compressed[offset:offset+part_bytes]
                rel = f'archive/objects/{original_hash}.gz.part{index:03d}'
                with (root / rel).open('xb') as handle:
                    handle.write(chunk)
                parts.append({'path': rel, 'bytes': len(chunk),
                              'sha256': hashlib.sha256(chunk).hexdigest()})
            objects[original_hash] = {'sha256': original_hash,
                                     'uncompressed_bytes': len(data), 'parts': parts}
        if digest(path) != original_hash:
            raise ValueError('Source changed during packing')
    manifest = {'schema': 'result-local-lossless-v1',
                'original_files': originals, 'objects': list(objects.values())}
    with (archive / 'manifest.json').open('x') as handle:
        json.dump(manifest, handle, indent=2)
        handle.write('\n')
    # Existing independent streaming decompressor checks every part and raw hash.
    return restore_run(root, restore=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('pack', 'verify', 'restore'))
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    if args.action == 'pack':
        result = pack(args.folder, [f'states/obs22_chi256_arm{arm}.npz' for arm in range(4)])
        with (args.folder / 'archive/verification.json').open('x') as handle:
            json.dump(result, handle, indent=2)
            handle.write('\n')
    else:
        result = restore_run(args.folder, restore=args.action == 'restore')
    print(json.dumps(result, indent=2))
