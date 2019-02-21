import argparse
import os
import sys
import json
from shutil import copyfile


DIR_INFO_TEMPLATE = '''
        <dir minversion="{minversion}">
            <info compressed="false">{addon_url}</info>
            <checksum>{checksum_url}</checksum>
            <datadir zip="true">{datadir_url}</datadir>
        </dir>
'''


def main():
    parser = argparse.ArgumentParser(description='Create a Kodi repository addon.xml')
    parser.add_argument('repo_user', help='The repository username')
    parser.add_argument('repo_name', help='The repository name')
    parser.add_argument('repo_addon_folder', help='Folder path for the generated repo addon')
    parser.add_argument(
        '--template', '-t', default='templates/repo.addon.xml.tmpl',
        help='Path to the addon.xml template file')
    parser.add_argument(
        '--icon', '-i', default='templates/icon.png',
        help='Path to the icon.png file')
    parser.add_argument(
        '--fanart', '-f', default='templates/fanart.jpg',
        help='Path to the fanart.jpg file')
    parser.add_argument(
        '--config', '-c', default='config.json',
        help='Path to config.json')
    parser.add_argument(
        '--datadir', '-d', default='datadir',
        help='path to datadir')

    args = parser.parse_args()

    if not os.path.isdir(args.repo_addon_folder):
        print('Invalid repo_addon_folder: {}'.format(args.repo_addon_folder))
        sys.exit(1)

    if not os.path.isfile(args.template):
        print('Invalid template: {}'.format(args.template))
        sys.exit(1)

    if not os.path.isfile(args.icon):
        print('Invalid icon: {}'.format(args.icon))
        sys.exit(1)

    if not os.path.isfile(args.config):
        print('Invalid config: {}'.format(args.config))
        sys.exit(1)

    repo_addon_name = 'repository.{}.{}'.format(
        args.repo_user,
        args.repo_name,
    )
    repo_addon_src = os.path.join(args.repo_addon_folder, repo_addon_name)
    if os.path.isdir(repo_addon_src):
        print('The repo addon folder already exists: {}'.format(repo_addon_src))
        sys.exit(1)

    os.mkdir(repo_addon_src)
    output_file = os.path.join(repo_addon_src, 'addon.xml')
    os.mkdir(os.path.join(repo_addon_src, 'resources'))
    icon_file = os.path.join(repo_addon_src, 'resources', 'icon.png')
    copyfile(args.icon, icon_file)
    fanart_file = ''
    if args.fanart and os.path.isfile(args.fanart):
        fanart_file = os.path.join(repo_addon_src, 'resources', 'fanart.jpg')
        copyfile(args.fanart, fanart_file)

    with open(args.template, 'r') as template_file, \
            open(args.config, 'r') as config_file, \
            open(output_file, 'w') as output:
        config = json.load(config_file)
        branches = config.get('branchmap', [])
        dir_info = ''
        for b in branches:
            dir_info = dir_info + DIR_INFO_TEMPLATE.format(
                minversion=b['minversion'],
                addon_url='https://{}.github.io/{}/{}/addons.xml'.format(
                    args.repo_user, args.repo_name, b['name']),
                checksum_url='https://{}.github.io/{}/{}/addons.xml.md5'.format(
                    args.repo_user, args.repo_name, b['name']),
                datadir_url='https://{}.github.io/{}/{}/{}/'.format(
                    args.repo_user, args.repo_name, b['name'], args.datadir)
            )
        template_string = template_file.read()
        output.write(template_string.format(
            repo_addon_id=repo_addon_name,
            repo_addon_name='{}/{} Repository'.format(args.repo_user, args.repo_name),
            repo_addon_provider=args.repo_user,
            repo_addon_version='1.0.1',
            repo_dir=dir_info,
            repo_addon_summary='A personal Kodi addon repository from https://github.com/{}/{}'.format(
                args.repo_user, args.repo_name),
            fanart_file='resources/fanart.jpg' if fanart_file else '',
        ))

    print('Generated {}'.format(output_file))


if __name__ == "__main__":
    main()
