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

import pytest
import os
import shutil
import signal
import subprocess
import time
import socket

import lttng_ivc.utils.ProjectFactory as ProjectFactory
import lttng_ivc.utils.utils as utils
import lttng_ivc.utils.runtime as Run
import lttng_ivc.settings as Settings

"""
TODO: Add Command header section
"""

"""
TODO: snapshot, file rotation, rotate
"""

"""
First member: relayd via lttng-tools
Second member: consumerd via lttng-tools
"""
test_matrix_streaming_base = [
        ("lttng-tools-2.7",  "lttng-tools-2.7",  True),
        ("lttng-tools-2.7",  "lttng-tools-2.8",  True),
        ("lttng-tools-2.7",  "lttng-tools-2.9",  True),
        ("lttng-tools-2.7",  "lttng-tools-2.10", True),
        ("lttng-tools-2.7",  "lttng-tools-2.11", True),
        ("lttng-tools-2.8",  "lttng-tools-2.7",  True),
        ("lttng-tools-2.8",  "lttng-tools-2.8",  True),
        ("lttng-tools-2.8",  "lttng-tools-2.9",  True),
        ("lttng-tools-2.8",  "lttng-tools-2.10", True),
        ("lttng-tools-2.8",  "lttng-tools-2.11", True),
        ("lttng-tools-2.9",  "lttng-tools-2.7",  True),
        ("lttng-tools-2.9",  "lttng-tools-2.8",  True),
        ("lttng-tools-2.9",  "lttng-tools-2.9",  True),
        ("lttng-tools-2.9",  "lttng-tools-2.10", True),
        ("lttng-tools-2.9",  "lttng-tools-2.11", True),
        ("lttng-tools-2.10", "lttng-tools-2.7",  True),
        ("lttng-tools-2.10", "lttng-tools-2.8",  True),
        ("lttng-tools-2.10", "lttng-tools-2.9",  True),
        ("lttng-tools-2.10", "lttng-tools-2.10", True),
        ("lttng-tools-2.10", "lttng-tools-2.11", True),
        ("lttng-tools-2.11", "lttng-tools-2.7",  True),
        ("lttng-tools-2.11", "lttng-tools-2.8",  True),
        ("lttng-tools-2.11", "lttng-tools-2.9",  True),
        ("lttng-tools-2.11", "lttng-tools-2.10", True),
        ("lttng-tools-2.11", "lttng-tools-2.11", True),
]

test_matrix_streaming_regenerate_metadata = [
        ("lttng-tools-2.7",  "lttng-tools-2.7",  "metadata regenerate", "Unsupported by tools"),
        ("lttng-tools-2.7",  "lttng-tools-2.8",  "metadata regenerate", "Unsupported by relayd"),
        ("lttng-tools-2.7",  "lttng-tools-2.9",  "regenerate metadata", "Unsupported by relayd"),
        ("lttng-tools-2.7",  "lttng-tools-2.10", "regenerate metadata", "Unsupported by relayd"),
        ("lttng-tools-2.7",  "lttng-tools-2.11", "regenerate metadata", "Unsupported by relayd"),
        ("lttng-tools-2.8",  "lttng-tools-2.7",  "metadata regenerate", "Unsupported by tools"),
        ("lttng-tools-2.8",  "lttng-tools-2.8",  "metadata regenerate", "Supported"),
        ("lttng-tools-2.8",  "lttng-tools-2.9",  "regenerate metadata", "Supported"),
        ("lttng-tools-2.8",  "lttng-tools-2.10", "regenerate metadata", "Supported"),
        ("lttng-tools-2.8",  "lttng-tools-2.11", "regenerate metadata", "Supported"),
        ("lttng-tools-2.9",  "lttng-tools-2.7",  "metadata regenerate", "Unsupported by tools"),
        ("lttng-tools-2.9",  "lttng-tools-2.8",  "metadata regenerate", "Supported"),
        ("lttng-tools-2.9",  "lttng-tools-2.9",  "regenerate metadata", "Supported"),
        ("lttng-tools-2.9",  "lttng-tools-2.10", "regenerate metadata", "Supported"),
        ("lttng-tools-2.9",  "lttng-tools-2.11", "regenerate metadata", "Supported"),
        ("lttng-tools-2.10", "lttng-tools-2.7",  "metadata regenerate", "Unsupported by tools"),
        ("lttng-tools-2.10", "lttng-tools-2.8",  "metadata regenerate", "Supported"),
        ("lttng-tools-2.10", "lttng-tools-2.9",  "regenerate metadata", "Supported"),
        ("lttng-tools-2.10", "lttng-tools-2.10", "regenerate metadata", "Supported"),
        ("lttng-tools-2.10", "lttng-tools-2.11", "regenerate metadata", "Supported"),
        ("lttng-tools-2.11", "lttng-tools-2.7",  "metadata regenerate", "Unsupported by tools"),
        ("lttng-tools-2.11", "lttng-tools-2.8",  "metadata regenerate", "Supported"),
        ("lttng-tools-2.11", "lttng-tools-2.9",  "regenerate metadata", "Supported"),
        ("lttng-tools-2.11", "lttng-tools-2.10", "regenerate metadata", "Supported"),
        ("lttng-tools-2.11", "lttng-tools-2.11", "regenerate metadata", "Supported"),
]

