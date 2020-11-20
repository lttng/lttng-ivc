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
EU: Event unavailable for tracing
SO: lttng-ust .so unavailable

+-----------------------------------------+-----+------+------+-------+
|                      LTTng UST tracepoint API/ABI:                  |
|                    Probe provider vs LTTng UST library              |
+-----------------------------------------+-----+------+------+-------+-------+-----+-----+
| Probe Provider / LTTng UST              | 2.7 |  2.8 |  2.9 |  2.10 |  2.11 | 2.12| 2.13|
+-----------------------------------------+-----+------+------+-------+-------+-----+-----+
| 2.7                                     | FC  | BC   | BC   | BC    | BC    | BC  | SO  |
| 2.8                                     | EU  | FC   | BC   | BC    | BC    | BC  | SO  |
| 2.9                                     | EU  | EU   | FC   | BC    | BC    | BC  | SO  |
| 2.10                                    | EU  | EU   | EU   | FC    | BC    | BC  | SO  |
| 2.11                                    | EU  | EU   | EU   | EU    | FC    | BC  | SO  |
| 2.12                                    | EU  | EU   | EU   | EU    | EU    | FC  | SO  |
| 2.13                                    | SO  | SO   | SO   | SO    | SO    | SO  | FC  |
+-----------------------------------------+-----+------+------+-------+-------+-----+-----+

Using tracepoint.h as a reference for change between version.

