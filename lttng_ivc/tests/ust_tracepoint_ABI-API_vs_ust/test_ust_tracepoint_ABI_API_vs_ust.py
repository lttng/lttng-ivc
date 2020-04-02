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

+-----------------------------------------+-----+------+------+-------+
|             LTTng UST tracepoint instrumentation API/ABI:           |
|                    Application vs LTTng UST library                 |
+-----------------------------------------+-----+------+------+-------+-------+-------+
| Application Instrumentation / LTTng UST | 2.7 |  2.8 |  2.9 | 2.10  | 2.11  | 2.12  |
+-----------------------------------------+-----+------+------+-------+-------+-------+
| 2.7                                     | FC  | BC   | BC   | BC    | BC    | BC    |
| 2.8                                     | BC  | FC   | BC   | BC    | BC    | BC    |
| 2.9                                     | BC  | BC   | FC   | BC    | BC    | BC    |
| 2.10                                    | BC  | BC   | BC   | FC    | BC    | BC    |
| 2.11                                    | BC  | BC   | BC   | BC    | FC    | BC    |
| 2.12                                    | BC  | BC   | BC   | BC    | BC    | FC    |
+-----------------------------------------+-----+------+------+-------+-------+-------+

Using tracepoint.h as a reference for change between version.

Compile application with under test version (Application instrumentation) tracepoints but do not link with provider.
Build provider with reference version (ust)
Launch application with provider using ld_preload.
Validate that events are registered.

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
fail_app = "fail_on_app"
success = "success"

test_matrix_enum = [
        ("lttng-ust-2.7",  "lttng-tools-2.7",  fail_provider),
        ("lttng-ust-2.7",  "lttng-tools-2.8",  fail_app),
        ("lttng-ust-2.7",  "lttng-tools-2.9",  fail_app),
        ("lttng-ust-2.7",  "lttng-tools-2.10", fail_app),
        ("lttng-ust-2.7",  "lttng-tools-2.11", fail_app),
        ("lttng-ust-2.7",  "lttng-tools-2.12", fail_app),
        ("lttng-ust-2.8",  "lttng-tools-2.7",  fail_provider),
        ("lttng-ust-2.8",  "lttng-tools-2.8",  success),
        ("lttng-ust-2.8",  "lttng-tools-2.9",  success),
        ("lttng-ust-2.8",  "lttng-tools-2.10", success),
        ("lttng-ust-2.8",  "lttng-tools-2.11", success),
        ("lttng-ust-2.8",  "lttng-tools-2.12", success),
        ("lttng-ust-2.9",  "lttng-tools-2.7",  fail_provider),
        ("lttng-ust-2.9",  "lttng-tools-2.8",  success),
        ("lttng-ust-2.9",  "lttng-tools-2.9",  success),
        ("lttng-ust-2.9",  "lttng-tools-2.10", success),
        ("lttng-ust-2.9",  "lttng-tools-2.11", success),
        ("lttng-ust-2.9",  "lttng-tools-2.12", success),
        ("lttng-ust-2.10", "lttng-tools-2.7",  fail_provider),
        ("lttng-ust-2.10", "lttng-tools-2.8",  success),
        ("lttng-ust-2.10", "lttng-tools-2.9",  success),
        ("lttng-ust-2.10", "lttng-tools-2.10", success),
        ("lttng-ust-2.10", "lttng-tools-2.11", success),
        ("lttng-ust-2.10", "lttng-tools-2.12", success),
        ("lttng-ust-2.11", "lttng-tools-2.7",  fail_provider),
        ("lttng-ust-2.11", "lttng-tools-2.8",  success),
        ("lttng-ust-2.11", "lttng-tools-2.9",  success),
        ("lttng-ust-2.11", "lttng-tools-2.10", success),
        ("lttng-ust-2.11", "lttng-tools-2.11", success),
        ("lttng-ust-2.11", "lttng-tools-2.12", success),
        ("lttng-ust-2.12", "lttng-tools-2.7",  fail_provider),
        ("lttng-ust-2.12", "lttng-tools-2.8",  success),
        ("lttng-ust-2.12", "lttng-tools-2.9",  success),
        ("lttng-ust-2.12", "lttng-tools-2.10", success),
        ("lttng-ust-2.12", "lttng-tools-2.11", success),
        ("lttng-ust-2.12", "lttng-tools-2.12", success),

]

