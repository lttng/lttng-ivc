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
import glob
import subprocess

import lttng_ivc.utils.ProjectFactory as ProjectFactory
import lttng_ivc.utils.runtime as Run
import lttng_ivc.settings as Settings
from lttng_ivc.utils.skip import must_be_root
from lttng_ivc.utils.utils import sessiond_spawn
from lttng_ivc.utils.utils import line_count
from lttng_ivc.utils.utils import file_contains

"""

NOTE: Kernel version is left to the Lttng-modules object on building. We assume
that a failing lttng-modules build is caused only by version validation. This
project is not dedicated to finding build problem but inter version problem.

NOTE: The command for regenerate metadata changed between 2.8 and 2.9 from
"metadata regenerate" to "regenerate metadata" breaking the cli ....bad
jdesfossez :P

TODO:Packet sequence number. 5b3cf4f924befda843a7736daf84f8ecae5e86a4
     LTTNG_RING_BUFFER_GET_SEQ_NUM
TODO:Stream instance id. 5594698f9c8ad13e0964c67946d1867df7757dae
     LTTNG_RING_BUFFER_INSTANCE_ID


FC: Fully Compatible
BC: Feature of the smallest version number will works.

+-------------------------------------------------------+
| LTTng Modules ABI vs LTTng Tools compatibility matrix |
+-------------------------------------------------------+--------------
| Modules / Tools  | 2.7  | 2.8  | 2.9  | 2.10          | 2.11 | 2.12 |
+------------------+------+------+------+---------------+------+------+
| 2.7              | FC   | BC   | BC   | BC            | BC   | BC   |
| 2.8              | BC   | FC   | BC   | BC            | BC   | BC   |
| 2.9              | BC   | BC   | FC   | BC            | BC   | BC   |
| 2.10             | BC   | BC   | BC   | FC            | BC   | BC   |
| 2.11             | BC   | BC   | BC   | BC            | FC   | BC   |
| 2.12             | BC   | BC   | BC   | BC            | BC   | FC   |
+------------------+------+------+------+---------------+------+------+

"""

"""
First tuple member: lttng-ust label
Second tuple member: lttng-tool label
Third tuple member: expected scenario
"""
test_matrix_base_tracing = [
    ("lttng-modules-2.7", "lttng-tools-2.7"),
    ("lttng-modules-2.7", "lttng-tools-2.8"),
    ("lttng-modules-2.7", "lttng-tools-2.9"),
    ("lttng-modules-2.7", "lttng-tools-2.10"),
    ("lttng-modules-2.7", "lttng-tools-2.11"),
    ("lttng-modules-2.7", "lttng-tools-2.12"),
    ("lttng-modules-2.8", "lttng-tools-2.7"),
    ("lttng-modules-2.8", "lttng-tools-2.8"),
    ("lttng-modules-2.8", "lttng-tools-2.9"),
    ("lttng-modules-2.8", "lttng-tools-2.10"),
    ("lttng-modules-2.8", "lttng-tools-2.11"),
    ("lttng-modules-2.8", "lttng-tools-2.12"),
    ("lttng-modules-2.9", "lttng-tools-2.7"),
    ("lttng-modules-2.9", "lttng-tools-2.8"),
    ("lttng-modules-2.9", "lttng-tools-2.9"),
    ("lttng-modules-2.9", "lttng-tools-2.10"),
    ("lttng-modules-2.9", "lttng-tools-2.11"),
    ("lttng-modules-2.9", "lttng-tools-2.12"),
    ("lttng-modules-2.10", "lttng-tools-2.7"),
    ("lttng-modules-2.10", "lttng-tools-2.8"),
    ("lttng-modules-2.10", "lttng-tools-2.9"),
    ("lttng-modules-2.10", "lttng-tools-2.10"),
    ("lttng-modules-2.10", "lttng-tools-2.11"),
    ("lttng-modules-2.10", "lttng-tools-2.12"),
    ("lttng-modules-2.11", "lttng-tools-2.7"),
    ("lttng-modules-2.11", "lttng-tools-2.8"),
    ("lttng-modules-2.11", "lttng-tools-2.9"),
    ("lttng-modules-2.11", "lttng-tools-2.10"),
    ("lttng-modules-2.11", "lttng-tools-2.11"),
    ("lttng-modules-2.11", "lttng-tools-2.12"),
    ("lttng-modules-2.12", "lttng-tools-2.7"),
    ("lttng-modules-2.12", "lttng-tools-2.8"),
    ("lttng-modules-2.12", "lttng-tools-2.9"),
    ("lttng-modules-2.12", "lttng-tools-2.10"),
    ("lttng-modules-2.12", "lttng-tools-2.11"),
    ("lttng-modules-2.12", "lttng-tools-2.12"),
]

