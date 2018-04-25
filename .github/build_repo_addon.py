import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description='Create a Kodi repository addon.xml')
    parser.add_argument('repo_user', help='The repository username')
    parser.add_argument('repo_name', help='The repository name')
    parser.add_argument('repo_addon_folder', help='Folder path for the generated repo addon')
    parser.add_argument(
        '--template', '-t', default='templates/repo.addon.xml.tmpl',
        help='Path to the addon.xml template file')
    parser.add_argument(
        '--datadir', '-d', default='datadir',
        help='datadir path for the repo')

    args = parser.parse_args()

    if not os.path.isdir(args.repo_addon_folder):
        print('Invalid repo_addon_folder: {}'.format(args.repo_addon_folder))
        sys.exit(1)

    if not os.path.isfile(args.template):
        print('Invalid template: {}'.format(args.template))
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

    with open(args.template, 'r') as template_file, open(output_file, 'w') as output_file:
        template_string = template_file.read()
        output_file.write(template_string.format(
            repo_addon_id=repo_addon_name,
            repo_addon_name='{}/{} Repository'.format(args.repo_user, args.repo_name),
            repo_addon_provider=args.repo_user,
            repo_addon_version='1.0.0',
            repo_info_url='https://{}.github.io/{}/addons.xml'.format(
                args.repo_user, args.repo_name),
            repo_info_checksum_url='https://{}.github.io/{}/addons.xml.md5'.format(
                args.repo_user, args.repo_name),
            repo_info_datadir_url='https://{}.github.io/{}/{}/'.format(
                args.repo_user, args.repo_name, args.datadir),
            repo_addon_summary='A personal Kodi addon repository from https://github.com/{}/{}'.format(
                args.repo_user, args.repo_name)
        ))

    print('Generated {}'.format(output_file))


if __name__ == "__main__":
    main()
