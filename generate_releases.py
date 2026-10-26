#!/usr/bin/env python3
"""Build a LibreELEC custom-channel releases.json from CroqueMr/libreelec-x86-DV GitHub releases.

The update .tar files are not mirrored. Each entry points at the GitHub release asset:

    channel["url"] + file["subpath"] + "/" + file["name"]
    = https://github.com/<repo>/releases/download/<tag>/<asset>

which is exactly how service.libreelec.settings (resources/lib/modules/updates.py,
get_available_builds / do_manual_update) assembles the download URL.

Standard library only.
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime

SOURCE_REPO = 'CroqueMr/libreelec-x86-DV'
API_URL = f'https://api.github.com/repos/{SOURCE_REPO}/releases?per_page=100'
DOWNLOAD_BASE = f'https://github.com/{SOURCE_REPO}/releases/download/'

# Channel key must be "<builder>-<major.minor>": the updater splits on '-' and compares
# the second part as a float against VERSION_ID (channels older than the running
# system are hidden). The builder part must not contain '-' and must differ from
# "LibreELEC", otherwise it would overwrite the official channel of the same name.
CHANNEL_BUILDER = 'LibreELEC_DV'

# The updater shows regex.findall(file name)[0] as the build name and later picks the
# file whose name *contains* that string, newest first. Capturing up to ".tar" keeps
# names unique (otherwise "...-Beta1" would also match "...-Beta10").
PRETTYNAME_REGEX = r'^LibreELEC-[^.]+\.[^-]+-(.+\.tar)$'

# LibreELEC image name: ${DISTRONAME}-${DISTRO_ARCH}-${OS_VERSION}-${DISTRO_VERSION}.tar,
# DISTRO_ARCH ("Generic.x86_64") is what the updater compares against the project key.
ASSET_RE = re.compile(
    r'^LibreELEC-(?P<project>[A-Za-z0-9_-]+\.(?:x86_64|aarch64|arm))'
    r'-(?P<version>\d+\.\d+)-(?P<suffix>.+)\.tar$'
)

DISPLAY_NAMES = {
    'Generic.x86_64': 'Generic (AMD/Intel)',
    'Generic-legacy.x86_64': 'Generic Legacy (AMD/Intel/NVIDIA)',
}


def fetch_releases(token=None):
    releases = []
    url = API_URL
    while url:
        request = urllib.request.Request(url, headers={
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'le-dv-channel',
        })
        if token:
            request.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(request, timeout=60) as response:
            releases.extend(json.load(response))
            match = re.search(r'<([^>]+)>;\s*rel="next"', response.headers.get('Link', ''))
            url = match.group(1) if match else None
    return releases


def timestamp(iso):
    return datetime.strptime(iso, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d %H:%M:%S')


def collect_builds(releases, include_debug=False):
    """Return [(channel, project, published_at, tag, asset)] for every usable update tarball."""
    builds = []
    for release in releases:
        if release.get('draft'):
            continue
        tag = release['tag_name']
        for asset in release.get('assets', []):
            if asset.get('state') != 'uploaded':
                continue
            match = ASSET_RE.match(asset['name'])
            if not match:
                # sources.tar.zst, vendor-inputs.tar.zst, *.tar.part-NN, *.img.gz
                continue
            if not include_debug and match.group('suffix').endswith('-debug'):
                continue
            channel = f"{CHANNEL_BUILDER}-{match.group('version')}"
            builds.append((channel, match.group('project'), release['published_at'], tag, asset))
    return builds


def build_json(builds):
    channels = {}
    for channel, project, published_at, tag, asset in sorted(builds, key=lambda b: (b[2], b[3], b[4]['name'])):
        projects = channels.setdefault(channel, {
            'prettyname_regex': PRETTYNAME_REGEX,
            'project': {},
            'url': DOWNLOAD_BASE,
        })['project']
        entry = projects.setdefault(project, {
            'displayName': DISPLAY_NAMES.get(project, project),
            'releases': {},
        })
        file_info = {
            'name': asset['name'],
            'size': str(asset['size']),
            'subpath': tag,
            'timestamp': timestamp(asset.get('updated_at') or published_at),
        }
        digest = asset.get('digest') or ''
        if digest.startswith('sha256:'):
            file_info['sha256'] = digest[len('sha256:'):]
        # updater sorts release keys with key=int, reverse=True -> highest index is newest
        entry['releases'][str(len(entry['releases']))] = {'file': dict(sorted(file_info.items()))}
    return dict(sorted(channels.items()))


def check_unique_names(data):
    """Replicate the updater's name lookup and make sure every build resolves to itself."""
    regex = re.compile(PRETTYNAME_REGEX)
    for channel, channel_data in data.items():
        for project, project_data in channel_data['project'].items():
            releases = project_data['releases']
            ordered = [releases[i]['file']['name'] for i in sorted(releases, key=int, reverse=True)]
            for name in ordered:
                matches = regex.findall(name)
                if not matches:
                    raise ValueError(f'{channel}/{project}: prettyname_regex does not match {name}')
                resolved = next(n for n in ordered if matches[0] in n)
                if resolved != name:
                    raise ValueError(f'{channel}/{project}: "{matches[0]}" would download {resolved}')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('-o', '--output', default='releases.json')
    parser.add_argument('--include-debug', action='store_true', help='also list the -debug builds')
    args = parser.parse_args()

    builds = collect_builds(fetch_releases(os.environ.get('GITHUB_TOKEN')), args.include_debug)
    if not builds:
        # never replace a working channel with an empty one because of an API hiccup
        sys.exit('no usable update tarballs found, releases.json left untouched')
    data = build_json(builds)
    check_unique_names(data)

    content = json.dumps(data, indent=2) + '\n'
    try:
        with open(args.output, encoding='utf-8') as f:
            if f.read() == content:
                print(f'{args.output} unchanged ({len(builds)} builds)')
                return
    except FileNotFoundError:
        pass
    with open(args.output, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print(f'{args.output} written ({len(builds)} builds)')


if __name__ == '__main__':
    main()
