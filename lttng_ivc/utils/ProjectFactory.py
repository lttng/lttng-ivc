# Copyright (c) 2017 Jonathan Rajotte-Julien <jonathan.rajotte-julien@efficios.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import logging
import yaml
import pickle

import lttng_ivc.utils.project as Project
import lttng_ivc.settings as Settings

from lttng_ivc.utils.utils import sha256_checksum

_logger = logging.getLogger('project.factory')
_project_constructor = {
        'babeltrace': Project.Babeltrace,
        'lttng-modules': Project.Lttng_modules,
        'lttng-tools': Project.Lttng_tools,
        'lttng-ust': Project.Lttng_ust,
}

__projects_cache = {}

_project_py_checksum = sha256_checksum(Settings.project_py_file_location)

_markers = None
with open(Settings.run_configuration_file, 'r') as stream:
    # This is voluntary static across calls, no need to perform this
    # every time.
    _markers = yaml.load(stream, Loader=yaml.FullLoader)


def get_fresh(label, tmpdir):
    if label not in _markers:
        # TODO: specialized exception, handle it caller-side so the caller
        # can decide to skip or fail test.
        raise Exception('Label is no present')
    marker = _markers[label]
    constructor = _project_constructor[marker['project']]
    path = marker['path']
    sha1 = marker['sha1']
    return constructor(label, path, sha1, tmpdir)


def _validate_pickle(pickle, label):
    _logger.debug("Checking validate for {} {}".format(pickle,
                                                       label))
    if pickle._py_file_checksum != _project_py_checksum:
        _logger.warn("Project py file changed".format(pickle.label,
                                                      label))
        return False

    if pickle.label != label:
        _logger.warn("Label  {} and {} are not the same".format(pickle.label,
                                                                label))
        return False
    if pickle.sha1 != _markers[label]['sha1']:
        _logger.warn("Sha1  {} and {} are not the same".format(pickle.sha1,
            _markers[label]['sha1']))
        return False

    deps = _markers[label]['deps']
    if len(deps) != len(pickle.dependencies):
        _logger.warn("Len {} and {} are not the same".format(len(deps),
            len(pickle.dependencies)))
        return False
    for dep in deps:
        if dep not in pickle.dependencies:
            _logger.warn("Dep {} is not in {}".format(dep,
                pickle.dependencies))
            return False
        else:
            _logger.debug("Calling validate {} {}".format(pickle.dependencies[dep],
                dep))
            valid = _validate_pickle(pickle.dependencies[dep], dep)
            if not valid:
                return False
    return True


def get_precook(label):
    """
    Retrieve a precooked immutable projects from a cache if present
    otherwise the project is built, installed and cached for future access.
    """
    if label not in _markers:
        # TODO: specialized exception, handle it caller-side so the caller
        # can decide to skip or fail test.
        raise Exception('Label is no present')
    marker = _markers[label]
    constructor = _project_constructor[marker['project']]
    path = marker['path']
    sha1 = marker['sha1']
    deps = marker['deps']

    # Cache path for the label
    cache_path = os.path.join(Settings.projects_cache_folder, label)
    pickle_path = os.path.join(cache_path, label+".pickle")

    # Check if Pickle Rick is present and valid. If so return it asap.
    if os.path.exists(pickle_path):
        with open(pickle_path, 'rb') as pickle_file:
            pickled = pickle.load(pickle_file)
        if _validate_pickle(pickled, label):
            return pickled
        else:
            pickled.cleanup()
            _logger.warn("Pickle for {} is invalid. Rebuilding".format(label))

    project = constructor(label, path, sha1, cache_path)

    for dep in deps:
        obj_dep = get_precook(dep)
        project.dependencies[dep] = obj_dep

    project.autobuild()
    project._immutable = True
    with open(pickle_path, 'wb') as pickle_file:
        pickle.dump(project, pickle_file)

    return project
