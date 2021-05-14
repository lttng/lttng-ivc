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

NOTE: tracing between 2.7 and 2.8 should work but a problem with
_ustctl_basic_type prevent event registration. Hence consider in further test
that the event registration is expected to fail.

+------------------------------------------------------------------------------+
|              LTTng UST control protocol compatibility matrix                 |
|   (between applications and tools linked on LTTng UST and liblttng-ust-ctl)  |
+--------------------------+------------+------------+------------+------------+------------+------------+------------------+
| LTTng UST / LTTng Tools  | 2.7 (6.0)  | 2.8 (6.1)  | 2.9 (7.1)  | 2.10 (7.2) | 2.11 (8.0) | 2.12 (8.1) | 2.13 (9.0) (8.1) |
+--------------------------+------------+------------+------------+------------+------------+------------+------------------+
| 2.7 (6.0)                | FC         | BC         | TU         | TU         | TU         | TU         | TU               |
| 2.8 (6.1)                | BC         | FC         | TU         | TU         | TU         | TU         | TU               |
| 2.9 (7.1)                | TU         | TU         | FC         | BC         | TU         | TU         | TU               |
| 2.10 (7.2)               | TU         | TU         | BC         | FC         | TU         | TU         | TU               |
| 2.11 (8.0)               | TU         | TU         | TU         | TU         | FC         | BC         | BC               |
| 2.12 (8.1)               | TU         | TU         | TU         | TU         | BC         | FC         | BC               |
| 2.13 (9.0) (8.1)         | TU         | TU         | TU         | TU         | TU         | TU         | FC               |
+--------------------------+------------+------------+------------+------------+------------+------------+------------------+

LTTng-ust 2.13 introduced the notion of
LTTNG_UST_ABI_MAJOR_VERSION_OLDEST_COMPATIBLE see lttng-ust commit:
6a359b8a4006. Hence a 2.12 ust app should be able to communicate with a
lttng-tools 2.13 daemon but not the other way around

Version number of this API is defined in include/lttng/ust-abi.h of lttng-ust project

"""

"""
First tuple member: lttng-ust label
Second tuple member: lttng-tool label
Third tuple member: expected scenario
"""

event_registration_error = "Error: UST app recv reg unsupported version"

test_matrix_tracing_available = [
    ("lttng-ust-2.7", "lttng-tools-2.7", "Success"),
    ("lttng-ust-2.7", "lttng-tools-2.8", "Unsupported version"),
    ("lttng-ust-2.7", "lttng-tools-2.9", "Unsupported"),
    ("lttng-ust-2.7", "lttng-tools-2.10", "Unsupported"),
    ("lttng-ust-2.7", "lttng-tools-2.11", "Unsupported"),
    ("lttng-ust-2.7", "lttng-tools-2.12", "Unsupported"),
    ("lttng-ust-2.7", "lttng-tools-2.13", "Unsupported"),
    ("lttng-ust-2.8", "lttng-tools-2.7", "Unsupported version"),
    ("lttng-ust-2.8", "lttng-tools-2.8", "Success"),
    ("lttng-ust-2.8", "lttng-tools-2.9", "Unsupported"),
    ("lttng-ust-2.8", "lttng-tools-2.10", "Unsupported"),
    ("lttng-ust-2.8", "lttng-tools-2.11", "Unsupported"),
    ("lttng-ust-2.8", "lttng-tools-2.12", "Unsupported"),
    ("lttng-ust-2.8", "lttng-tools-2.13", "Unsupported"),
    ("lttng-ust-2.9", "lttng-tools-2.7", "Unsupported"),
    ("lttng-ust-2.9", "lttng-tools-2.8", "Unsupported"),
    ("lttng-ust-2.9", "lttng-tools-2.9", "Success"),
    ("lttng-ust-2.9", "lttng-tools-2.10", "Success"),
    ("lttng-ust-2.9", "lttng-tools-2.11", "Unsupported"),
    ("lttng-ust-2.9", "lttng-tools-2.12", "Unsupported"),
    ("lttng-ust-2.9", "lttng-tools-2.13", "Unsupported"),
    ("lttng-ust-2.10", "lttng-tools-2.7", "Unsupported"),
    ("lttng-ust-2.10", "lttng-tools-2.8", "Unsupported"),
    ("lttng-ust-2.10", "lttng-tools-2.9", "Success"),
    ("lttng-ust-2.10", "lttng-tools-2.10", "Success"),
    ("lttng-ust-2.10", "lttng-tools-2.11", "Unsupported"),
    ("lttng-ust-2.10", "lttng-tools-2.12", "Unsupported"),
    ("lttng-ust-2.10", "lttng-tools-2.13", "Unsupported"),
    ("lttng-ust-2.11", "lttng-tools-2.7", "Unsupported"),
    ("lttng-ust-2.11", "lttng-tools-2.8", "Unsupported"),
    ("lttng-ust-2.11", "lttng-tools-2.9", "Unsupported"),
    ("lttng-ust-2.11", "lttng-tools-2.10", "Unsupported"),
    ("lttng-ust-2.11", "lttng-tools-2.11", "Success"),
    ("lttng-ust-2.11", "lttng-tools-2.12", "Success"),
    ("lttng-ust-2.11", "lttng-tools-2.13", "Success"),
    ("lttng-ust-2.12", "lttng-tools-2.7", "Unsupported"),
    ("lttng-ust-2.12", "lttng-tools-2.8", "Unsupported"),
    ("lttng-ust-2.12", "lttng-tools-2.9", "Unsupported"),
    ("lttng-ust-2.12", "lttng-tools-2.10", "Unsupported"),
    ("lttng-ust-2.12", "lttng-tools-2.11", "Success"),
    ("lttng-ust-2.12", "lttng-tools-2.12", "Success"),
    ("lttng-ust-2.12", "lttng-tools-2.13", "Success"),
    ("lttng-ust-2.13", "lttng-tools-2.7", "Unsupported"),
    ("lttng-ust-2.13", "lttng-tools-2.8", "Unsupported"),
    ("lttng-ust-2.13", "lttng-tools-2.9", "Unsupported"),
    ("lttng-ust-2.13", "lttng-tools-2.10", "Unsupported"),
    ("lttng-ust-2.13", "lttng-tools-2.11", "Unsupported"),
    ("lttng-ust-2.13", "lttng-tools-2.12", "Unsupported"),
    ("lttng-ust-2.13", "lttng-tools-2.13", "Success"),
]


"""
Statedump are supported starting at lttng-ust >= 2.9.
No need to test for prior lttng-ust given that there is also a bump leading to
loss of tracing for application running under lttng-ust < 2.9.