test_matrix_live_base = [
        ("lttng-tools-2.7",  "lttng-tools-2.7",  True),
        ("lttng-tools-2.7",  "lttng-tools-2.8",  True),
        ("lttng-tools-2.7",  "lttng-tools-2.9",  True),
        ("lttng-tools-2.7",  "lttng-tools-2.10", True),
        ("lttng-tools-2.7",  "lttng-tools-2.11", True),
        ("lttng-tools-2.8",  "lttng-tools-2.7",  True),
        ("lttng-tools-2.8",  "lttng-tools-2.8",  True),
        ("lttng-tools-2.8",  "lttng-tools-2.9",  True),
        ("lttng-tools-2.8",  "lttng-tools-2.10", True),
        ("lttng-tools-2.8",  "lttng-tools-2.11", True),
        ("lttng-tools-2.9",  "lttng-tools-2.7",  True),
        ("lttng-tools-2.9",  "lttng-tools-2.8",  True),
        ("lttng-tools-2.9",  "lttng-tools-2.9",  True),
        ("lttng-tools-2.9",  "lttng-tools-2.10", True),
        ("lttng-tools-2.9",  "lttng-tools-2.11", True),
        ("lttng-tools-2.10", "lttng-tools-2.7",  True),
        ("lttng-tools-2.10", "lttng-tools-2.8",  True),
        ("lttng-tools-2.10", "lttng-tools-2.9",  True),
        ("lttng-tools-2.10", "lttng-tools-2.10", True),
        ("lttng-tools-2.10", "lttng-tools-2.11", True),
        ("lttng-tools-2.11", "lttng-tools-2.7",  True),
        ("lttng-tools-2.11", "lttng-tools-2.8",  True),
        ("lttng-tools-2.11", "lttng-tools-2.9",  True),
        ("lttng-tools-2.11", "lttng-tools-2.10", True),
        ("lttng-tools-2.11", "lttng-tools-2.11", True),
]

runtime_matrix_streaming_base = []
runtime_matrix_streaming_regenerate_metadata = []
runtime_matrix_live_base = []

if not Settings.test_only:
    runtime_matrix_streaming_base = test_matrix_streaming_base
    runtime_matrix_streaming_regenerate_metadata = test_matrix_streaming_regenerate_metadata
    runtime_matrix_live_base = test_matrix_live_base
else:
    for tup in test_matrix_streaming_base:
        if (tup[0] in Settings.test_only or tup[1] in
                Settings.test_only):
            runtime_matrix_streaming_base.append(tup)
    for tup in test_matrix_streaming_regenerate_metadata:
        if (tup[0] in Settings.test_only or tup[1] in
                Settings.test_only):
            runtime_matrix_streaming_regenerate_metadata.append(tup)
    for tup in test_matrix_live_base:
        if (tup[0] in Settings.test_only or tup[1] in
                Settings.test_only):
            runtime_matrix_live_base.append(tup)

