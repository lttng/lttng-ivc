import pytest
import subprocess
import platform
import shutil
import os

import lttng_ivc.utils.ProjectFactory as ProjectFactory
import lttng_ivc.utils.utils as utils
import lttng_ivc.utils.runtime as Run
import lttng_ivc.settings as Settings

"""
FC: Fully Compatible
I: Incompatible

+------------------------------------------------------------------------------+
|                 LTTng consumer daemon vs LTTng session daemon                |
+--------------------------+------------+------------+------------+------------+
| Consumerd/Sessiond       | 2.7        | 2.8        | 2.9        | 2.10       |
+--------------------------+------------+------------+------------+------------+
| 2.7                      | FC         | I          | I          | I          |
| 2.8                      | I          | FC         | I          | I          |
| 2.9                      | I          | I          | FC         | I          |
| 2.10                     | I          | I          | I          | FC         |
+--------------------------+------------+------------+------------+------------+

"""

test_matrix_consumerd = [
    ("lttng-tools-2.7",  "lttng-tools-2.7",   True),
    ("lttng-tools-2.7",  "lttng-tools-2.8",   False),
    ("lttng-tools-2.7",  "lttng-tools-2.9",   False),
    ("lttng-tools-2.7",  "lttng-tools-2.10",  False),
    ("lttng-tools-2.8",  "lttng-tools-2.7",   False),
    ("lttng-tools-2.8",  "lttng-tools-2.8",   True),
    ("lttng-tools-2.8",  "lttng-tools-2.9",   True),
    ("lttng-tools-2.8",  "lttng-tools-2.10",  False),
    ("lttng-tools-2.9",  "lttng-tools-2.7",   False),
    ("lttng-tools-2.9",  "lttng-tools-2.8",   True),
    ("lttng-tools-2.9",  "lttng-tools-2.9",   True),
    ("lttng-tools-2.9",  "lttng-tools-2.10",  False),
    ("lttng-tools-2.10",  "lttng-tools-2.7",  False),
    ("lttng-tools-2.10",  "lttng-tools-2.8",  False),
    ("lttng-tools-2.10",  "lttng-tools-2.9",  False),
    ("lttng-tools-2.10",  "lttng-tools-2.10", True),
]

runtime_matrix_consumerd = []

if not Settings.test_only:
    runtime_matrix_consumerd = test_matrix_consumerd
else:
    for tup in test_matrix_consumerd:
        if (tup[0] in Settings.test_only or tup[1] in
                Settings.test_only):
            runtime_matrix_consumerd.append(tup)


@pytest.mark.parametrize("consumerd_l,tools_l,should_work", runtime_matrix_consumerd)
def test_consumerd_vs_sessiond(tmpdir, consumerd_l, tools_l, should_work):

    # Prepare environment
    consumerd = ProjectFactory.get_precook(consumerd_l)
    tools = ProjectFactory.get_precook(tools_l)

    app_path = os.path.join(str(tmpdir), "app")

    replacement_consumerd = utils.find_file(consumerd.installation_path, "lttng-consumerd")
    assert(replacement_consumerd)

    c_dict = {"32bit": "-consumerd32-path", "64bit": "--consumerd64-path"}
    platform_type = platform.architecture()[0]

    sessiond_opt_args = "{}={}".format(c_dict[platform_type], replacement_consumerd)

    with Run.get_runtime(str(tmpdir)) as runtime:
        runtime.add_project(tools)

        shutil.copytree(Settings.apps_gen_events_folder, app_path)
        runtime.run("make V=1", cwd=app_path)

        utils.sessiond_spawn(runtime, sessiond_opt_args)

        # Consumer is only called on channel creation
        runtime.run("lttng create")
        try:
            runtime.run("lttng enable-event -u tp:test", timeout=5)
            runtime.run("lttng start", timeout=5)

            # Run application
            cmd = './app {}'.format(100)
            runtime.run(cmd, cwd=app_path)

            runtime.run("lttng destroy -a", timeout=5)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            if should_work:
                raise e
        if not should_work:
            raise Exception("Supposed to fail")

