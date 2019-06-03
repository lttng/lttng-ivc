import sys
import os
import yaml
import logging
import hashlib

from git import Repo

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(dir_path, ".."))

import settings as Settings

def is_ref_branch(repo, ref):
    try:
        repo.remote().refs[ref]
        is_branch = True
    except:
        is_branch = False

    return is_branch


def is_ref_tag(repo, ref):
    try:
        repo.tags[ref]
        is_tag = True
    except:
        is_tag = False

    return is_tag


def is_ref_commit(repo, ref):
    try:
        Repo.rev_parse(repo, ref)
        is_commit = True
    except:
        is_commit = False

    return is_commit


def logging_setup():
    logger_format = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
    logging.basicConfig(level=logging.DEBUG,
                        format=logger_format,
                        datefmt='%m-%d %H:%M',
                        filename='./debug.log',
                        filemode='w')
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)


logging_setup()

# Remote setup
logger_git = logging.getLogger('setup.git')

# Fetch local base repository
with open(Settings.configuration_file, 'r') as stream:
    config = yaml.load(stream, Loader=yaml.FullLoader)

# Validate that all default dependancy are present.
# TODO: move to function
projects_markers = set()
for project, markers in config.items():
    if markers is None:
        continue
    for marker in markers:
        projects_markers.add(marker['marker'])

for project, markers in config.items():
    if markers is None:
        continue
    for marker in markers:
        if 'precook_deps' in marker:
            for dep in marker['precook_deps']:
                if dep not in projects_markers:
                    raise Exception("{} is not defined".format(dep))


# Retrieve all possibles remotes and clean url for path
remotes = {}
for project, markers in config.items():
    if markers is None:
        continue
    for marker in markers:
        url = marker['url']
        url2path = hashlib.sha1(url.encode('utf8')).hexdigest()
        path = os.path.abspath(Settings.git_remote_folder + '/' + url2path)
        remotes[url] = path

logger_git.info('Remotes to be fetched {}'.format(remotes))

if not os.path.isdir(Settings.git_remote_folder):
    os.makedirs(Settings.git_remote_folder)

# Fetch the remote
for url, path in remotes.items():
    if os.path.exists(path):
        if not os.path.isdir(path):
            logger_git.error('Remote path {} exists and is not a folder'.format(path))
            exit()
        repo = Repo(path)
    else:
        repo = Repo.clone_from(url, path)

    # TODO: might be necessary to actually update the base branch, to validate
    repo.remote().fetch()

# Create marker definition for test runners
runnable_markers = {}
for project, markers in config.items():
    if markers is None:
        continue
    for marker in markers:
        name = marker['marker']
        ref = marker['ref']
        url = marker['url']
        if 'precook_deps' in marker:
            deps = marker['precook_deps']
        else:
            deps = []

        path = remotes[url]
        repo = Repo(path)

        git_object = None
        if is_ref_branch(repo, ref):
            git_object = Repo.rev_parse(repo, repo.remote().refs[ref].name)
        elif is_ref_tag(repo, ref):
            git_object = repo.tags[ref].commit
        elif is_ref_commit(repo, ref):
            git_object = repo.commit(ref)

        if git_object is None:
            logger_git.error('Invalid git reference for marker "{}"'.format(name))
            exit(1)

        logger_git.info('Marker:{: <30}  Sha1 {: <20}'.format(name, git_object.hexsha))

        if name in runnable_markers:
            logger_git.error('Duplicate for entry for marker "{}"'.format(name))
            exit(1)

        runnable_markers[name] = {
                'project': project,
                'sha1': git_object.hexsha,
                'url': url,
                'path': path,
                'deps': deps
        }

with open(Settings.run_configuration_file, 'w') as run_configuration:
    yaml.dump(runnable_markers, run_configuration, default_flow_style=False)