test_matrix_regen_metadata = [
    (
        "lttng-modules-2.7",
        "lttng-tools-2.7",
        "metadata regenerate",
        "Unsupported by tools",
    ),
    (
        "lttng-modules-2.7",
        "lttng-tools-2.8",
        "metadata regenerate",
        "Unsupported by modules",
    ),
    (
        "lttng-modules-2.7",
        "lttng-tools-2.9",
        "regenerate metadata",
        "Unsupported by modules",
    ),
    (
        "lttng-modules-2.7",
        "lttng-tools-2.10",
        "regenerate metadata",
        "Unsupported by modules",
    ),
    (
        "lttng-modules-2.7",
        "lttng-tools-2.11",
        "regenerate metadata",
        "Unsupported by modules",
    ),
    (
        "lttng-modules-2.7",
        "lttng-tools-2.12",
        "regenerate metadata",
        "Unsupported by modules",
    ),
    (
        "lttng-modules-2.8",
        "lttng-tools-2.7",
        "metadata regenerate",
        "Unsupported by tools",
    ),
    ("lttng-modules-2.8", "lttng-tools-2.8", "metadata regenerate", "Supported"),
    ("lttng-modules-2.8", "lttng-tools-2.9", "regenerate metadata", "Supported"),
    ("lttng-modules-2.8", "lttng-tools-2.10", "regenerate metadata", "Supported"),
    ("lttng-modules-2.8", "lttng-tools-2.11", "regenerate metadata", "Supported"),
    ("lttng-modules-2.8", "lttng-tools-2.12", "regenerate metadata", "Supported"),
    (
        "lttng-modules-2.9",
        "lttng-tools-2.7",
        "metadata regenerate",
        "Unsupported by tools",
    ),
    ("lttng-modules-2.9", "lttng-tools-2.8", "metadata regenerate", "Supported"),
    ("lttng-modules-2.9", "lttng-tools-2.9", "regenerate metadata", "Supported"),
    ("lttng-modules-2.9", "lttng-tools-2.10", "regenerate metadata", "Supported"),
    ("lttng-modules-2.9", "lttng-tools-2.11", "regenerate metadata", "Supported"),
    ("lttng-modules-2.9", "lttng-tools-2.12", "regenerate metadata", "Supported"),
    (
        "lttng-modules-2.10",
        "lttng-tools-2.7",
        "metadata regenerate",
        "Unsupported by tools",
    ),
    ("lttng-modules-2.10", "lttng-tools-2.8", "metadata regenerate", "Supported"),
    ("lttng-modules-2.10", "lttng-tools-2.9", "regenerate metadata", "Supported"),
    ("lttng-modules-2.10", "lttng-tools-2.10", "regenerate metadata", "Supported"),
    ("lttng-modules-2.10", "lttng-tools-2.11", "regenerate metadata", "Supported"),
    ("lttng-modules-2.10", "lttng-tools-2.12", "regenerate metadata", "Supported"),
    (
        "lttng-modules-2.11",
        "lttng-tools-2.7",
        "metadata regenerate",
        "Unsupported by tools",
    ),
    ("lttng-modules-2.11", "lttng-tools-2.8", "metadata regenerate", "Supported"),
    ("lttng-modules-2.11", "lttng-tools-2.9", "regenerate metadata", "Supported"),
    ("lttng-modules-2.11", "lttng-tools-2.10", "regenerate metadata", "Supported"),
    ("lttng-modules-2.11", "lttng-tools-2.11", "regenerate metadata", "Supported"),
    ("lttng-modules-2.11", "lttng-tools-2.12", "regenerate metadata", "Supported"),
    (
        "lttng-modules-2.12",
        "lttng-tools-2.7",
        "metadata regenerate",
        "Unsupported by tools",
    ),
    ("lttng-modules-2.12", "lttng-tools-2.8", "metadata regenerate", "Supported"),
    ("lttng-modules-2.12", "lttng-tools-2.9", "regenerate metadata", "Supported"),
    ("lttng-modules-2.12", "lttng-tools-2.10", "regenerate metadata", "Supported"),
    ("lttng-modules-2.12", "lttng-tools-2.11", "regenerate metadata", "Supported"),
    ("lttng-modules-2.12", "lttng-tools-2.12", "regenerate metadata", "Supported"),
]

