# Almost "Instant" Kodi Addon Repository

_Almost_ instant but not quite (/understatement)

[![Travis](https://img.shields.io/travis/ping/instant-kodi-repo.svg?style=flat-square)](https://travis-ci.org/ping/instant-kodi-repo/)

## Features
- Auto generates your personal Kodi addon repository hosted on GitHub
- Auto updates everytime you update your addon code
- Auto generates a repository addon zip for your new personal repository

[Demo](https://ping.github.io/instant-kodi-repo/)

## Get Started

These instructions require you to have a bash environment and git installed. Most Linux and Mac machines will already have these available by default. For Windows, you probably should install the [Git for Windows](https://github.com/git-for-windows/git/releases) and run the commands from Git Bash.

These instructions will be a 100x easier if you have a basic understanding of Git.

1. Create a new GitHub repository with the files from this repo or just fork this one if you don't care about names and such

1. Create an account at [Travis](https://travis-ci.org) and add your project to Travis: https://travis-ci.org/profile/

1. In terminal (or Git Bash), clone your repo locally
    ```
    git clone git@github.com:YOUR_USER_NAME/YOUR_REPO_NAME.git my_kodi_repo
    cd my_kodi_repo
    ```

1. Generate a GitHub deploy key
    ```
    ssh-keygen -q -t rsa -b 4096 -C 'put-your-repo-name-here' -f deploy_key -N ''
    ```
    If successful, you will see 2 files ``deploy_key`` and ``deploy_key.pub`` in the folder.

1. Copy the contents of the text file ``deploy_key.pub`` and set it as a new Deploy key for your project ``https://github.com/<your name>/<your repo>/settings/keys``. Remember to __allow write access__.

1. [Install the travis CLI client](https://github.com/travis-ci/travis.rb#installation)

1. From the Terminal, login with the travis cli
    ```
    travis login
    ```

1. Use ``travis`` to encrypt your ``deploy_key`` and save the encrypted key as ``.github/deploy_key.enc``
    ```bash
    # or go to where your repo folder is
    cd my_kodi_repo && rm .github/deploy_key.enc
    travis encrypt-file deploy_key .github/deploy_key.enc
    ```
    You should see something like
    ```
    encrypting deploy_key for yourname/your-repo-project
    storing result as deploy_key.enc
    storing secure env variables for decryption

    Please add the following to your build script (before_install stage in your .travis.yml, for instance):

        openssl aes-256-cbc -K $encrypted_0a6446eb3ae3_key -iv $encrypted_0a6446eb3ae3_key -in super_secret.txt.enc -out super_secret.txt -d

    Pro Tip: You can add it automatically by running with --add.

    Make sure to add deploy_key.enc to the git repository.
    Make sure not to add deploy_key to the git repository.
    Commit all changes to your .travis.yml.
    ```
    Look for the ["encryption label"](https://gist.github.com/domenic/ec8b0fc8ab45f39403dd#get-encrypted-credentials). For example, in the output above, ``0a6446eb3ae3`` is the encryption label.

1. Take the encryption label from the previous step and set it in the file ``.travis.yml``. Take this chance to also set your email address in ``.travis.yml``

1. Add your addon source code folders into the ``src/`` folder so that it looks like
    ```
    - src/
        - your.addon.folder.one/
        - your.addon.folder.two/
    ```

1. Git add your changes and new files and push it to your repo.
    ```
    git add -A .
    git push
    ```

1. If nothing goes wrong, you will have a personal Kodi addon repository at ``https://your_user_name.github.io/your_repo_name/`` in a few minutes.


## Advance Usage

By default, only the ``master`` branch is built to create an addons repository compatible with Krypton (minversion="17.0.0").

You can change this by customising ``.github/config.json`` and ``.travis.yml``.

For example, to make your repo only for Leia, edit ``.github/config.json`` to look like
```json
{
    "branchmap": [
        {
            "name": "master",
            "minversion": "17.9.0"
        }
    ]
}
```

If you have different branches for different Kodi versions:

``.github/config.json``
```json
{
    "branchmap": [
        {
            "name": "master",
            "minversion": "17.9.0"
        },
        {
            "name": "krypton",
            "minversion": "17.0.0"
        }
    ]
}
```

``.travis.yml``
```yml
branches:
  only:
    - master
    - krypton
```
