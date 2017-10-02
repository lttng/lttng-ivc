import os
import logging
import yaml

import lttng_ivc.utils.project as Project


_logger = logging.getLogger('project.factory')
_conf_file = os.path.dirname(os.path.abspath(__file__)) + "/../run_configuration.yaml"
_project_constructor = {
        'babeltrace': Project.Babeltrace,
        'lttng-modules': Project.Lttng_modules,
        'lttng-tools': Project.Lttng_tools,
        'lttng-ust': Project.Lttng_ust,
}

_markers = None
with open(_conf_file, 'r') as stream:
    # This is voluntary static across call, no need to perform this
    # every time.
    _markers = yaml.load(stream)


def get(label, tmpdir):
    if label not in _markers:
        # TODO: specialized exception, handle it caller-side so the caller
        # can decide to skip or fail test.
        raise Exception('Label is no present')
    marker = _markers[label]
    constructor = _project_constructor[marker['project']]
    path = marker['path']
    sha1 = marker['sha1']
    return constructor(label, path, sha1, tmpdir)