test_matrix_statedump = [
    ("lttng-modules-2.7", "lttng-tools-2.7", "Unsupported by tools"),
    ("lttng-modules-2.7", "lttng-tools-2.8", "Unsupported by tools"),
    ("lttng-modules-2.7", "lttng-tools-2.9", "Unsupported by modules"),
    ("lttng-modules-2.7", "lttng-tools-2.10", "Unsupported by modules"),
    ("lttng-modules-2.7", "lttng-tools-2.11", "Unsupported by modules"),
    ("lttng-modules-2.7", "lttng-tools-2.12", "Unsupported by modules"),
    ("lttng-modules-2.8", "lttng-tools-2.7", "Unsupported by tools"),
    ("lttng-modules-2.8", "lttng-tools-2.8", "Unsupported by tools"),
    ("lttng-modules-2.8", "lttng-tools-2.9", "Unsupported by modules"),
    ("lttng-modules-2.8", "lttng-tools-2.10", "Unsupported by modules"),
    ("lttng-modules-2.8", "lttng-tools-2.11", "Unsupported by modules"),
    ("lttng-modules-2.8", "lttng-tools-2.12", "Unsupported by modules"),
    ("lttng-modules-2.9", "lttng-tools-2.7", "Unsupported by tools"),
    ("lttng-modules-2.9", "lttng-tools-2.8", "Unsupported by tools"),
    ("lttng-modules-2.9", "lttng-tools-2.9", "Supported"),
    ("lttng-modules-2.9", "lttng-tools-2.10", "Supported"),
    ("lttng-modules-2.9", "lttng-tools-2.11", "Supported"),
    ("lttng-modules-2.9", "lttng-tools-2.12", "Supported"),
    ("lttng-modules-2.10", "lttng-tools-2.7", "Unsupported by tools"),
    ("lttng-modules-2.10", "lttng-tools-2.8", "Unsupported by tools"),
    ("lttng-modules-2.10", "lttng-tools-2.9", "Supported"),
    ("lttng-modules-2.10", "lttng-tools-2.10", "Supported"),
    ("lttng-modules-2.10", "lttng-tools-2.11", "Supported"),
    ("lttng-modules-2.10", "lttng-tools-2.12", "Supported"),
    ("lttng-modules-2.11", "lttng-tools-2.7", "Unsupported by tools"),
    ("lttng-modules-2.11", "lttng-tools-2.8", "Unsupported by tools"),
    ("lttng-modules-2.11", "lttng-tools-2.9", "Supported"),
    ("lttng-modules-2.11", "lttng-tools-2.10", "Supported"),
    ("lttng-modules-2.11", "lttng-tools-2.11", "Supported"),
    ("lttng-modules-2.11", "lttng-tools-2.12", "Supported"),
    ("lttng-modules-2.12", "lttng-tools-2.7", "Unsupported by tools"),
    ("lttng-modules-2.12", "lttng-tools-2.8", "Unsupported by tools"),
    ("lttng-modules-2.12", "lttng-tools-2.9", "Supported"),
    ("lttng-modules-2.12", "lttng-tools-2.10", "Supported"),
    ("lttng-modules-2.12", "lttng-tools-2.11", "Supported"),
    ("lttng-modules-2.12", "lttng-tools-2.12", "Supported"),
]

