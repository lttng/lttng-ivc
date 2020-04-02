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

import lttng_ivc.utils.ProjectFactory as ProjectFactory
import lttng_ivc.utils.utils as utils
import lttng_ivc.utils.runtime as Run
import lttng_ivc.settings as Settings

"""

FC: Fully Compatible
BC: Feature of the smallest version number will works.
TU: Tracing unavailable

Note: actual testing is limited by lttng-ust and lttng-tools abi/api.

TU is due to ust abi breaking.

+----------------------------------------------------------------------------------+
|             LTTng UST Java agent protocol vs LTTng session daemon                |
+--------------------------+------------+------------+------------+----------------+------------+------------+
| LTTng UST Java/ LTTng Tools  | 2.7 (1.0)  | 2.8 (2.0)  | 2.9 (2.0)  | 2.10 (2.0) | 2.11 (2.0) | 2.11 (2.0) |
+--------------------------+------------+------------+------------+----------------+------------+------------+
| 2.7 (1.0)                    | FC         | TU         | TU         | TU         | TU         | TU         |
| 2.8 (2.0)                    | TU         | FC         | BC         | BC         | TU         | TU         |
| 2.9 (2.0)                    | TU         | BC         | FC         | BC         | TU         | TU         |
| 2.10 (2.0)                   | TU         | BC         | BC         | FC         | TU         | TU         |
| 2.11 (2.0)                   | TU         | TU         | TU         | TU         | FC         | BC         |
| 2.12 (2.0)                   | TU         | TU         | TU         | TU         | BC         | FC         |
+--------------------------+------------+------------+------------+----------------+------------+------------+

"""

"""
First tuple member: lttng-ust label
Second tuple member: lttng-tool label
Third tuple member: app version to use
Fourth tuple member: expected scenario
"""

version_to_app = {1: Settings.apps_jul_1,
                  2: Settings.apps_jul_2}

test_matrix_tracing_available = [
    ("lttng-ust-2.7", "lttng-tools-2.7",   1, True),
    ("lttng-ust-2.7", "lttng-tools-2.8",   1, False),
    ("lttng-ust-2.7", "lttng-tools-2.9",   1, False),
    ("lttng-ust-2.7", "lttng-tools-2.10",  1, False),
    ("lttng-ust-2.7", "lttng-tools-2.11",  1, False),
    ("lttng-ust-2.7", "lttng-tools-2.12",  1, False),
    ("lttng-ust-2.8", "lttng-tools-2.7",   2, False),
    ("lttng-ust-2.8", "lttng-tools-2.8",   2, True),
    ("lttng-ust-2.8", "lttng-tools-2.9",   2, False),
    ("lttng-ust-2.8", "lttng-tools-2.10",  2, False),
    ("lttng-ust-2.8", "lttng-tools-2.11",  2, False),
    ("lttng-ust-2.8", "lttng-tools-2.12",  2, False),
    ("lttng-ust-2.9", "lttng-tools-2.7",   2, False),
    ("lttng-ust-2.9", "lttng-tools-2.8",   2, False),
    ("lttng-ust-2.9", "lttng-tools-2.9",   2, True),
    ("lttng-ust-2.9", "lttng-tools-2.10",  2, True),
    ("lttng-ust-2.9", "lttng-tools-2.11",  2, False),
    ("lttng-ust-2.9", "lttng-tools-2.12",  2, False),
    ("lttng-ust-2.10", "lttng-tools-2.7",  2, False),
    ("lttng-ust-2.10", "lttng-tools-2.8",  2, False),
    ("lttng-ust-2.10", "lttng-tools-2.9",  2, True),
    ("lttng-ust-2.10", "lttng-tools-2.10", 2, True),
    ("lttng-ust-2.10", "lttng-tools-2.11", 2, False),
    ("lttng-ust-2.10", "lttng-tools-2.12", 2, False),
    ("lttng-ust-2.11", "lttng-tools-2.7",  2, False),
    ("lttng-ust-2.11", "lttng-tools-2.8",  2, False),
    ("lttng-ust-2.11", "lttng-tools-2.9",  2, False),
    ("lttng-ust-2.11", "lttng-tools-2.10", 2, False),
    ("lttng-ust-2.11", "lttng-tools-2.11", 2, True),
    ("lttng-ust-2.11", "lttng-tools-2.12", 2, True),
    ("lttng-ust-2.12", "lttng-tools-2.7",  2, False),
    ("lttng-ust-2.12", "lttng-tools-2.8",  2, False),
    ("lttng-ust-2.12", "lttng-tools-2.9",  2, False),
    ("lttng-ust-2.12", "lttng-tools-2.10", 2, False),
    ("lttng-ust-2.12", "lttng-tools-2.11", 2, True),
    ("lttng-ust-2.12", "lttng-tools-2.12", 2, True),

]