Compile application with version under test (Probe Provider) tracepoints but do not link with provider.
Build provider with version under test (Probe Provider)
Launch application with provider using ld_preload.
Validate that events are registered and present in trace.
"""

"""
First tuple member: application lttng-ust version
Second tuple member: reference (lttng-ust,lttng-tools) version
Third tuple member: expected scenario
"""

"""
We use lttng-tools instead of lttng-ust as second tuple since each
lttng-tools is locked with the corresponding lttng-ust we want to test given
that we use pre_cooked one.
"""

fail_provider = "fail_on_provider"
# The .so of lttng-ust was bumped for 2.13. hence application linked against
# the previous .so cannot work in "fresh" upgraded" runtime without it.
fail_so_0 = "fail_on_ust_so_0"
fail_so_1 = "fail_on_ust_so_1"
success = "success"
tracing_unavailable = "tracing_unavailable"

fail_so_errors = {
        fail_so_0 : "error while loading shared libraries: liblttng-ust.so.0: cannot open shared object file",
        fail_so_1 : "error while loading shared libraries: liblttng-ust.so.1: cannot open shared object file"
    }

test_matrix_enum = [
    ("lttng-ust-2.7", "lttng-tools-2.7", fail_provider, 0),
    ("lttng-ust-2.7", "lttng-tools-2.8", fail_provider, 0),
    ("lttng-ust-2.7", "lttng-tools-2.9", fail_provider, 0),
    ("lttng-ust-2.7", "lttng-tools-2.10", fail_provider, 0),
    ("lttng-ust-2.7", "lttng-tools-2.11", fail_provider, 0),
    ("lttng-ust-2.7", "lttng-tools-2.12", fail_provider, 0),
    ("lttng-ust-2.7", "lttng-tools-2.13", fail_provider, 0),
    ("lttng-ust-2.8", "lttng-tools-2.7", success, 100),
    ("lttng-ust-2.8", "lttng-tools-2.8", success, 200),
    ("lttng-ust-2.8", "lttng-tools-2.9", success, 200),
    ("lttng-ust-2.8", "lttng-tools-2.10", success, 200),
    ("lttng-ust-2.8", "lttng-tools-2.11", success, 200),
    ("lttng-ust-2.8", "lttng-tools-2.12", success, 200),
    ("lttng-ust-2.8", "lttng-tools-2.13", fail_so_0, 200),
    ("lttng-ust-2.9", "lttng-tools-2.7", success, 100),
    ("lttng-ust-2.9", "lttng-tools-2.8", success, 200),
    ("lttng-ust-2.9", "lttng-tools-2.9", success, 200),
    ("lttng-ust-2.9", "lttng-tools-2.10", success, 200),
    ("lttng-ust-2.9", "lttng-tools-2.11", success, 200),
    ("lttng-ust-2.9", "lttng-tools-2.12", success, 200),
    ("lttng-ust-2.9", "lttng-tools-2.13", fail_so_0, 0),
    ("lttng-ust-2.10", "lttng-tools-2.7", success, 100),
    ("lttng-ust-2.10", "lttng-tools-2.8", success, 200),
    ("lttng-ust-2.10", "lttng-tools-2.9", success, 200),
    ("lttng-ust-2.10", "lttng-tools-2.10", success, 200),
    ("lttng-ust-2.10", "lttng-tools-2.11", success, 200),
    ("lttng-ust-2.10", "lttng-tools-2.11", success, 200),
    ("lttng-ust-2.10", "lttng-tools-2.12", success, 200),
    ("lttng-ust-2.10", "lttng-tools-2.13", fail_so_0, 0),
    ("lttng-ust-2.11", "lttng-tools-2.7", success, 100),
    ("lttng-ust-2.11", "lttng-tools-2.8", success, 200),
    ("lttng-ust-2.11", "lttng-tools-2.9", success, 200),
    ("lttng-ust-2.11", "lttng-tools-2.10", success, 200),
    ("lttng-ust-2.11", "lttng-tools-2.11", success, 200),
    ("lttng-ust-2.11", "lttng-tools-2.12", success, 200),
    ("lttng-ust-2.11", "lttng-tools-2.13", fail_so_0, 0),
    ("lttng-ust-2.12", "lttng-tools-2.7", success, 100),
    ("lttng-ust-2.12", "lttng-tools-2.8", success, 200),
    ("lttng-ust-2.12", "lttng-tools-2.9", success, 200),
    ("lttng-ust-2.12", "lttng-tools-2.10", success, 200),
    ("lttng-ust-2.12", "lttng-tools-2.11", success, 200),
    ("lttng-ust-2.12", "lttng-tools-2.12", success, 200),
    ("lttng-ust-2.12", "lttng-tools-2.13", fail_so_0, 0),
    ("lttng-ust-2.13", "lttng-tools-2.7", fail_so_1, 0),
    ("lttng-ust-2.13", "lttng-tools-2.8", fail_so_1, 0),
    ("lttng-ust-2.13", "lttng-tools-2.9", fail_so_1, 0),
    ("lttng-ust-2.13", "lttng-tools-2.10", fail_so_1, 0),
    ("lttng-ust-2.13", "lttng-tools-2.11", fail_so_1, 0),
    ("lttng-ust-2.13", "lttng-tools-2.12", fail_so_1, 0),
    ("lttng-ust-2.13", "lttng-tools-2.13", success, 200),

]

test_matrix_base = [
    ("lttng-ust-2.7", "lttng-tools-2.7", success),
    ("lttng-ust-2.7", "lttng-tools-2.8", success),
    ("lttng-ust-2.7", "lttng-tools-2.9", success),
    ("lttng-ust-2.7", "lttng-tools-2.10", success),
    ("lttng-ust-2.7", "lttng-tools-2.11", success),
    ("lttng-ust-2.7", "lttng-tools-2.12", success),
    ("lttng-ust-2.7", "lttng-tools-2.13", fail_so_0),
    ("lttng-ust-2.8", "lttng-tools-2.7", success),
    ("lttng-ust-2.8", "lttng-tools-2.8", success),
    ("lttng-ust-2.8", "lttng-tools-2.9", success),
    ("lttng-ust-2.8", "lttng-tools-2.10", success),
    ("lttng-ust-2.8", "lttng-tools-2.11", success),
    ("lttng-ust-2.8", "lttng-tools-2.12", success),
    ("lttng-ust-2.8", "lttng-tools-2.13", fail_so_0),
    ("lttng-ust-2.9", "lttng-tools-2.7", success),
    ("lttng-ust-2.9", "lttng-tools-2.8", success),
    ("lttng-ust-2.9", "lttng-tools-2.9", success),
    ("lttng-ust-2.9", "lttng-tools-2.10", success),
    ("lttng-ust-2.9", "lttng-tools-2.11", success),
    ("lttng-ust-2.9", "lttng-tools-2.12", success),
    ("lttng-ust-2.9", "lttng-tools-2.13", fail_so_0),
    ("lttng-ust-2.10", "lttng-tools-2.7", success),
    ("lttng-ust-2.10", "lttng-tools-2.8", success),
    ("lttng-ust-2.10", "lttng-tools-2.9", success),
    ("lttng-ust-2.10", "lttng-tools-2.10", success),
    ("lttng-ust-2.10", "lttng-tools-2.11", success),
    ("lttng-ust-2.10", "lttng-tools-2.12", success),
    ("lttng-ust-2.10", "lttng-tools-2.13", fail_so_0),
    ("lttng-ust-2.11", "lttng-tools-2.7", success),
    ("lttng-ust-2.11", "lttng-tools-2.8", success),
    ("lttng-ust-2.11", "lttng-tools-2.9", success),
    ("lttng-ust-2.11", "lttng-tools-2.10", success),
    ("lttng-ust-2.11", "lttng-tools-2.11", success),
    ("lttng-ust-2.11", "lttng-tools-2.12", success),
    ("lttng-ust-2.11", "lttng-tools-2.13", fail_so_0),
    ("lttng-ust-2.12", "lttng-tools-2.7", success),
    ("lttng-ust-2.12", "lttng-tools-2.8", success),
    ("lttng-ust-2.12", "lttng-tools-2.9", success),
    ("lttng-ust-2.12", "lttng-tools-2.10", success),
    ("lttng-ust-2.12", "lttng-tools-2.11", success),
    ("lttng-ust-2.12", "lttng-tools-2.12", success),
    ("lttng-ust-2.12", "lttng-tools-2.13", fail_so_0),
    ("lttng-ust-2.13", "lttng-tools-2.7", fail_so_1),
    ("lttng-ust-2.13", "lttng-tools-2.8", fail_so_1),
    ("lttng-ust-2.13", "lttng-tools-2.9", fail_so_1),
    ("lttng-ust-2.13", "lttng-tools-2.10", fail_so_1),
    ("lttng-ust-2.13", "lttng-tools-2.11", fail_so_1),
    ("lttng-ust-2.13", "lttng-tools-2.12", fail_so_1),
    ("lttng-ust-2.13", "lttng-tools-2.13", success),

]

runtime_matrix_enum = Settings.generate_runtime_test_matrix(test_matrix_enum, [0, 1])
runtime_matrix_base = Settings.generate_runtime_test_matrix(test_matrix_base, [0, 1])


@pytest.mark.parametrize(
    "ust_label,tools_label,scenario, expected_event", runtime_matrix_enum
)
def test_ust_tracepoint_probe_abi_api_vs_ust_enum(
    tmpdir, ust_label, tools_label, scenario, expected_event
):

    nb_loop = 100
    nb_expected_events = expected_event

    # Prepare environment
    ust = ProjectFactory.get_precook(ust_label)
    tools = ProjectFactory.get_precook(tools_label)
    babeltrace = ProjectFactory.get_precook(Settings.default_babeltrace)

    tools_runtime_path = os.path.join(str(tmpdir), "tools")
    ust_runtime_path = os.path.join(str(tmpdir), "ust")
    app_path = os.path.join(str(tmpdir), "app")

    with Run.get_runtime(ust_runtime_path) as runtime_ust, Run.get_runtime(
        tools_runtime_path
    ) as runtime_tools:
        runtime_tools.add_project(tools)
        runtime_tools.add_project(babeltrace)

        runtime_ust.add_project(ust)
        runtime_ust.lttng_home = runtime_tools.lttng_home

        trace_path = os.path.join(runtime_tools.lttng_home, "trace")

        # Make application using the ust runtime
        shutil.copytree(Settings.apps_preload_provider_folder, app_path)

        # Make the probe using the ust runtime
        if scenario == fail_provider:
            with pytest.raises(subprocess.CalledProcessError):
                runtime_ust.run("make provider-enum", cwd=app_path)
            return
        else:
            runtime_ust.run("make provider-enum", cwd=app_path)

        # Make the application using the ust runtime
        runtime_ust.run("make app-enum", cwd=app_path)

        # Start lttng-sessiond.
        sessiond = utils.sessiond_spawn(runtime_tools)
        runtime_tools.run("lttng create trace --output={}".format(trace_path))
        runtime_tools.run("lttng enable-event -u tp:tptest,tp:tpenum")
        runtime_tools.run("lttng start")

        # Run application under the tools runtime.
        cmd = "./app-enum {}".format(nb_loop)
        if scenario in fail_so_errors:
            cp_process, cp_out, cp_err = runtime_tools.run(cmd, cwd=app_path, ld_preload="./libtp-enum.so", check_return=False)
            assert cp_process.returncode == 127
            assert utils.file_contains(
                    cp_err,
                    [fail_so_errors[scenario]]
                    )

            # Nothing else to check.
            return
        else:
            runtime_tools.run(cmd, cwd=app_path, ld_preload="./libtp-enum.so")


        # Stop tracing
        runtime_tools.run("lttng stop")
        runtime_tools.run("lttng destroy -a")
        runtime_tools.subprocess_terminate(sessiond)

        # Read trace with babeltrace and check for event count via number of line
        cmd = "babeltrace {}".format(trace_path)
        cp_process, cp_out, cp_err = runtime_tools.run(cmd)
        assert utils.line_count(cp_out) == nb_expected_events


@pytest.mark.parametrize("ust_label,tools_label,scenario", runtime_matrix_base)
def test_ust_tracepoint_probe_abi_api_vs_ust_base(
    tmpdir, ust_label, tools_label, scenario
):

    nb_loop = 100

    if scenario != tracing_unavailable:
        nb_expected_events = 200
    else:
        nb_expected_events = 0


    # Prepare environment
    ust = ProjectFactory.get_precook(ust_label)
    tools = ProjectFactory.get_precook(tools_label)
    babeltrace = ProjectFactory.get_precook(Settings.default_babeltrace)

    tools_runtime_path = os.path.join(str(tmpdir), "tools")
    ust_runtime_path = os.path.join(str(tmpdir), "ust")
    app_path = os.path.join(str(tmpdir), "app")

    with Run.get_runtime(ust_runtime_path) as runtime_ust, Run.get_runtime(
        tools_runtime_path
    ) as runtime_tools:
        runtime_tools.add_project(tools)
        runtime_tools.add_project(babeltrace)

        runtime_ust.add_project(ust)
        runtime_ust.lttng_home = runtime_tools.lttng_home

        trace_path = os.path.join(runtime_tools.lttng_home, "trace")

        # Make application using the ust runtime
        shutil.copytree(Settings.apps_preload_provider_folder, app_path)

        # Make the probe in the ust runtime
        runtime_ust.run("make provider", cwd=app_path)

        # Use the ust env to test tracepoint instrumentation
        runtime_ust.run("make app", cwd=app_path)

        # Start lttng-sessiond
        sessiond = utils.sessiond_spawn(runtime_tools)

        # Create session using mi to get path and session name
        runtime_tools.run("lttng create trace --output={}".format(trace_path))

        runtime_tools.run("lttng enable-event -u tp:tptest,tp:tpenum")
        runtime_tools.run("lttng start")

        # Run in the tools runtime application
        cmd = "./app {}".format(nb_loop)
        if scenario in fail_so_errors:
            cp_process, cp_out, cp_err = runtime_tools.run(cmd, cwd=app_path, ld_preload="./libtp.so", check_return=False)
            assert cp_process.returncode == 127
            assert utils.file_contains(
                    cp_err,
                    [fail_so_errors[scenario]]
                    )

            # Nothing else to check.
            return
        else:
            runtime_tools.run(cmd, cwd=app_path, ld_preload="./libtp.so")

        # Stop tracing
        runtime_tools.run("lttng stop")
        runtime_tools.run("lttng destroy -a")
        runtime_tools.subprocess_terminate(sessiond)

        # Read trace with babeltrace and check for event count via number of line
        cmd = "babeltrace {}".format(trace_path)
        cp_process, cp_out, cp_err = runtime_tools.run(cmd)
        assert utils.line_count(cp_out) == nb_expected_events