@pytest.mark.parametrize("relayd_label,consumerd_label,scenario", runtime_matrix_streaming_base)
def test_relayd_vs_consumerd_streaming_base(tmpdir, relayd_label, consumerd_label, scenario):

    nb_loop = 100
    nb_expected_events = 100

    # Prepare environment
    relayd = ProjectFactory.get_precook(relayd_label)
    consumerd = ProjectFactory.get_precook(consumerd_label)
    babeltrace = ProjectFactory.get_precook(Settings.default_babeltrace)

    relayd_runtime_path = os.path.join(str(tmpdir), "relayd")
    consumerd_runtime_path = os.path.join(str(tmpdir), "consumerd")
    app_path = os.path.join(str(tmpdir), "app")

    with Run.get_runtime(relayd_runtime_path) as runtime_relayd, Run.get_runtime(consumerd_runtime_path) as runtime_consumerd:
        runtime_relayd.add_project(relayd)
        runtime_relayd.add_project(babeltrace)
        runtime_consumerd.add_project(consumerd)

        # Make application using the ust runtime
        shutil.copytree(Settings.apps_gen_events_folder, app_path)
        runtime_consumerd.run("make V=1", cwd=app_path)

        # Start lttng-sessiond
        relayd, ctrl_port, data_port, live_port = utils.relayd_spawn(runtime_relayd)
        sessiond = utils.sessiond_spawn(runtime_consumerd)

        url = "net://localhost:{}:{}".format(ctrl_port, data_port)

        # Create session using mi to get path and session name
        runtime_consumerd.run('lttng create --set-url={} trace '.format(url))

        runtime_consumerd.run('lttng enable-event -u tp:tptest')
        runtime_consumerd.run('lttng start')

        # Run application
        cmd = './app {}'.format(nb_loop)
        runtime_consumerd.run(cmd, cwd=app_path)

        # Stop tracing
        runtime_consumerd.run('lttng stop')
        runtime_consumerd.run('lttng destroy -a')
        runtime_consumerd.subprocess_terminate(sessiond)

        # TODO check for error.
        runtime_relayd.subprocess_terminate(relayd)


        # Read trace with babeltrace and check for event count via number of line
        cmd = 'babeltrace {}'.format(runtime_relayd.lttng_home)
        cp_process, cp_out, cp_err = runtime_relayd.run(cmd)
        assert(utils.line_count(cp_out) == nb_expected_events)


@pytest.mark.parametrize("relayd_label,consumerd_label,command, scenario", runtime_matrix_streaming_regenerate_metadata)
def test_relayd_vs_consumerd_streaming_regenerate_metadata(tmpdir, relayd_label, consumerd_label, command, scenario):

    nb_loop = 100
    nb_expected_events = 100

    # Prepare environment
    relayd = ProjectFactory.get_precook(relayd_label)
    consumerd = ProjectFactory.get_precook(consumerd_label)
    babeltrace = ProjectFactory.get_precook(Settings.default_babeltrace)

    relayd_runtime_path = os.path.join(str(tmpdir), "relayd")
    consumerd_runtime_path = os.path.join(str(tmpdir), "consumerd")
    app_path = os.path.join(str(tmpdir), "app")


    with Run.get_runtime(relayd_runtime_path) as runtime_relayd, Run.get_runtime(consumerd_runtime_path) as runtime_consumerd:
        runtime_relayd.add_project(relayd)
        runtime_relayd.add_project(babeltrace)
        runtime_consumerd.add_project(consumerd)

        babeltrace_cmd = 'babeltrace {}'.format(runtime_relayd.lttng_home)

        # Make application using the ust runtime
        shutil.copytree(Settings.apps_gen_events_folder, app_path)
        runtime_consumerd.run("make V=1", cwd=app_path)

        # Start lttng-relayd
        relayd, ctrl_port, data_port, live_port = utils.relayd_spawn(runtime_relayd)
        sessiond = utils.sessiond_spawn(runtime_consumerd)

        url = "net://localhost:{}:{}".format(ctrl_port, data_port)

        # Create session using mi to get path and session name
        runtime_consumerd.run('lttng create --set-url={} trace '.format(url))

        runtime_consumerd.run('lttng enable-event -u tp:tptest')
        runtime_consumerd.run('lttng start')

        # Run application
        cmd = './app {}'.format(nb_loop)
        runtime_consumerd.run(cmd, cwd=app_path)

        # Stop tracing
        runtime_consumerd.run('lttng stop')

        # Empty the metadata file
        metadata = utils.find_file(runtime_relayd.lttng_home, "metadata")
        open(metadata, 'w').close()

        # Babeltrace should never be able to parse the trace
        with pytest.raises(subprocess.CalledProcessError):
            runtime_relayd.run(babeltrace_cmd)

        runtime_consumerd.run("lttng start")

        # TODO: rework this a bit to differentiate each errors and rework how
        # the condition are meet
        if scenario in ("Unsupported by tools", "Unsupported by relayd"):
            with pytest.raises(subprocess.CalledProcessError):
                runtime_consumerd.run("lttng {}".format(command))

            # Make sure everything looks good on this side
            sessiond = runtime_consumerd.subprocess_terminate(sessiond)
            if sessiond.returncode != 0:
                pytest.fail("Return value of sessiond is not zero")
            relayd = runtime_relayd.subprocess_terminate(relayd)
            if relayd.returncode != 0:
                pytest.fail("Return value of relayd is not zero")
            return

        runtime_consumerd.run("lttng {}".format(command))

        runtime_consumerd.run('lttng stop')
        runtime_consumerd.run('lttng destroy -a')

        # Make sure everything looks good
        sessiond = runtime_consumerd.subprocess_terminate(sessiond)
        if sessiond.returncode != 0:
            pytest.fail("Return value of sessiond is not zero")
        relayd = runtime_relayd.subprocess_terminate(relayd)
        if relayd.returncode != 0:
            pytest.fail("Return value of relayd is not zero")

        # Read trace with babeltrace and check for event count via number of line
        cp_process, cp_out, cp_err = runtime_relayd.run(babeltrace_cmd)
        assert utils.line_count(cp_out) == nb_expected_events

