"""Create or verify an experiment input lock without loading/rebuilding features."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from experiment_identity import build_input_lock, verify_input_lock, write_input_lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--spec', type=Path, help='JSON build_input_lock arguments excluding root')
    group.add_argument('--verify', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.verify:
        lock = json.loads(args.verify.read_text())
        print(verify_input_lock(lock, root=ROOT))
    else:
        if args.output is None:
            parser.error('--spec requires --output')
        lock = build_input_lock(root=ROOT, **json.loads(args.spec.read_text()))
        write_input_lock(args.output, lock)
        print(lock['input_identity_sha256'])


if __name__ == '__main__':
    main()