The ust abi from 2.10 to 2.11 limits the number of tuple to be tested here due
to registration handshake. For now tools 2.11 can only be tested against
lttng-ust >= 2.11 (8.0 ust abi).
"""
test_matrix_regen_statedump = [
    ("lttng-ust-2.9", "lttng-tools-2.9", True),
    ("lttng-ust-2.9", "lttng-tools-2.10", True),
    ("lttng-ust-2.10", "lttng-tools-2.9", True),
    ("lttng-ust-2.10", "lttng-tools-2.10", True),
    ("lttng-ust-2.11", "lttng-tools-2.11", True),
    ("lttng-ust-2.11", "lttng-tools-2.12", True),
    ("lttng-ust-2.12", "lttng-tools-2.11", True),
    ("lttng-ust-2.12", "lttng-tools-2.12", True),
    ("lttng-ust-2.12", "lttng-tools-2.13", True),
    ("lttng-ust-2.13", "lttng-tools-2.13", True),
]

"""
The ust abi from 2.10 to 2.11 limits the number of tuple to be tested here due
to registration handshake. For now tools 2.11 can only be tested against
lttng-ust >= 2.11 (8.0 ust abi).
"""
test_matrix_starglobing_enabler = [
    ("lttng-ust-2.9", "lttng-tools-2.9", "Unsupported by tools"),
    ("lttng-ust-2.9", "lttng-tools-2.10", "Unsupported by ust"),
    ("lttng-ust-2.10", "lttng-tools-2.9", "Unsupported by tools"),
    ("lttng-ust-2.10", "lttng-tools-2.10", "Supported"),
    ("lttng-ust-2.11", "lttng-tools-2.11", "Supported"),
    ("lttng-ust-2.11", "lttng-tools-2.12", "Supported"),
    ("lttng-ust-2.12", "lttng-tools-2.11", "Supported"),
    ("lttng-ust-2.12", "lttng-tools-2.12", "Supported"),
    ("lttng-ust-2.12", "lttng-tools-2.13", "Supported"),
    ("lttng-ust-2.13", "lttng-tools-2.13", "Supported"),
]

runtime_matrix_tracing_available = Settings.generate_runtime_test_matrix(
    test_matrix_tracing_available, [0, 1]
)
runtime_matrix_regen_statedump = Settings.generate_runtime_test_matrix(
    test_matrix_regen_statedump, [0, 1]
)
runtime_matrix_starglobing_enabler = Settings.generate_runtime_test_matrix(
    test_matrix_starglobing_enabler, [0, 1]
)


@pytest.mark.parametrize(
    "ust_label,tools_label,outcome", runtime_matrix_tracing_available
)
def test_ust_app_tracing_available(tmpdir, ust_label, tools_label, outcome):

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
        runtime_app.run("ldd ./app", cwd=app_path)
        cmd = "./app {}".format(nb_events)
        runtime_app.run(cmd, cwd=app_path)

        # Stop tracing
        runtime_tools.run("lttng stop")
        runtime_tools.run("lttng destroy -a")
        cp = runtime_tools.subprocess_terminate(sessiond)
        if cp.returncode != 0:
            pytest.fail("Sessiond return code")

        cmd = "babeltrace {}".format(trace_path)
        if outcome == "Success":
            cp_process, cp_out, cp_err = runtime_tools.run(cmd)
            assert utils.line_count(cp_out) == nb_events
        else:
            with pytest.raises(subprocess.CalledProcessError):
                cp_process, cp_out, cp_err = runtime_tools.run(cmd)
            if outcome == "Unsupported version":
                assert utils.file_contains(
                    runtime_tools.get_subprocess_stderr_path(sessiond),
                    [event_registration_error],
                )


@pytest.mark.parametrize(
    "ust_label,tools_label, success", runtime_matrix_regen_statedump
)
def test_ust_app_regen_statedump(tmpdir, ust_label, tools_label, success):
    nb_events = 100

    if success:
        expected_events = 4
    else:
        expected_events = 2

    ust = ProjectFactory.get_precook(ust_label)
    tools = ProjectFactory.get_precook(tools_label)
    babeltrace = ProjectFactory.get_precook(Settings.default_babeltrace)

    tools_runtime_path = os.path.join(str(tmpdir), "tools")
    ust_runtime_path = os.path.join(str(tmpdir), "ust")
    app_path = os.path.join(str(tmpdir), "app")

    app_sync_start = os.path.join(app_path, "sync_start")
    app_sync_end = os.path.join(app_path, "sync_end")

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

        runtime_tools.run(
            "lttng enable-event -u lttng_ust_statedump:start,lttng_ust_statedump:end"
        )
        runtime_tools.run("lttng start")

        # Run application
        cmd = "./app {} 0 {} {}".format(nb_events, app_sync_start, app_sync_end)
        runtime_app.spawn_subprocess(cmd, cwd=app_path)

        utils.wait_for_file(app_sync_start)

        if not success:
            with pytest.raises(subprocess.CalledProcessError):
                runtime_tools.run("lttng regenerate statedump")
        else:
            runtime_tools.run("lttng regenerate statedump")

        utils.create_empty_file(app_sync_end)

        # Stop tracing
        runtime_tools.run("lttng stop")
        runtime_tools.run("lttng destroy -a")
        cp = runtime_tools.subprocess_terminate(sessiond)
        if cp.returncode != 0:
            pytest.fail("Sessiond return code")

        # Read trace with babeltrace and check for event count via number of line
        cmd = "babeltrace {}".format(trace_path)
        cp_process, cp_out, cp_err = runtime_tools.run(cmd)
        assert utils.line_count(cp_out) == expected_events


@pytest.mark.parametrize(
    "ust_label,tools_label, scenario", runtime_matrix_starglobing_enabler
)
def test_ust_app_starglobing_enabler(tmpdir, ust_label, tools_label, scenario):

    nb_events = 100

    if scenario == "Unsupported by ust":
        expected_events = 0
    else:
        expected_events = nb_events

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

        # If unsupported by tools simply finish early
        if scenario == "Unsupported by tools":
            with pytest.raises(subprocess.CalledProcessError):
                runtime_tools.run('lttng enable-event -u "tp:*te*"')

            # TODO move this to internal runtime...
            cp = runtime_tools.subprocess_terminate(sessiond)
            if cp.returncode != 0:
                pytest.fail("Sessiond return code")
            return
        else:
            runtime_tools.run('lttng enable-event -u "tp:*te*"')

        runtime_tools.run("lttng start")

        # Run application
        cmd = "./app {}".format(nb_events)
        runtime_app.run(cmd, cwd=app_path)

        # Stop tracing
        runtime_tools.run("lttng stop")
        runtime_tools.run("lttng destroy -a")
        cp = runtime_tools.subprocess_terminate(sessiond)
        if cp.returncode != 0:
            pytest.fail("Sessiond return code")

            # Read trace with babeltrace and check for event count via number of line
        cmd = "babeltrace {}".format(trace_path)
        cp_process, cp_out, cp_err = runtime_tools.run(cmd)
        assert utils.line_count(cp_out) == expected_events