test_matrix_agent_interface = [
    ("lttng-ust-2.7", "lttng-tools-2.7",   1, "Success"),
    ("lttng-ust-2.7", "lttng-tools-2.8",   1, "Unsupported protocol"),
    ("lttng-ust-2.7", "lttng-tools-2.9",   1, "Unsupported protocol"),
    ("lttng-ust-2.7", "lttng-tools-2.10",  1, "Unsupported protocol"),
    ("lttng-ust-2.7", "lttng-tools-2.11",  1, "Unsupported protocol"),
    ("lttng-ust-2.7", "lttng-tools-2.12",  1, "Unsupported protocol"),
    ("lttng-ust-2.8", "lttng-tools-2.7",   2, "Unsupported protocol"),
    ("lttng-ust-2.8", "lttng-tools-2.8",   2, "Success"),
    ("lttng-ust-2.8", "lttng-tools-2.9",   2, "Success"),
    ("lttng-ust-2.8", "lttng-tools-2.10",  2, "Success"),
    ("lttng-ust-2.8", "lttng-tools-2.11",  2, "Success"),
    ("lttng-ust-2.8", "lttng-tools-2.12",  2, "Success"),
    ("lttng-ust-2.9", "lttng-tools-2.7",   2, "Unsupported protocol"),
    ("lttng-ust-2.9", "lttng-tools-2.8",   2, "Success"),
    ("lttng-ust-2.9", "lttng-tools-2.9",   2, "Success"),
    ("lttng-ust-2.9", "lttng-tools-2.10",  2, "Success"),
    ("lttng-ust-2.9", "lttng-tools-2.11",  2, "Success"),
    ("lttng-ust-2.9", "lttng-tools-2.12",  2, "Success"),
    ("lttng-ust-2.10", "lttng-tools-2.7",  2, "Unsupported protocol"),
    ("lttng-ust-2.10", "lttng-tools-2.8",  2, "Success"),
    ("lttng-ust-2.10", "lttng-tools-2.9",  2, "Success"),
    ("lttng-ust-2.10", "lttng-tools-2.10", 2, "Success"),
    ("lttng-ust-2.10", "lttng-tools-2.11", 2, "Success"),
    ("lttng-ust-2.10", "lttng-tools-2.12", 2, "Success"),
    ("lttng-ust-2.11", "lttng-tools-2.7",  2, "Unsupported protocol"),
    ("lttng-ust-2.11", "lttng-tools-2.8",  2, "Success"),
    ("lttng-ust-2.11", "lttng-tools-2.9",  2, "Success"),
    ("lttng-ust-2.11", "lttng-tools-2.10", 2, "Success"),
    ("lttng-ust-2.11", "lttng-tools-2.11", 2, "Success"),
    ("lttng-ust-2.12", "lttng-tools-2.7",  2, "Unsupported protocol"),
    ("lttng-ust-2.12", "lttng-tools-2.8",  2, "Success"),
    ("lttng-ust-2.12", "lttng-tools-2.9",  2, "Success"),
    ("lttng-ust-2.12", "lttng-tools-2.10", 2, "Success"),
    ("lttng-ust-2.12", "lttng-tools-2.11", 2, "Success"),
    ("lttng-ust-2.12", "lttng-tools-2.12", 2, "Success"),
    ("lttng-ust-2.12", "lttng-tools-2.12", 2, "Success"),
]

runtime_matrix_tracing_available = Settings.generate_runtime_test_matrix(test_matrix_tracing_available, [0, 1])
runtime_matrix_agent_interface = Settings.generate_runtime_test_matrix(test_matrix_agent_interface, [0, 1])