test_matrix_base = [
        ("lttng-ust-2.7",  "lttng-tools-2.7",  success),
        ("lttng-ust-2.7",  "lttng-tools-2.8",  success),
        ("lttng-ust-2.7",  "lttng-tools-2.9",  success),
        ("lttng-ust-2.7",  "lttng-tools-2.10", success),
        ("lttng-ust-2.7",  "lttng-tools-2.11", success),
        ("lttng-ust-2.7",  "lttng-tools-2.12", success),
        ("lttng-ust-2.8",  "lttng-tools-2.7",  success),
        ("lttng-ust-2.8",  "lttng-tools-2.8",  success),
        ("lttng-ust-2.8",  "lttng-tools-2.9",  success),
        ("lttng-ust-2.8",  "lttng-tools-2.10", success),
        ("lttng-ust-2.8",  "lttng-tools-2.11", success),
        ("lttng-ust-2.8",  "lttng-tools-2.12", success),
        ("lttng-ust-2.9",  "lttng-tools-2.7",  success),
        ("lttng-ust-2.9",  "lttng-tools-2.8",  success),
        ("lttng-ust-2.9",  "lttng-tools-2.9",  success),
        ("lttng-ust-2.9",  "lttng-tools-2.10", success),
        ("lttng-ust-2.9",  "lttng-tools-2.11", success),
        ("lttng-ust-2.9",  "lttng-tools-2.12", success),
        ("lttng-ust-2.10", "lttng-tools-2.7",  success),
        ("lttng-ust-2.10", "lttng-tools-2.8",  success),
        ("lttng-ust-2.10", "lttng-tools-2.9",  success),
        ("lttng-ust-2.10", "lttng-tools-2.10", success),
        ("lttng-ust-2.10", "lttng-tools-2.11", success),
        ("lttng-ust-2.10", "lttng-tools-2.12", success),
        ("lttng-ust-2.11", "lttng-tools-2.7",  success),
        ("lttng-ust-2.11", "lttng-tools-2.8",  success),
        ("lttng-ust-2.11", "lttng-tools-2.9",  success),
        ("lttng-ust-2.11", "lttng-tools-2.10", success),
        ("lttng-ust-2.11", "lttng-tools-2.11", success),
        ("lttng-ust-2.11", "lttng-tools-2.12", success),
        ("lttng-ust-2.12", "lttng-tools-2.7",  success),
        ("lttng-ust-2.12", "lttng-tools-2.8",  success),
        ("lttng-ust-2.12", "lttng-tools-2.9",  success),
        ("lttng-ust-2.12", "lttng-tools-2.10", success),
        ("lttng-ust-2.12", "lttng-tools-2.11", success),
        ("lttng-ust-2.12", "lttng-tools-2.12", success),

]

runtime_matrix_enum = Settings.generate_runtime_test_matrix(test_matrix_enum, [0, 1])
runtime_matrix_base = Settings.generate_runtime_test_matrix(test_matrix_base, [0, 1])

@pytest.mark.parametrize("ust_label,tools_label,scenario", runtime_matrix_enum)
def test_ust_tracepoint_abi_api_vs_ust_enum(tmpdir, ust_label, tools_label, scenario):

    nb_loop = 100
    nb_expected_events = 200

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
        shutil.copytree(Settings.apps_preload_provider_folder, app_path)

        # Use the testing env to make the probe
        if scenario == fail_provider:
            with pytest.raises(subprocess.CalledProcessError):
                runtime_tools.run("make provider-enum", cwd=app_path)
            return
        else:
            runtime_tools.run("make provider-enum", cwd=app_path)

        # Use the ust env to test tracepoint instrumentation
        if scenario == fail_app:
            with pytest.raises(subprocess.CalledProcessError):
                runtime_app.run("make app-enum", cwd=app_path)
            return
        else:
            runtime_app.run("make app-enum", cwd=app_path)

        # Start lttng-sessiond
        sessiond = utils.sessiond_spawn(runtime_tools)

        # Create session using mi to get path and session name
        runtime_tools.run('lttng create trace --output={}'.format(trace_path))

        runtime_tools.run('lttng enable-event -u tp:tptest,tp:tpenum')
        runtime_tools.run('lttng start')

        # Run application
        cmd = './app-enum {}'.format(nb_loop)
        runtime_tools.run(cmd, cwd=app_path, ld_preload="./libtp-enum.so")

        # Stop tracing
        runtime_tools.run('lttng stop')
        runtime_tools.run('lttng destroy -a')
        runtime_tools.subprocess_terminate(sessiond)


        # Read trace with babeltrace and check for event count via number of line
        cmd = 'babeltrace {}'.format(trace_path)
        cp_process, cp_out, cp_err = runtime_tools.run(cmd)
        assert(utils.line_count(cp_out) == nb_expected_events)

@pytest.mark.parametrize("ust_label,tools_label,scenario", runtime_matrix_base)
def test_ust_tracepoint_abi_api_vs_ust_base(tmpdir, ust_label, tools_label, scenario):

    nb_loop = 100
    nb_expected_events = 200

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
        shutil.copytree(Settings.apps_preload_provider_folder, app_path)

        # Use the testing env to make the probe
        runtime_tools.run("make provider", cwd=app_path)

        # Use the ust env to test tracepoint instrumentation
        runtime_app.run("make app", cwd=app_path)

        # Start lttng-sessiond
        sessiond = utils.sessiond_spawn(runtime_tools)

        # Create session using mi to get path and session name
        runtime_tools.run('lttng create trace --output={}'.format(trace_path))

        runtime_tools.run('lttng enable-event -u tp:tptest,tp:tpenum')
        runtime_tools.run('lttng start')

        # Run application
        cmd = './app {}'.format(nb_loop)
        runtime_tools.run(cmd, cwd=app_path, ld_preload="./libtp.so")

        # Stop tracing
        runtime_tools.run('lttng stop')
        runtime_tools.run('lttng destroy -a')
        runtime_tools.subprocess_terminate(sessiond)


        # Read trace with babeltrace and check for event count via number of line
        cmd = 'babeltrace {}'.format(trace_path)
        cp_process, cp_out, cp_err = runtime_tools.run(cmd)
        assert(utils.line_count(cp_out) == nb_expected_events)