@pytest.mark.parametrize("relayd_label,consumerd_label,scenario", runtime_matrix_streaming_base)
def test_relayd_vs_consumerd_live_base(tmpdir, relayd_label, consumerd_label, scenario):

    nb_loop = 100
    nb_expected_events = 100

    # Prepare environment
    relayd = ProjectFactory.get_precook(relayd_label)
    consumerd = ProjectFactory.get_precook(consumerd_label)
    babeltrace = ProjectFactory.get_precook(Settings.default_babeltrace)

    relayd_runtime_path = os.path.join(str(tmpdir), "relayd")
    consumerd_runtime_path = os.path.join(str(tmpdir), "consumerd")
    app_path = os.path.join(str(tmpdir), "app")

    with Run.get_runtime(relayd_runtime_path) as runtime_relayd, Run.get_runtime(consumerd_runtime_path) as runtime_consumerd:
        runtime_relayd.add_project(relayd)
        runtime_relayd.add_project(babeltrace)
        runtime_consumerd.add_project(consumerd)

        # Make application using the ust runtime
        shutil.copytree(Settings.apps_gen_events_folder, app_path)
        runtime_consumerd.run("make V=1", cwd=app_path)

        # Start lttng-relayd
        relayd, ctrl_port, data_port, live_port = utils.relayd_spawn(runtime_relayd)
        sessiond = utils.sessiond_spawn(runtime_consumerd)

        url = "net://localhost:{}:{}".format(ctrl_port, data_port)

        # Create session using mi to get path and session name
        runtime_consumerd.run('lttng create --live --set-url={} trace '.format(url))

        runtime_consumerd.run('lttng enable-event -u tp:tptest')
        runtime_consumerd.run('lttng start')

        # Run application
        cmd = './app {}'.format(nb_loop)
        runtime_consumerd.run(cmd, cwd=app_path)

        # Stop tracing
        runtime_consumerd.run('lttng stop')
        runtime_consumerd.run('lttng destroy -a')
        runtime_consumerd.subprocess_terminate(sessiond)

        # TODO check for error.
        runtime_relayd.subprocess_terminate(relayd)


        # Read trace with babeltrace and check for event count via number of line
        cmd = 'babeltrace {}'.format(runtime_relayd.lttng_home)
        cp_process, cp_out, cp_err = runtime_relayd.run(cmd)
        assert(utils.line_count(cp_out) == nb_expected_events)


