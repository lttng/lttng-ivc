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

+------------------------------------------------------------------------------+
|              LTTng UST control protocol compatibility matrix                 |
|   (between applications and tools linked on LTTng UST and liblttng-ust-ctl)  |
+--------------------------+------------+------------+------------+------------+
| LTTng UST / LTTng Tools  | 2.7 (6.0)  | 2.8 (6.1)  | 2.9 (7.1)  | 2.10 (7.2) |
+--------------------------+------------+------------+------------+------------+
| 2.7 (6.0)                | FC         | BC         | TU         | TU         |
| 2.8 (6.1)                | BC         | FC         | TU         | TU         |
| 2.9 (7.1)                | TU         | TU         | FC         | BC         |
| 2.10 (7.2)               | TU         | TU         | BC         | FC         |
+--------------------------+------------+------------+------------+------------+

Version number of this API is defined in include/lttng/ust-abi.h of lttng-ust project

"""

"""
First tuple member: lttng-ust label
Second tuple member: lttng-tool label
Third tuple member: expected scenario
"""

test_matrix_tracing_available = [
    ("lttng-ust-2.7", "lttng-tools-2.7",   True),
    ("lttng-ust-2.7", "lttng-tools-2.8",   True),
    ("lttng-ust-2.7", "lttng-tools-2.9",   False),
    ("lttng-ust-2.7", "lttng-tools-2.10",  False),
    ("lttng-ust-2.8", "lttng-tools-2.7",   True),
    ("lttng-ust-2.8", "lttng-tools-2.8",   True),
    ("lttng-ust-2.8", "lttng-tools-2.9",   False),
    ("lttng-ust-2.8", "lttng-tools-2.10",  False),
    ("lttng-ust-2.9", "lttng-tools-2.7",   False),
    ("lttng-ust-2.9", "lttng-tools-2.8",   False),
    ("lttng-ust-2.9", "lttng-tools-2.9",   True),
    ("lttng-ust-2.9", "lttng-tools-2.10",  True),
    ("lttng-ust-2.10", "lttng-tools-2.7",  False),
    ("lttng-ust-2.10", "lttng-tools-2.8",  False),
    ("lttng-ust-2.10", "lttng-tools-2.9",  True),
    ("lttng-ust-2.10", "lttng-tools-2.10", True),
]

# Only consider test case for which tracing is valid
test_matrix_app_context = [
    ("lttng-ust-2.7", "lttng-tools-2.7",  ""),
    ("lttng-ust-2.7", "lttng-tools-2.8",  ""),
    ("lttng-ust-2.7", "lttng-tools-2.9",  ""),
    ("lttng-ust-2.7", "lttng-tools-2.10", ""),
    ("lttng-ust-2.8", "lttng-tools-2.7",  ""),
    ("lttng-ust-2.8", "lttng-tools-2.8",  ""),
    ("lttng-ust-2.8", "lttng-tools-2.9",  ""),
    ("lttng-ust-2.8", "lttng-tools-2.10", ""),
    ("lttng-ust-2.9", "lttng-tools-2.7",  ""),
    ("lttng-ust-2.9", "lttng-tools-2.8",  ""),
    ("lttng-ust-2.9", "lttng-tools-2.9",  ""),
    ("lttng-ust-2.9", "lttng-tools-2.10", ""),
    ("lttng-ust-2.10", "lttng-tools-2.7", ""),
    ("lttng-ust-2.10", "lttng-tools-2.8", ""),
    ("lttng-ust-2.10", "lttng-tools-2.9", ""),
    ("lttng-ust-2.10", "lttng-tools-2.10", ""),
]

runtime_matrix_tracing_available = []

if not Settings.test_only:
    runtime_matrix_tracing_available = test_matrix_tracing_available
else:
    for tup in test_matrix_tracing_available:
        if (tup[0] in Settings.test_only or tup[1] in
                Settings.test_only):
            runtime_matrix_tracing_available.append(tup)


def lttng_sessiond_ready():
    print("lttng sessiond is ready ! FFS")

@pytest.mark.parametrize("ust_label,tools_label, should_trace", runtime_matrix_tracing_available)
def test_ust_app_tracing_available(tmpdir, ust_label, tools_label, should_trace):

    nb_events = 100

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
        shutil.copytree(Settings.apps_gen_events_folder, app_path)
        runtime_app.run("make V=1", cwd=app_path)

        # Start lttng-sessiond
        sessiond = utils.sessiond_spawn(runtime_tools)

        # Create session using mi to get path and session name
        runtime_tools.run('lttng create trace --output={}'.format(trace_path))

        # TODO: test with event present in listing

        runtime_tools.run('lttng enable-event -u tp:tptest')
        runtime_tools.run('lttng start')

        # Run application
        cmd = './app {}'.format(nb_events)
        runtime_app.run(cmd, cwd=app_path)

        # Stop tracing
        runtime_tools.run('lttng destroy -a')
        runtime_tools.subprocess_terminate(sessiond)

        try:
            # Read trace with babeltrace and check for event count via number of line
            cmd = 'babeltrace {}'.format(trace_path)
            cp_process, cp_out, cp_err = runtime_tools.run(cmd)
            assert(utils.line_count(cp_out) == nb_events)
        except subprocess.CalledProcessError as e:
            # Check if we expected a problem here
            if should_trace:
                # Something happened
                raise e