test_matrix_starglobing_enabler = [
    ("lttng-modules-2.7", "lttng-tools-2.7", "Unsupported by tools"),
    ("lttng-modules-2.7", "lttng-tools-2.8", "Unsupported by tools"),
    ("lttng-modules-2.7", "lttng-tools-2.9", "Unsupported by tools"),
    ("lttng-modules-2.7", "lttng-tools-2.10", "Unsupported by modules"),
    ("lttng-modules-2.7", "lttng-tools-2.11", "Unsupported by modules"),
    ("lttng-modules-2.7", "lttng-tools-2.12", "Unsupported by modules"),
    ("lttng-modules-2.8", "lttng-tools-2.7", "Unsupported by tools"),
    ("lttng-modules-2.8", "lttng-tools-2.8", "Unsupported by tools"),
    ("lttng-modules-2.8", "lttng-tools-2.9", "Unsupported by tools"),
    ("lttng-modules-2.8", "lttng-tools-2.10", "Unsupported by modules"),
    ("lttng-modules-2.8", "lttng-tools-2.11", "Unsupported by modules"),
    ("lttng-modules-2.8", "lttng-tools-2.12", "Unsupported by modules"),
    ("lttng-modules-2.9", "lttng-tools-2.7", "Unsupported by tools"),
    ("lttng-modules-2.9", "lttng-tools-2.8", "Unsupported by tools"),
    ("lttng-modules-2.9", "lttng-tools-2.9", "Unsupported by tools"),
    ("lttng-modules-2.9", "lttng-tools-2.10", "Unsupported by modules"),
    ("lttng-modules-2.9", "lttng-tools-2.11", "Unsupported by modules"),
    ("lttng-modules-2.9", "lttng-tools-2.12", "Unsupported by modules"),
    ("lttng-modules-2.10", "lttng-tools-2.7", "Unsupported by tools"),
    ("lttng-modules-2.10", "lttng-tools-2.8", "Unsupported by tools"),
    ("lttng-modules-2.10", "lttng-tools-2.9", "Unsupported by tools"),
    ("lttng-modules-2.10", "lttng-tools-2.10", "Supported"),
    ("lttng-modules-2.10", "lttng-tools-2.11", "Supported"),
    ("lttng-modules-2.10", "lttng-tools-2.12", "Supported"),
    ("lttng-modules-2.11", "lttng-tools-2.7", "Unsupported by tools"),
    ("lttng-modules-2.11", "lttng-tools-2.8", "Unsupported by tools"),
    ("lttng-modules-2.11", "lttng-tools-2.9", "Unsupported by tools"),
    ("lttng-modules-2.11", "lttng-tools-2.10", "Supported"),
    ("lttng-modules-2.11", "lttng-tools-2.11", "Supported"),
    ("lttng-modules-2.11", "lttng-tools-2.12", "Supported"),
    ("lttng-modules-2.12", "lttng-tools-2.7", "Unsupported by tools"),
    ("lttng-modules-2.12", "lttng-tools-2.8", "Unsupported by tools"),
    ("lttng-modules-2.12", "lttng-tools-2.9", "Unsupported by tools"),
    ("lttng-modules-2.12", "lttng-tools-2.10", "Supported"),
    ("lttng-modules-2.12", "lttng-tools-2.11", "Supported"),
    ("lttng-modules-2.12", "lttng-tools-2.12", "Supported"),
]


def get_metadata_file_path(base_trace_path):
    metadata = os.path.join(base_trace_path, "kernel", "metadata")
    return metadata


runtime_matrix_base_tracing = Settings.generate_runtime_test_matrix(
    test_matrix_base_tracing, [0, 1]
)
runtime_matrix_regen_metadata = Settings.generate_runtime_test_matrix(
    test_matrix_regen_metadata, [0, 1]
)
runtime_matrix_statedump = Settings.generate_runtime_test_matrix(
    test_matrix_statedump, [0, 1]
)
runtime_matrix_starglobing_enabler = Settings.generate_runtime_test_matrix(
    test_matrix_starglobing_enabler, [0, 1]
)


