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
import filecmp

import lttng_ivc.utils.ProjectFactory as ProjectFactory
import lttng_ivc.utils.utils as utils
import lttng_ivc.utils.runtime as Run
import lttng_ivc.settings as Settings


from lttng_ivc.utils.skip import must_be_root
from itertools import combinations
"""

FC: Fully Compatible
BC: Feature of the smallest version number will works.

+------------------------------------------------------------------------------+
|                   Babeltrace vs UST/Tools/Metadata                           |
+--------------------------+------------+------------+------------+------------+------------+
| Babeltrace / LTTng       | 2.7        | 2.8        | 2.9        | 2.10       | 2.11       |
+--------------------------+------------+------------+------------+------------+------------+
| 1.3                      | FC         | BC         | BC         | BC         | BC         |
| 1.4                      | FC         | FC         | FC         | FC         | FC         |
| 1.5                      | FC         | FC         | FC         | FC         | FC         |
+--------------------------+------------+------------+------------+------------+------------+

"""
test_matrix_base_ust = [
        ("babeltrace-1.3", "lttng-tools-2.7"),
        ("babeltrace-1.3", "lttng-tools-2.8"),
        ("babeltrace-1.3", "lttng-tools-2.9"),
        ("babeltrace-1.3", "lttng-tools-2.10"),
        ("babeltrace-1.3", "lttng-tools-2.11"),
        ("babeltrace-1.4", "lttng-tools-2.7"),
        ("babeltrace-1.4", "lttng-tools-2.8"),
        ("babeltrace-1.4", "lttng-tools-2.9"),
        ("babeltrace-1.4", "lttng-tools-2.10"),
        ("babeltrace-1.4", "lttng-tools-2.11"),
        ("babeltrace-1.5", "lttng-tools-2.7"),
        ("babeltrace-1.5", "lttng-tools-2.8"),
        ("babeltrace-1.5", "lttng-tools-2.9"),
        ("babeltrace-1.5", "lttng-tools-2.11"),
]

test_matrix_base_modules = [
        ("babeltrace-1.3", "lttng-modules-2.7",  "lttng-tools-2.7"),
        ("babeltrace-1.3", "lttng-modules-2.8",  "lttng-tools-2.8"),
        ("babeltrace-1.3", "lttng-modules-2.9",  "lttng-tools-2.9"),
        ("babeltrace-1.3", "lttng-modules-2.10", "lttng-tools-2.10"),
        ("babeltrace-1.3", "lttng-modules-2.11", "lttng-tools-2.11"),
        ("babeltrace-1.4", "lttng-modules-2.7",  "lttng-tools-2.7"),
        ("babeltrace-1.4", "lttng-modules-2.8",  "lttng-tools-2.8"),
        ("babeltrace-1.4", "lttng-modules-2.9",  "lttng-tools-2.9"),
        ("babeltrace-1.4", "lttng-modules-2.10", "lttng-tools-2.10"),
        ("babeltrace-1.4", "lttng-modules-2.11", "lttng-tools-2.11"),
        ("babeltrace-1.5", "lttng-modules-2.7",  "lttng-tools-2.7"),
        ("babeltrace-1.5", "lttng-modules-2.8",  "lttng-tools-2.8"),
        ("babeltrace-1.5", "lttng-modules-2.9",  "lttng-tools-2.9"),
        ("babeltrace-1.5", "lttng-modules-2.10", "lttng-tools-2.10"),
        ("babeltrace-1.5", "lttng-modules-2.11", "lttng-tools-2.11"),
]

test_matrix_lost_packet = [
        ("babeltrace-1.3", False),
        ("babeltrace-1.4", True),
        ("babeltrace-1.5", True),
]

test_matrix_same_trace_modules = [
        (["babeltrace-1.3", "babeltrace-1.4", "babeltrace-1.5"], "lttng-modules-2.7",  "lttng-tools-2.7"),
        (["babeltrace-1.3", "babeltrace-1.4", "babeltrace-1.5"], "lttng-modules-2.8",  "lttng-tools-2.8"),
        (["babeltrace-1.3", "babeltrace-1.4", "babeltrace-1.5"], "lttng-modules-2.9",  "lttng-tools-2.9"),
        (["babeltrace-1.3", "babeltrace-1.4", "babeltrace-1.5"], "lttng-modules-2.10", "lttng-tools-2.10"),
        (["babeltrace-1.3", "babeltrace-1.4", "babeltrace-1.5"], "lttng-modules-2.11", "lttng-tools-2.11"),
]

test_matrix_same_trace_ust = [
        (["babeltrace-1.3", "babeltrace-1.4", "babeltrace-1.5"], "lttng-tools-2.7"),
        (["babeltrace-1.3", "babeltrace-1.4", "babeltrace-1.5"], "lttng-tools-2.8"),
        (["babeltrace-1.3", "babeltrace-1.4", "babeltrace-1.5"], "lttng-tools-2.9"),
        (["babeltrace-1.3", "babeltrace-1.4", "babeltrace-1.5"], "lttng-tools-2.10"),
        (["babeltrace-1.3", "babeltrace-1.4", "babeltrace-1.5"], "lttng-tools-2.11"),
]


