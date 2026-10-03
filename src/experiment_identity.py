"""Immutable, content-addressed experiment input locks; never rebuild features."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from feature_cache import sha256_file
from research_policy import classify_years


class ExperimentIdentityError(ValueError):
    pass


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def clean_git_commit(root):
    root = Path(root)
    # Generated/untracked reports do not dirty the tracked code identity.
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=root, text=True)
    untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', 'src', 'scripts', 'config'], cwd=root, text=True)
    if dirty.strip() or untracked.strip():
        raise ExperimentIdentityError('Commit code/config changes before locking experiment inputs')
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()


def build_input_lock(*, experiment_id, root, files, years, contracts, counts,
                     settings, unavailable=None, archive_identifier=None, timestamp=None):
    """Files map logical roles to paths (relative paths resolve from root).

    Missing upstream raw/cache inputs are explicit reasons, never guessed hashes.
    Counts/coverage/settings are caller-supplied provenance and must be verified
    against the producer's metadata; unknown counts use null.
    """
    root = Path(root).resolve()
    if not experiment_id or not files or not years:
        raise ExperimentIdentityError('experiment ID, files and research years are required')
    if not any(role.startswith(('ledger', 'scored_cache')) for role in files):
        raise ExperimentIdentityError('A ledger or scored cache input is required')
    for role in ('strategy', 'sessions', 'research_policy'):
        if role not in files:
            raise ExperimentIdentityError(f'Missing config role: {role}')
    for key in ('bars', 'candidates', 'trades'):
        value = counts.get(key)
        if key not in counts or (value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0)):
            raise ExperimentIdentityError(f'Invalid/missing count: {key}')
    if not all(key in settings for key in ('execution', 'cost', 'slippage')):
        raise ExperimentIdentityError('Execution, cost and slippage settings are required')
    git_commit = clean_git_commit(root)
    artifacts = {}
    for role, raw_path in sorted(files.items()):
        path = Path(raw_path)
        path = path if path.is_absolute() else root / path
        if not path.is_file():
            raise ExperimentIdentityError(f'Missing declared input: {role}: {path}')
        artifacts[role] = {'path': str(path.resolve()), 'bytes': path.stat().st_size,
                           'sha256': sha256_file(path)}
    identity = {
        'schema_version': 1, 'git_commit': git_commit,
        'files': {role: {k: v for k, v in item.items() if k != 'path'} for role, item in artifacts.items()},
        'coverage': {'years': sorted(set(int(y) for y in years)),
                     'contracts': sorted(set(contracts)), 'classification': classify_years(years, root / files['research_policy'])},
        'counts': counts, 'settings': settings,
        'archive_identifier': archive_identifier, 'unavailable': unavailable or {},
    }
    return {'experiment_id': experiment_id,
            'created_at': timestamp or datetime.now(timezone.utc).isoformat(),
            'input_identity_sha256': canonical_hash(identity), 'identity': identity,
            'artifacts': artifacts}


def verify_input_lock(lock, *, check_files=True, root=None):
    if canonical_hash(lock['identity']) != lock['input_identity_sha256']:
        raise ExperimentIdentityError('Input identity digest mismatch')
    expected = lock['identity']['files']
    actual = {role: {k: v for k, v in item.items() if k != 'path'} for role, item in lock['artifacts'].items()}
    if actual != expected:
        raise ExperimentIdentityError('Artifact metadata differs from locked identity')
    if root is not None and clean_git_commit(root) != lock['identity']['git_commit']:
        raise ExperimentIdentityError('Git commit differs from locked identity')
    if check_files:
        for role, item in lock['artifacts'].items():
            path = Path(item['path'])
            if not path.is_file() or path.stat().st_size != item['bytes'] or sha256_file(path) != item['sha256']:
                raise ExperimentIdentityError(f'Input drift: {role}')
    return lock['input_identity_sha256']


def write_input_lock(path, lock):
    verify_input_lock(lock)
    # Exclusive creation preserves old experiment identities.
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as handle:
        json.dump(lock, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')