@must_be_root
@pytest.mark.parametrize("modules_label,tools_label", runtime_matrix_base_tracing)
def test_modules_base_tracing(tmpdir, modules_label, tools_label):
    modules = ProjectFactory.get_precook(modules_label)
    if modules.skip:
        pytest.skip("{} cannot be built on this kernel".format(modules.label))
    tools = ProjectFactory.get_precook(tools_label)
    babeltrace = ProjectFactory.get_precook(Settings.default_babeltrace)

    nb_events = 100

    with Run.get_runtime(str(tmpdir)) as runtime:
        runtime.add_project(modules)
        runtime.add_project(tools)
        runtime.add_project(babeltrace)

        trace_path = os.path.join(runtime.lttng_home, "trace")
        babeltrace_cmd = "babeltrace {}".format(trace_path)

        sessiond = sessiond_spawn(runtime)
        runtime.load_test_module()

        runtime.run("lttng create trace -o {}".format(trace_path))
        runtime.run("lttng enable-event -k lttng_test_filter_event")
        runtime.run("lttng start")
        with open(Settings.lttng_test_procfile, "w") as procfile:
            procfile.write("{}".format(nb_events))

        runtime.run("lttng stop")
        runtime.run("lttng destroy -a")

        sessiond = runtime.subprocess_terminate(sessiond)
        if sessiond.returncode != 0:
            pytest.fail("Return value of sessiond is not zero")
            return

        cp_process, cp_out, cp_err = runtime.run(babeltrace_cmd)
        assert line_count(cp_out) == nb_events


@must_be_root
@pytest.mark.parametrize(
    "modules_label,tools_label,command,scenario", runtime_matrix_regen_metadata
)
def test_modules_regen_metadata(tmpdir, modules_label, tools_label, command, scenario):
    modules = ProjectFactory.get_precook(modules_label)
    if modules.skip:
        pytest.skip("{} cannot be built on this kernel".format(modules.label))
    tools = ProjectFactory.get_precook(tools_label)
    babeltrace = ProjectFactory.get_precook(Settings.default_babeltrace)

    nb_events = 10

    with Run.get_runtime(str(tmpdir)) as runtime:
        runtime.add_project(modules)
        runtime.add_project(tools)
        runtime.add_project(babeltrace)

        trace_path = os.path.join(runtime.lttng_home, "trace")
        babeltrace_cmd = "babeltrace {}".format(trace_path)

        sessiond = sessiond_spawn(runtime)
        runtime.load_test_module()

        runtime.run("lttng create trace -o {}".format(trace_path))
        runtime.run("lttng enable-event -k lttng_test_filter_event")
        runtime.run("lttng start")
        with open(Settings.lttng_test_procfile, "w") as procfile:
            procfile.write("{}".format(nb_events))

        runtime.run("lttng stop")

        # Validate that we have all event base on the current metadata
        cp_process, cp_out, cp_err = runtime.run(babeltrace_cmd)
        assert line_count(cp_out) == nb_events

        # Empty the metadata file
        open(get_metadata_file_path(trace_path), "w").close()

        # Babeltrace should never be able to parse the trace
        with pytest.raises(subprocess.CalledProcessError):
            runtime.run(babeltrace_cmd)

        runtime.run("lttng start")

        # TODO: rework this a bit to differentiate each errors and rework how
        # the condition are meet
        if scenario == "Unsupported by tools" or scenario == "Unsupported by modules":
            if (
                modules_label == "lttng-modules-2.7"
                and scenario == "Unsupported by modules"
            ):
                # Error from lttng-modules-2.7 is not reported correctly by
                # sessiond. But it is reported on the sessiond side.
                # For now, run the command, validate that the error exist on
                # sessiond side and mark as xfail.
                runtime.run("lttng {}".format(command))
            else:
                with pytest.raises(subprocess.CalledProcessError):
                    runtime.run("lttng {}".format(command))

            # Make sure everything looks good on this side
            runtime.run("lttng stop")
            runtime.run("lttng destroy -a")
            stderr_path = runtime.get_subprocess_stderr_path(sessiond)
            sessiond = runtime.subprocess_terminate(sessiond)
            if scenario == "Unsupported by modules":
                error_msg = "Error: Failed to regenerate the kernel metadata"
                assert file_contains(stderr_path, [error_msg]), "Error message missing"
            if (
                modules_label == "lttng-modules-2.7"
                and scenario == "Unsupported by modules"
            ):
                pytest.xfail(
                    "Lttng-tools does not bubble up error from unsupported metadata regeneration"
                )

            return

        runtime.run("lttng {}".format(command))
        runtime.run("lttng stop")
        runtime.run("lttng destroy -a")

        sessiond = runtime.subprocess_terminate(sessiond)
        if sessiond.returncode != 0:
            pytest.fail("Return value of sessiond is not zero")

        cp_process, cp_out, cp_err = runtime.run(babeltrace_cmd)
        assert line_count(cp_out) == nb_events


