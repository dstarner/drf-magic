import subprocess
import sys

VERSION_FILE = 'drf_magic/__init__.py'
VERSION_VAR = '__version__'


def main(version):
    res = subprocess.run(
        ['git', 'describe', '--tags', version],
        capture_output=True, text=True, check=False
    )
    if res.returncode == 0:
        raise ValueError(f'Expected version {version} to not already exist')

    contents = []
    with open(VERSION_FILE, 'r') as f:
        contents = f.readlines()
    for i, line in enumerate(contents):
        if line.startswith(VERSION_VAR):
            contents[i] = f"{VERSION_VAR} = '{version}'\n"

    with open(VERSION_FILE, 'w') as f:
        f.writelines(contents)

    subprocess.run(['git', 'add', VERSION_FILE])
    subprocess.run(['git', 'commit', '-m', f'Release version {version}'])
    subprocess.run(['git', 'push', 'main'])

    subprocess.run(
        ['git', 'tag', version, '-a', '-m', f'Release version {version}'],
        capture_output=True, text=True,
    )
    subprocess.run(['git', 'push', 'origin', version])


if __name__ == "__main__":
    if not len(sys.argv) == 2:
        raise ValueError('Expected a version argument')
    main(sys.argv[1])
