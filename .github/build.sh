#!/bin/bash

# Adapted from https://gist.github.com/domenic/ec8b0fc8ab45f39403dd

set -e

if [ "$TRAVIS_PULL_REQUEST" != 'false' ]; then
    # don't run for PRs
    exit 0
fi

CWD=$(pwd)
SOURCE_BRANCH="master"
TARGET_BRANCH="gh-pages"

BUILD_DIR="$HOME/.build"
SOURCES_DIR="$HOME/.sources"
REPO=`git config remote.origin.url`
SSH_REPO=${REPO/https:\/\/github.com\//git@github.com:}
SHA=`git rev-parse --verify HEAD`

REPO_USER=$(echo "$TRAVIS_REPO_SLUG" | grep -Eo '^([^/]+)')
REPO_NAME=$(echo "$TRAVIS_REPO_SLUG" | grep -Eo '([^/]+)$')

DATADIR='datadir'

git clone --quiet $REPO $BUILD_DIR

cd $BUILD_DIR
git checkout $TARGET_BRANCH || git checkout --orphan $TARGET_BRANCH

cd $CWD
# Clean out existing contents
rm -rf $BUILD_DIR/* || exit 1
rm -rf $BUILD_DIR/.github $BUILD_DIR/.travis.yml $BUILD_DIR/.gitignore || exit 1

# Download create_repository.py
create_repo_script_url='https://raw.githubusercontent.com/chadparry/kodi-repository.chad.parry.org/master/tools/create_repository.py'
create_repository_py='.github/create_repository.py'
wget -q -t 2 -O "$create_repository_py" "$create_repo_script_url" || curl --retry 2 -o "$create_repository_py" "$create_repo_script_url"

# Download jq
jq_url='https://github.com/stedolan/jq/releases/download/jq-1.5/jq-linux64'
jq_path='.github/jq'
wget -q -t 2 -O "$jq_path" "$jq_url" || curl --retry 2 -o "$jq_path" "$jq_url"
chmod +x "$jq_path"

# Iterate through config.json and clone each branch
# - Generate a repo addon for each branch
#   - repo addon will include all the branches
# - Generate a repo set of addons.xml, addons.xml.md5 etc for each branch
for b in $(cat .github/config.json | .github/jq -c .branchmap[]); do
    name=$(echo "$b" | .github/jq -r '.name')
    minversion=$(echo "$b" | .github/jq -r '.minversion')
    mkdir -p "$SOURCES_DIR/$name" "$SOURCES_DIR/$datadir"

    git clone --quiet --depth 1 "$REPO" -b "$name" "$SOURCES_DIR/$name"

    python .github/build_repo_addon.py "$REPO_USER" "$REPO_NAME" "$SOURCES_DIR/$name/src/" -t '.github/templates/repo.addon.xml.tmpl' -c '.github/config.json' -d "$DATADIR" --icon '.github/templates/icon.png' --fanart '.github/templates/fanart.jpg'

    # Do our repo build
    plugin_sources=''
    for d in "$SOURCES_DIR/$name/src/"* ; do
        if [ -d "$d" ]; then
            if [ ! -z "$plugin_sources" ]; then
                # Append a space
                plugin_sources="$plugin_sources "
            fi
            plugin_sources="$plugin_sources$d"
        fi
    done
    mkdir -p "$BUILD_DIR/$name/" "$BUILD_DIR/$name/$DATADIR/"
    python "$create_repository_py" -d "$BUILD_DIR/$name/$DATADIR/" -i "$BUILD_DIR/$name/addons.xml" -c "$BUILD_DIR/$name/addons.xml.md5" $plugin_sources

done

# Generate readme.md
python .github/build_readme.py "$REPO_USER" "$REPO_NAME" ".github/config.json" "$SHA" -t ".github/templates/repo.readme.md.tmpl" -o "$BUILD_DIR/README.md" -d "$DATADIR" -b "$BUILD_DIR"

cd $BUILD_DIR
git config user.name "Travis CI"
git config user.email "$COMMIT_AUTHOR_EMAIL"

if git diff --quiet; then
    echo "No changes to the output on this push; exiting."
    exit 0
fi

git add -A .
git commit -m "Deploy to GitHub Pages: ${SHA} (Travis Build: $TRAVIS_BUILD_NUMBER)"

# Get the deploy key by using Travis's stored variables to decrypt deploy_key.enc
ENCRYPTED_KEY_VAR="encrypted_${ENCRYPTION_LABEL}_key"
ENCRYPTED_IV_VAR="encrypted_${ENCRYPTION_LABEL}_iv"
ENCRYPTED_KEY=${!ENCRYPTED_KEY_VAR}
ENCRYPTED_IV=${!ENCRYPTED_IV_VAR}

eval `ssh-agent -s`
# Use stdin/stdout instead of key writing to disk
openssl aes-256-cbc -K $ENCRYPTED_KEY -iv $ENCRYPTED_IV -in "$CWD/.github/deploy_key.enc" -d | ssh-add -

# Now that we're all set up, we can push.
git push --quiet $SSH_REPO $TARGET_BRANCH

echo "Published to GitHub Pages https://$REPO_USER.github.io/$REPO_NAME/"