@pytest.mark.parametrize("ust_label,tools_label,app_version,should_trace", runtime_matrix_tracing_available)
def test_ust_java_agent_tracing_available(tmpdir, ust_label, tools_label, app_version, should_trace):

    nb_iter = 100
    nb_events = 3 * nb_iter

    # Prepare environment
    ust = ProjectFactory.get_precook(ust_label)
    tools = ProjectFactory.get_precook(tools_label)
    babeltrace = ProjectFactory.get_precook(Settings.default_babeltrace)

    tools_runtime_path = os.path.join(str(tmpdir), "tools")
    ust_runtime_path = os.path.join(str(tmpdir), "ust")
    app_path = os.path.join(str(tmpdir), "app")

    with Run.get_runtime(ust_runtime_path) as runtime_app, Run.get_runtime(tools_runtime_path) as runtime_tools:
        runtime_tools.add_project(tools)
        runtime_tools.add_project(babeltrace)

        runtime_app.add_project(ust)
        runtime_app.lttng_home = runtime_tools.lttng_home

        trace_path = os.path.join(runtime_tools.lttng_home, 'trace')

        # Make application using the ust runtime
        shutil.copytree(version_to_app[app_version], app_path)
        runtime_app.run("javac App.java", cwd=app_path)

        # Start lttng-sessiond
        sessiond = utils.sessiond_spawn(runtime_tools)

        # Create session using mi to get path and session name
        runtime_tools.run('lttng create trace --output={}'.format(trace_path))

        runtime_tools.run('lttng enable-event -j jello')
        runtime_tools.run('lttng start')

        # Run application
        cmd = 'java App {}'.format(nb_iter)
        runtime_app.run(cmd, cwd=app_path)

        # Stop tracing
        runtime_tools.run('lttng stop')
        runtime_tools.run('lttng destroy -a')
        cp = runtime_tools.subprocess_terminate(sessiond)
        if cp.returncode != 0:
            pytest.fail("Sessiond return code")

        # Read trace with babeltrace and check for event count via number of line
        cmd = 'babeltrace {}'.format(trace_path)
        if should_trace:
            cp_process, cp_out, cp_err = runtime_tools.run(cmd)
            assert(utils.line_count(cp_out) == nb_events)
        else:
            with pytest.raises(subprocess.CalledProcessError):
                cp_process, cp_out, cp_err = runtime_tools.run(cmd)

@pytest.mark.parametrize("ust_label,tools_label,app_version,outcome", runtime_matrix_agent_interface)
def test_ust_java_agent_interface(tmpdir, ust_label, tools_label, app_version, outcome):
    """
    Use the agent coming from ust_label, but run app under tools_version runtime using ust agent.
    """

    nb_iter = 100
    nb_events = 3 * nb_iter

    # Prepare environment
    ust = ProjectFactory.get_precook(ust_label)
    tools = ProjectFactory.get_precook(tools_label)
    babeltrace = ProjectFactory.get_precook(Settings.default_babeltrace)

    tools_runtime_path = os.path.join(str(tmpdir), "tools")
    ust_runtime_path = os.path.join(str(tmpdir), "ust")
    app_path = os.path.join(str(tmpdir), "app")

    with Run.get_runtime(ust_runtime_path) as runtime_app, Run.get_runtime(tools_runtime_path) as runtime_tools:
        runtime_tools.add_project(tools)
        runtime_tools.add_project(babeltrace)

        runtime_app.add_project(ust)
        runtime_app.lttng_home = runtime_tools.lttng_home

        trace_path = os.path.join(runtime_tools.lttng_home, 'trace')

        # Make application using the ust runtime
        shutil.copytree(version_to_app[app_version], app_path)
        runtime_app.run("javac App.java", cwd=app_path)

        # Start lttng-sessiond
        sessiond = utils.sessiond_spawn(runtime_tools)

        # Create session using mi to get path and session name
        runtime_tools.run('lttng create trace --output={}'.format(trace_path))

        runtime_tools.run('lttng enable-event -j jello')
        runtime_tools.run('lttng start')

        # Steal the classpath from ust project
        ust_classpath = ust.special_env_variables['CLASSPATH']

        # Run application with tools runtime
        cmd = 'java App {}'.format(nb_iter)
        runtime_tools.run(cmd, cwd=app_path, classpath=ust_classpath)

        # Stop tracing
        runtime_tools.run('lttng stop')
        runtime_tools.run('lttng destroy -a')
        cp = runtime_tools.subprocess_terminate(sessiond)
        if cp.returncode != 0:
            pytest.fail("Sessiond return code")

        # Read trace with babeltrace and check for event count via number of line
        cmd = 'babeltrace {}'.format(trace_path)
        if outcome == "Success":
            assert utils.file_contains(runtime_tools.get_subprocess_stderr_path(sessiond),["New registration for pid"])
            cp_process, cp_out, cp_err = runtime_tools.run(cmd)
            assert utils.line_count(cp_out) == nb_events
        else:
            if outcome == "Unsupported protocol":
                assert not(utils.file_contains(runtime_tools.get_subprocess_stderr_path(sessiond),["New registration for pid"]))
                cp_process, cp_out, cp_err = runtime_tools.run(cmd)
                assert utils.line_count(cp_out) == 0
