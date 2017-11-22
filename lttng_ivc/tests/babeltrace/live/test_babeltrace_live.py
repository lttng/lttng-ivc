import pytest
import os
import shutil
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
First member: babeltrace label
Second member: tools label
"""
test_matrix_live = [
        pytest.param("babeltrace-1.3", "lttng-tools-2.7", marks=pytest.mark.xfail(reason="Flaky test or Flaky babeltrace. Is under investigation")),
        pytest.param("babeltrace-1.3", "lttng-tools-2.8", marks=pytest.mark.xfail(reason="Flaky test or Flaky babeltrace. Is under investigation")),
        pytest.param("babeltrace-1.3", "lttng-tools-2.9", marks=pytest.mark.xfail(reason="Flaky test or Flaky babeltrace. Is under investigation")),
        pytest.param("babeltrace-1.3", "lttng-tools-2.10", marks=pytest.mark.xfail(reason="Flaky test or Flaky babeltrace. Is under investigation")),
        ("babeltrace-1.4", "lttng-tools-2.7"),
        ("babeltrace-1.4", "lttng-tools-2.8"),
        ("babeltrace-1.4", "lttng-tools-2.9"),
        ("babeltrace-1.4", "lttng-tools-2.10"),
        ("babeltrace-1.5", "lttng-tools-2.7"),
        ("babeltrace-1.5", "lttng-tools-2.8"),
        ("babeltrace-1.5", "lttng-tools-2.9"),
        ("babeltrace-1.5", "lttng-tools-2.10"),
]

runtime_matrix_live = []

if not Settings.test_only:
    runtime_matrix_live = test_matrix_live
else:
    for tup in test_matrix_live:
        if (tup[0] in Settings.test_only or tup[1] in
                Settings.test_only):
            runtime_matrix_live.append(tup)


@pytest.mark.parametrize("babeltrace_l,tools_l", runtime_matrix_live)
def test_babeltrace_live(tmpdir, babeltrace_l, tools_l):

    nb_loop = 100
    nb_expected_events = 100

    babeltrace = ProjectFactory.get_precook(babeltrace_l)
    tools = ProjectFactory.get_precook(tools_l)

    runtime_path = os.path.join(str(tmpdir), "runtime")
    app_path = os.path.join(str(tmpdir), "app")
    session_name = "trace"

    with Run.get_runtime(runtime_path) as runtime:
        runtime.add_project(tools)
        runtime.add_project(babeltrace)

        shutil.copytree(Settings.apps_gen_events_folder, app_path)
        runtime.run("make V=1", cwd=app_path)

        relayd, ctrl_port, data_port, live_port = utils.relayd_spawn(runtime)
        sessiond = utils.sessiond_spawn(runtime)

        hostname = socket.gethostname()
        url_babeltrace = "net://localhost:{}/host/{}/{}".format(live_port, hostname, session_name)
        url = "net://localhost:{}:{}".format(ctrl_port, data_port)

        # Create session using mi to get path and session name
        runtime.run('lttng create --set-url={} {} --live'.format(url, session_name))

        runtime.run('lttng enable-event -u tp:tptest')

        # From now on babeltrace should be able to hook itself up.
        # Synchronization point is done via relayd log
        p_babeltrace = runtime.spawn_subprocess("babeltrace -i lttng-live {}".format(url_babeltrace))

        # TODO: Move to settings
        timeout = 60
        # TODO: Move to settings
        # Make sure that babeltrace did hook itself or at least tried to.
        synchro_text = "Version check done using protocol"
        listening = False
        for i in range(timeout):
            log = runtime.get_subprocess_stderr_path(relayd)
            if utils.file_contains(log, synchro_text):
                listening = True
                break
            time.sleep(1)

        if not listening:
            raise Exception("Babeltrace live is not listening after timeout")

        runtime.run('lttng start')

        # Run application
        cmd = './app {}'.format(nb_loop)
        runtime.run(cmd, cwd=app_path)

        # Stop tracing
        runtime.run('lttng stop')
        runtime.run('lttng destroy -a')

        # Make sure babeltrace is done reading
        runtime.subprocess_wait(p_babeltrace)

        runtime.subprocess_terminate(sessiond)
        runtime.subprocess_terminate(relayd)

        # Check the output from babeltrace
        cp_out = runtime.get_subprocess_stdout_path(p_babeltrace)
        assert(utils.line_count(cp_out) == nb_expected_events)
