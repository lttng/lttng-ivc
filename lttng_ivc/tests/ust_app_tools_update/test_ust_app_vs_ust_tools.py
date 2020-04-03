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

"""

"""
First tuple member: lttng-ust label
Second tuple member: lttng-tool label
Third tuple member: expected scenario
"""

event_registration_error = "Error: UST app recv reg unsupported version"

test_matrix_base_app_tracing_available = [
    ("lttng-ust-2.7", "lttng-tools-2.7", True),
    ("lttng-ust-2.7", "lttng-tools-2.8", True),
    ("lttng-ust-2.7", "lttng-tools-2.9", True),
    ("lttng-ust-2.7", "lttng-tools-2.10", True),
    ("lttng-ust-2.7", "lttng-tools-2.11", True),
    ("lttng-ust-2.7", "lttng-tools-2.12", True),
    ("lttng-ust-2.8", "lttng-tools-2.7", True),
    ("lttng-ust-2.8", "lttng-tools-2.8", True),
    ("lttng-ust-2.8", "lttng-tools-2.9", True),
    ("lttng-ust-2.8", "lttng-tools-2.10", True),
    ("lttng-ust-2.8", "lttng-tools-2.11", True),
    ("lttng-ust-2.8", "lttng-tools-2.12", True),
    ("lttng-ust-2.9", "lttng-tools-2.7", True),
    ("lttng-ust-2.9", "lttng-tools-2.8", True),
    ("lttng-ust-2.9", "lttng-tools-2.9", True),
    ("lttng-ust-2.9", "lttng-tools-2.10", True),
    ("lttng-ust-2.9", "lttng-tools-2.11", True),
    ("lttng-ust-2.9", "lttng-tools-2.12", True),
    ("lttng-ust-2.10", "lttng-tools-2.7", True),
    ("lttng-ust-2.10", "lttng-tools-2.8", True),
    ("lttng-ust-2.10", "lttng-tools-2.9", True),
    ("lttng-ust-2.10", "lttng-tools-2.10", True),
    ("lttng-ust-2.10", "lttng-tools-2.11", True),
    ("lttng-ust-2.10", "lttng-tools-2.12", True),
    ("lttng-ust-2.11", "lttng-tools-2.7", True),
    ("lttng-ust-2.11", "lttng-tools-2.8", True),
    ("lttng-ust-2.11", "lttng-tools-2.9", True),
    ("lttng-ust-2.11", "lttng-tools-2.10", True),
    ("lttng-ust-2.11", "lttng-tools-2.11", True),
    ("lttng-ust-2.11", "lttng-tools-2.12", True),
    ("lttng-ust-2.12", "lttng-tools-2.7", True),
    ("lttng-ust-2.12", "lttng-tools-2.8", True),
    ("lttng-ust-2.12", "lttng-tools-2.9", True),
    ("lttng-ust-2.12", "lttng-tools-2.10", True),
    ("lttng-ust-2.12", "lttng-tools-2.11", True),
    ("lttng-ust-2.12", "lttng-tools-2.12", True),
]

runtime_matrix_base_app_tracing_available = Settings.generate_runtime_test_matrix(
    test_matrix_base_app_tracing_available, [0, 1]
)


@pytest.mark.parametrize(
    "ust_label,tools_label,success", runtime_matrix_base_app_tracing_available
)
def test_ust_app_tools_update_tracing_available(
    tmpdir, ust_label, tools_label, success
):

    nb_events = 100

    # Prepare environment
    ust = ProjectFactory.get_precook(ust_label)
    tools = ProjectFactory.get_precook(tools_label)
    babeltrace = ProjectFactory.get_precook(Settings.default_babeltrace)

    tools_runtime_path = os.path.join(str(tmpdir), "tools")
    ust_runtime_path = os.path.join(str(tmpdir), "ust")
    app_path = os.path.join(str(tmpdir), "app")

    with Run.get_runtime(ust_runtime_path) as runtime_app, Run.get_runtime(
        tools_runtime_path
    ) as runtime_tools:
        runtime_tools.add_project(tools)
        runtime_tools.add_project(babeltrace)

        runtime_app.add_project(ust)
        runtime_app.lttng_home = runtime_tools.lttng_home

        trace_path = os.path.join(runtime_tools.lttng_home, "trace")

        # Make application using the ust runtime
        shutil.copytree(Settings.apps_gen_events_folder, app_path)
        runtime_app.run("make V=1", cwd=app_path)

        # Start lttng-sessiond
        sessiond = utils.sessiond_spawn(runtime_tools)

        # Create session using mi to get path and session name
        runtime_tools.run("lttng create trace --output={}".format(trace_path))

        runtime_tools.run("lttng enable-event -u tp:tptest")
        runtime_tools.run("lttng start")

        # Run application
        cmd = "./app {}".format(nb_events)
        runtime_tools.run(cmd, cwd=app_path)

        runtime_tools.run("objdump -p ./app", cwd=app_path)
        runtime_app.run("objdump -p ./app", cwd=app_path)

        # Stop tracing
        runtime_tools.run("lttng stop")
        runtime_tools.run("lttng destroy -a")
        cp = runtime_tools.subprocess_terminate(sessiond)
        if cp.returncode != 0:
            pytest.fail("Sessiond return code")

        cmd = "babeltrace {}".format(trace_path)
        if success:
            cp_process, cp_out, cp_err = runtime_tools.run(cmd)
            assert utils.line_count(cp_out) == nb_events
        else:
            with pytest.raises(subprocess.CalledProcessError):
                cp_process, cp_out, cp_err = runtime_tools.run(cmd)