runtime_matrix_base_ust = []
runtime_matrix_lost_packet = []
runtime_matrix_base_modules = []
runtime_matrix_same_trace_modules = []
runtime_matrix_same_trace_ust = []


if not Settings.test_only:
    runtime_matrix_base_ust = test_matrix_base_ust
    runtime_matrix_base_modules = test_matrix_base_modules
    runtime_matrix_lost_packet = test_matrix_lost_packet
    runtime_matrix_same_trace_modules = test_matrix_same_trace_modules
    runtime_matrix_same_trace_ust = test_matrix_same_trace_ust
else:
    for tup in test_matrix_base_ust:
        if (tup[0] in Settings.test_only or tup[1] in
                Settings.test_only):
            runtime_matrix_base_ust.append(tup)
    for tup in test_matrix_base_modules:
        if (tup[0] in Settings.test_only or tup[1] in
                Settings.test_only):
            runtime_matrix_base_modules.append(tup)
    for tup in test_matrix_lost_packet:
        if (tup[0] in Settings.test_only or tup[1] in
                Settings.test_only):
            test_matrix_lost_packet.append(tup)
    for tup in test_matrix_same_trace_modules:
        if (tup[0] in Settings.test_only or tup[1] in
                Settings.test_only):
            runtime_matrix_same_trace_modules.append(tup)
    for tup in test_matrix_same_trace_ust:
        if (tup[0] in Settings.test_only or tup[1] in
                Settings.test_only):
            runtime_matrix_same_trace_ust.append(tup)


@pytest.mark.parametrize("babeltrace_l, tools_l", runtime_matrix_base_ust)
def test_babeltrace_base_ust(tmpdir, babeltrace_l, tools_l):

    nb_events = 100

    # Prepare environment
    babeltrace = ProjectFactory.get_precook(babeltrace_l)
    tools = ProjectFactory.get_precook(tools_l)

    runtime_path = os.path.join(str(tmpdir), "runtime")
    app_path = os.path.join(str(tmpdir), "app")

    with Run.get_runtime(runtime_path) as runtime:
        runtime.add_project(tools)
        runtime.add_project(babeltrace)

        # Make application using the runtime
        shutil.copytree(Settings.apps_gen_events_folder, app_path)
        runtime.run("make V=1", cwd=app_path)

        # Start lttng-sessiond
        sessiond = utils.sessiond_spawn(runtime)

        # Create session using mi to get path and session name
        runtime.run('lttng create trace')
        runtime.run('lttng enable-event -u tp:tptest')
        runtime.run('lttng start')

        # Run application
        cmd = './app {}'.format(nb_events)
        runtime.run(cmd, cwd=app_path)

        # Stop tracing
        runtime.run('lttng stop')
        runtime.run('lttng destroy -a')
        cp = runtime.subprocess_terminate(sessiond)
        if cp.returncode != 0:
            pytest.fail("Sessiond return code")

        # Do not validate the metadata only the return code of babeltrace
        cmd = 'babeltrace -o ctf-metadata {}'.format(runtime.lttng_home)
        runtime.run(cmd)

        cmd = 'babeltrace {}'.format(runtime.lttng_home)
        cp_process, cp_out, cp_err = runtime.run(cmd)
        assert(utils.line_count(cp_out) == nb_events)


@must_be_root
@pytest.mark.parametrize("babeltrace_l,modules_l,tools_l", runtime_matrix_base_modules)
def test_babeltrace_base_modules(tmpdir, babeltrace_l, modules_l, tools_l):
    modules = ProjectFactory.get_precook(modules_l)
    if modules.skip:
        pytest.skip("{} cannot be built on this kernel".format(modules.label))
    tools = ProjectFactory.get_precook(tools_l)
    babeltrace = ProjectFactory.get_precook(babeltrace_l)

    nb_events = 100

    with Run.get_runtime(str(tmpdir)) as runtime:
        runtime.add_project(modules)
        runtime.add_project(tools)
        runtime.add_project(babeltrace)

        sessiond = utils.sessiond_spawn(runtime)
        runtime.load_test_module()

        runtime.run("lttng create trace")
        runtime.run("lttng enable-event -k lttng_test_filter_event")
        runtime.run("lttng start")
        with open(Settings.lttng_test_procfile, 'w') as procfile:
            procfile.write("{}".format(nb_events))

        runtime.run("lttng stop")
        runtime.run("lttng destroy -a")

        sessiond = runtime.subprocess_terminate(sessiond)
        if sessiond.returncode != 0:
            pytest.fail("Return value of sessiond is not zero")
            return

        babeltrace_cmd = 'babeltrace {}'.format(runtime.lttng_home)
        cp_process, cp_out, cp_err = runtime.run(babeltrace_cmd)
        assert(utils.line_count(cp_out) == nb_events)