@must_be_root
@pytest.mark.parametrize("modules_label,tools_label,scenario", runtime_matrix_statedump)
def test_modules_statedump(tmpdir, modules_label, tools_label, scenario):
    modules = ProjectFactory.get_precook(modules_label)
    if modules.skip:
        pytest.skip("{} cannot be built on this kernel".format(modules.label))
    tools = ProjectFactory.get_precook(tools_label)
    babeltrace = ProjectFactory.get_precook(Settings.default_babeltrace)

    nb_events = 100
    if scenario == "Unsupported by tools" or scenario == "Unsupported by modules":
        expected_event = 2
    else:
        expected_event = 4

    with Run.get_runtime(str(tmpdir)) as runtime:
        runtime.add_project(modules)
        runtime.add_project(tools)
        runtime.add_project(babeltrace)

        trace_path = os.path.join(runtime.lttng_home, "trace")
        babeltrace_cmd = "babeltrace {}".format(trace_path)

        sessiond = sessiond_spawn(runtime)
        runtime.load_test_module()

        runtime.run("lttng create trace -o {}".format(trace_path))
        runtime.run("lttng enable-event -k lttng_statedump_start,lttng_statedump_end")
        runtime.run("lttng start")

        # Generate some event
        with open(Settings.lttng_test_procfile, "w") as procfile:
            procfile.write("{}".format(nb_events))

        if scenario == "Unsupported by tools" or scenario == "Unsupported by modules":
            with pytest.raises(subprocess.CalledProcessError):
                runtime.run("lttng regenerate statedump")
        else:
            runtime.run("lttng regenerate statedump")

        runtime.run("lttng stop")
        runtime.run("lttng destroy -a")

        sessiond = runtime.subprocess_terminate(sessiond)
        if sessiond.returncode != 0:
            pytest.fail("Return value of sessiond is not zero")

        cp_process, cp_out, cp_err = runtime.run(babeltrace_cmd)
        assert line_count(cp_out) == expected_event


@must_be_root
@pytest.mark.parametrize(
    "modules_label,tools_label, scenario", runtime_matrix_starglobing_enabler
)
def test_modules_starglobing_enabler(tmpdir, modules_label, tools_label, scenario):
    modules = ProjectFactory.get_precook(modules_label)
    if modules.skip:
        pytest.skip("{} cannot be built on this kernel".format(modules.label))
    tools = ProjectFactory.get_precook(tools_label)
    babeltrace = ProjectFactory.get_precook(Settings.default_babeltrace)

    nb_events = 100

    if scenario == "Unsupported by modules":
        expected_events = 0
    else:
        expected_events = nb_events

    with Run.get_runtime(str(tmpdir)) as runtime:
        runtime.add_project(modules)
        runtime.add_project(tools)
        runtime.add_project(babeltrace)

        trace_path = os.path.join(runtime.lttng_home, "trace")
        babeltrace_cmd = "babeltrace {}".format(trace_path)

        sessiond = sessiond_spawn(runtime)
        runtime.load_test_module()

        runtime.run("lttng create trace -o {}".format(trace_path))

        if scenario == "Unsupported by tools":
            with pytest.raises(subprocess.CalledProcessError):
                runtime.run("lttng enable-event -k 'lttng_test_*_even*'")
            sessiond = runtime.subprocess_terminate(sessiond)
            if sessiond.returncode != 0:
                pytest.fail("Return value of sessiond is not zero")
            return

        runtime.run("lttng enable-event -k 'lttng_test_*_even*'")
        runtime.run("lttng start")

        # Generate some event
        with open(Settings.lttng_test_procfile, "w") as procfile:
            procfile.write("{}".format(nb_events))

        runtime.run("lttng stop")
        runtime.run("lttng destroy -a")

        sessiond = runtime.subprocess_terminate(sessiond)
        if sessiond.returncode != 0:
            pytest.fail("Return value of sessiond is not zero")

        cp_process, cp_out, cp_err = runtime.run(babeltrace_cmd)
        assert line_count(cp_out) == expected_events
