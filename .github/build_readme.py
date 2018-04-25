import argparse
import os
import sys
import xml.etree.ElementTree
from collections import namedtuple


Addon = namedtuple('Addon', ['id', 'name', 'version', 'zip'])


def main():
    parser = argparse.ArgumentParser(description='Create a readme for the kodi repo')
    parser.add_argument('repo_user', help='The repository username')
    parser.add_argument('repo_name', help='The repository name')
    parser.add_argument('addonsxml_path', help='Path to the generated addons.xml file')
    parser.add_argument('commit_hash', help='Commit hash')
    parser.add_argument(
        '--output', '-o', default='README.md',
        help='Path to the output README.md')
    parser.add_argument(
        '--template', '-t', default='templates/repo.readme.md.tmpl',
        help='Path to the README.md template file')
    parser.add_argument(
        '--datadir', '-d', default='datadir',
        help='datadir path for the repo')

    args = parser.parse_args()

    if not os.path.isfile(args.addonsxml_path):
        print('Invalid addson.xml path: {}'.format(args.addonsxml_path))
        sys.exit(1)

    if not os.path.isfile(args.template):
        print('Invalid template: {}'.format(args.template))
        sys.exit(1)

    tree = xml.etree.ElementTree.parse(args.addonsxml_path)
    addons = []

    repo_addon_id = 'repository.{}.{}'.format(
        args.repo_user,
        args.repo_name,
    )
    repo_addon_link = ''

    for addon in tree.getroot():
        if not addon.tag == 'addon':
            continue
        addon_id = addon.get('id')
        addon_nm = addon.get('name')
        addon_ver = addon.get('version')
        plugin_zip_link = '{datadir}/{id}/{id}-{ver}.zip'.format(
            id=addon_id, ver=addon_ver, datadir=args.datadir)
        addons.append(
            Addon(addon_id, addon_nm, addon_ver, plugin_zip_link)
        )
        if repo_addon_id == addon_id:
            repo_addon_link = plugin_zip_link

    addons_text = '\n'.join(
        [
            '- [__{nm}__]({link}) {id} v{ver}'.format(
                id=a.id, nm=a.name, link=a.zip, ver=a.version)
            for a in addons
        ]
    )

    with open(args.template, 'r') as template_file, open(args.output, 'w') as output_file:
        template_string = template_file.read()
        output_file.write(template_string.format(
            repo_user=args.repo_user,
            repo_name=args.repo_name,
            addons=addons_text,
            commit=args.commit_hash,
            repo_addon_link=repo_addon_link,
        ))


if __name__ == "__main__":
    main()