@must_be_root
@pytest.mark.parametrize("babeltrace_list,modules_l,tools_l", runtime_matrix_same_trace_modules)
def test_babeltrace_same_trace_modules(tmpdir, babeltrace_list, modules_l, tools_l):
    modules = ProjectFactory.get_precook(modules_l)
    if modules.skip:
        pytest.skip("{} cannot be built on this kernel".format(modules.label))
    tools = ProjectFactory.get_precook(tools_l)

    nb_events = 100

    with Run.get_runtime(str(tmpdir)) as runtime:
        runtime.add_project(modules)
        runtime.add_project(tools)

        sessiond = utils.sessiond_spawn(runtime)
        runtime.load_test_module()

        runtime.run("lttng create trace")
        runtime.run("lttng enable-event -k lttng_test_filter_event")
        runtime.run("lttng start")
        with open(Settings.lttng_test_procfile, 'w') as procfile:
            procfile.write("{}".format(nb_events))

        runtime.run("lttng stop")
        runtime.run("lttng destroy -a")

        sessiond = runtime.subprocess_terminate(sessiond)
        if sessiond.returncode != 0:
            pytest.fail("Return value of sessiond is not zero")
            return

        # Actual testing
        processed_trace_files = {}
        # Gather text traces
        for label in babeltrace_list:
            babeltrace = ProjectFactory.get_precook(label)
            runtime.add_project(babeltrace)
            babeltrace_cmd = 'babeltrace {}'.format(runtime.lttng_home)
            cp_process, cp_out, cp_err = runtime.run(babeltrace_cmd)
            assert (utils.line_count(cp_out) == nb_events)
            processed_trace_files[label] = cp_out
            runtime.remove_project(babeltrace)

        # Perform combinations and validate that traces match
        for a, b in combinations(processed_trace_files, 2):
            version_a = processed_trace_files[a]
            version_b = processed_trace_files[b]
            assert (filecmp.cmp(version_a, version_b)), "Processed trace from {} and {} differ.".format(a,b)

@pytest.mark.parametrize("babeltrace_list,tools_l", runtime_matrix_same_trace_ust)
def test_babeltrace_same_trace_ust(tmpdir, babeltrace_list, tools_l):
    tools = ProjectFactory.get_precook(tools_l)

    nb_events = 100

    app_path = os.path.join(str(tmpdir), "app")

    with Run.get_runtime(str(tmpdir)) as runtime:
        runtime.add_project(tools)

        shutil.copytree(Settings.apps_gen_events_folder, app_path)
        runtime.run("make V=1", cwd=app_path)

        sessiond = utils.sessiond_spawn(runtime)

        # Create session using mi to get path and session name
        runtime.run('lttng create trace')
        runtime.run('lttng enable-event -u tp:tptest')
        runtime.run('lttng start')

        # Run application
        cmd = './app {}'.format(nb_events)
        runtime.run(cmd, cwd=app_path)

        # Stop tracing
        runtime.run('lttng stop')
        runtime.run('lttng destroy -a')
        cp = runtime.subprocess_terminate(sessiond)
        if cp.returncode != 0:
            pytest.fail("Sessiond return code")

        # Actual testing
        processed_trace_files = {}
        # Gather text traces
        for label in babeltrace_list:
            babeltrace = ProjectFactory.get_precook(label)
            runtime.add_project(babeltrace)
            babeltrace_cmd = 'babeltrace {}'.format(runtime.lttng_home)
            cp_process, cp_out, cp_err = runtime.run(babeltrace_cmd)
            assert (utils.line_count(cp_out) == nb_events)
            processed_trace_files[label] = cp_out
            runtime.remove_project(babeltrace)

        # Perform combinations and validate that traces match
        for a, b in combinations(processed_trace_files, 2):
            version_a = processed_trace_files[a]
            version_b = processed_trace_files[b]
            assert (filecmp.cmp(version_a, version_b)), "Processed trace from {} and {} differ.".format(a, b)



@pytest.mark.parametrize("babeltrace_l,supported", runtime_matrix_lost_packet)
def test_babeltrace_lost_patcket(tmpdir, babeltrace_l, supported):
    babeltrace = ProjectFactory.get_precook(babeltrace_l)

    trace_path = Settings.trace_lost_packet

    with Run.get_runtime(str(tmpdir)) as runtime:
        runtime.add_project(babeltrace)
        cmd = "babeltrace {}".format(trace_path)
        cp, cp_out, cp_err = runtime.run(cmd)
        if supported:
            assert(utils.file_contains(cp_err, "Tracer lost 3 trace packets"))
            assert(utils.file_contains(cp_err, "Tracer lost 2 trace packets"))
            assert(utils.file_contains(cp_err, "Tracer lost 1 trace packets"))
        else:
            os.path.getsize(cp_err) > 0

        assert(utils.line_count(cp_out) == 8)
