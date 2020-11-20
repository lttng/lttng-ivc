# Copyright (c) 2019 Jonathan Rajotte-Julien <jonathan.rajotte-julien@efficios.com>
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

import os
import shutil
import socket
from collections import namedtuple
from io import StringIO
from pprint import pformat

import pytest

import lttng_ivc.utils.ProjectFactory as ProjectFactory
import lttng_ivc.utils.utils as utils
import lttng_ivc.utils.runtime as Run
import lttng_ivc.settings as Settings

"""
Local output test only test regression across version
"""
matrix_base = [
    ("lttng-tools-2.7",),
    ("lttng-tools-2.8",),
    ("lttng-tools-2.9",),
    ("lttng-tools-2.10",),
    ("lttng-tools-2.11",),
    ("lttng-tools-2.12",),
    ("lttng-tools-2.13",),
]

"""
Generate tuple for uid and pid mode.
"""
test_matrix_base = [tup + ("uid",) for tup in matrix_base] + [
    tup + ("pid",) for tup in matrix_base
]

"""
First member: relayd via lttng-tools
Second member: lttng-tools
"""
matrix_relayd = [
    ("lttng-tools-2.7", "lttng-tools-2.7"),
    ("lttng-tools-2.7", "lttng-tools-2.8"),
    ("lttng-tools-2.7", "lttng-tools-2.9"),
    ("lttng-tools-2.7", "lttng-tools-2.10"),
    ("lttng-tools-2.7", "lttng-tools-2.11"),
    ("lttng-tools-2.7", "lttng-tools-2.12"),
    ("lttng-tools-2.7", "lttng-tools-2.13"),
    ("lttng-tools-2.8", "lttng-tools-2.7"),
    ("lttng-tools-2.8", "lttng-tools-2.8"),
    ("lttng-tools-2.8", "lttng-tools-2.9"),
    ("lttng-tools-2.8", "lttng-tools-2.10"),
    ("lttng-tools-2.8", "lttng-tools-2.11"),
    ("lttng-tools-2.8", "lttng-tools-2.12"),
    ("lttng-tools-2.8", "lttng-tools-2.13"),
    ("lttng-tools-2.9", "lttng-tools-2.7"),
    ("lttng-tools-2.9", "lttng-tools-2.8"),
    ("lttng-tools-2.9", "lttng-tools-2.9"),
    ("lttng-tools-2.9", "lttng-tools-2.10"),
    ("lttng-tools-2.9", "lttng-tools-2.11"),
    ("lttng-tools-2.9", "lttng-tools-2.12"),
    ("lttng-tools-2.9", "lttng-tools-2.13"),
    ("lttng-tools-2.10", "lttng-tools-2.7"),
    ("lttng-tools-2.10", "lttng-tools-2.8"),
    ("lttng-tools-2.10", "lttng-tools-2.9"),
    ("lttng-tools-2.10", "lttng-tools-2.10"),
    ("lttng-tools-2.10", "lttng-tools-2.11"),
    ("lttng-tools-2.10", "lttng-tools-2.12"),
    ("lttng-tools-2.10", "lttng-tools-2.13"),
    ("lttng-tools-2.11", "lttng-tools-2.7"),
    ("lttng-tools-2.11", "lttng-tools-2.8"),
    ("lttng-tools-2.11", "lttng-tools-2.9"),
    ("lttng-tools-2.11", "lttng-tools-2.10"),
    ("lttng-tools-2.11", "lttng-tools-2.11"),
    ("lttng-tools-2.11", "lttng-tools-2.12"),
    ("lttng-tools-2.11", "lttng-tools-2.13"),
    ("lttng-tools-2.12", "lttng-tools-2.7"),
    ("lttng-tools-2.12", "lttng-tools-2.8"),
    ("lttng-tools-2.12", "lttng-tools-2.9"),
    ("lttng-tools-2.12", "lttng-tools-2.10"),
    ("lttng-tools-2.12", "lttng-tools-2.11"),
    ("lttng-tools-2.12", "lttng-tools-2.12"),
    ("lttng-tools-2.12", "lttng-tools-2.13"),
    ("lttng-tools-2.13", "lttng-tools-2.7"),
    ("lttng-tools-2.13", "lttng-tools-2.8"),
    ("lttng-tools-2.13", "lttng-tools-2.9"),
    ("lttng-tools-2.13", "lttng-tools-2.10"),
    ("lttng-tools-2.13", "lttng-tools-2.11"),
    ("lttng-tools-2.13", "lttng-tools-2.12"),
    ("lttng-tools-2.13", "lttng-tools-2.13"),
]

"""
Generate tuple for uid and pid mode.
"""
test_matrix_relayd = [tup + ("uid",) for tup in matrix_relayd] + [
    tup + ("pid",) for tup in matrix_relayd
]

runtime_matrix_base = Settings.generate_runtime_test_matrix(test_matrix_base, [0])
runtime_matrix_relayd = Settings.generate_runtime_test_matrix(
    test_matrix_relayd, [0, 1]
)


"""
Generate tuple for relayd test involving snapshot:
This is needed due to:
    commit 10d653513d572b8727d6935767a96c9dd82e4fe2
    Author: Julien Desfossez <jdesfossez@efficios.com>
    Date:   Wed Aug 30 14:06:42 2017 -0400

    Fix: path of snapshots with a relay and default URI

    When recording a snapshot to a relay without custom URI (ex:
    net://localhost vs net://localhost/custom), the snapshots end up being
    stored in ~/lttng-traces/<hostname>/snapshot-XXX instead of being inside
    the <session-name> folder like on local snapshots. We would expect the
    path to be: ~/lttng-traces/<hostname>/<session-name>/snapshot-XXX

    So there is a discrepancy between the local and remote behaviour. This
    behaviour has been there since at least v2.6, maybe earlier.

    Moreover, there is nothing that informs the user about the default
    snapshot name, so it is not possible to know where a snapshot has been
    stored.

    After parsing the URI provided by the user, we now check if a custom
    name was provided or copy the session name there. This is the same
    operation performed in _lttng_create_session_ext.

    Signed-off-by: Julien Desfossez <jdesfossez@efficios.com>
    Signed-off-by: Jérémie Galarneau <jeremie.galarneau@efficios.com>

Before this remote path for snapshot is simply broken.
This is introduced in stable-2.11.
"""
broken_snapshot_relayd_client = [
    "lttng-tools-2.7",
    "lttng-tools-2.8",
    "lttng-tools-2.9",
    "lttng-tools-2.10",
]

runtime_matrix_relayd_snapshot = []
for tup in runtime_matrix_relayd:
    if tup[0] in broken_snapshot_relayd_client:
        runtime_matrix_relayd_snapshot.append((tup + ("buggy_client",)))
    else:
        runtime_matrix_relayd_snapshot.append((tup + ("valid",)))


@pytest.mark.parametrize("version,mode", runtime_matrix_base)
def test_output_path_local(tmpdir, version, mode):

    nb_loop = 10
    datetime_regex = "[0-9]{8}-[0-9]{6}"
    trailing = "ust/{}".format(mode)

    Output_test = namedtuple("Output_test", ["name", "command", "path_regex"])

    # Prepare environment
    lttng_tools = ProjectFactory.get_precook(version)

    app_path = os.path.join(str(tmpdir), "app")

    with Run.get_runtime(tmpdir) as runtime:
        base_path = runtime.lttng_home
        tests = [
            Output_test(
                "",
                "",
                "{}/lttng-traces/auto-{}/{}".format(
                    str(base_path), datetime_regex, trailing
                ),
            ),
            Output_test(
                "test",
                "",
                "{}/lttng-traces/test-{}/{}".format(
                    str(base_path), datetime_regex, trailing
                ),
            ),
            Output_test(
                "test-20190319-120000",
                "",
                "{}/lttng-traces/test-20190319-120000-{}/{}".format(
                    str(base_path), datetime_regex, trailing
                ),
            ),
            Output_test(
                "test1",
                "--output='{}/custom_output'".format(str(base_path)),
                "{}/custom_output/{}".format(str(base_path), trailing),
            ),
            Output_test(
                "test2",
                "--set-url=file://{}/custom_output2".format(str(base_path)),
                "{}/custom_output2/{}".format(str(base_path), trailing),
            ),
        ]

        runtime.add_project(lttng_tools)

        # Make application using the runtime
        shutil.copytree(Settings.apps_gen_events_folder, app_path)
        runtime.run("make V=1", cwd=app_path)

        sessiond = utils.sessiond_spawn(runtime)

        # Create session using mi to get path and session name
        failed_tests = []
        for test in tests:
            runtime.run("lttng create {} {}".format(test.name, test.command))
            runtime.run("lttng enable-channel -u --buffers-{} channel".format(mode))
            runtime.run("lttng enable-event -u tp:tptest -c channel")
            runtime.run("lttng start")

            cmd = "./app {}".format(nb_loop)
            runtime.run(cmd, cwd=app_path)

            runtime.run("lttng stop")
            runtime.run("lttng destroy -a")
            if not utils.path_exists_regex(base_path, test.path_regex):
                failed_tests.append(test)

        runtime.subprocess_terminate(sessiond)
        if failed_tests:
            s = StringIO()
            utils.tree(base_path, s)
            pytest.fail(pformat(failed_tests) + "\n" + s.getvalue())


@pytest.mark.parametrize("version,mode", runtime_matrix_base)
def test_output_path_snapshot_local_on_create(tmpdir, version, mode):

    nb_loop = 10
    datetime_re = "[0-9]{8}-[0-9]{6}"
    snapshot_re = "snapshot-1-{}-0".format(datetime_re)
    trailing = "{}/ust/{}".format(snapshot_re, mode)

    Output_test = namedtuple("Output_test", ["name", "command", "path_regex"])

    # Prepare environment
    lttng_tools = ProjectFactory.get_precook(version)

    app_path = os.path.join(str(tmpdir), "app")
    app_sync_start = os.path.join(app_path, "sync_start")
    app_sync_end = os.path.join(app_path, "sync_end")
    shutil.copytree(Settings.apps_gen_events_folder, app_path)

    with Run.get_runtime(tmpdir) as runtime:
        base_path = runtime.lttng_home
        tests = [
            Output_test(
                "",
                "",
                "{}/lttng-traces/auto-{}/{}".format(
                    str(base_path), datetime_re, trailing
                ),
            ),
            Output_test(
                "test",
                "",
                "{}/lttng-traces/test-{}/{}".format(
                    str(base_path), datetime_re, trailing
                ),
            ),
            Output_test(
                "test-20190319-120000",
                "",
                "{}/lttng-traces/test-20190319-120000-{}/{}".format(
                    str(base_path), datetime_re, trailing
                ),
            ),
            Output_test(
                "test1",
                "--ctrl-url=file://{}/custom_output".format(str(base_path))
                + " --data-url=''",
                "{}/custom_output/{}".format(str(base_path), trailing),
            ),
            Output_test(
                "test2",
                "--set-url=file://{}/custom_output2".format(str(base_path)),
                "{}/custom_output2/{}".format(str(base_path), trailing),
            ),
        ]

        runtime.add_project(lttng_tools)

        # Make application using the runtime
        runtime.run("make V=1", cwd=app_path)

        sessiond = utils.sessiond_spawn(runtime)

        # Create session using mi to get path and session name
        failed_tests = []
        for test in tests:
            runtime.run("lttng create --snapshot {} {}".format(test.name, test.command))
            runtime.run("lttng enable-channel -u --buffers-{} channel".format(mode))
            runtime.run("lttng enable-event -u tp:tptest -c channel")
            runtime.run("lttng start")

            # Run application asynchronously since per-pid and snapshot mode
            # need the application alive at snapshot time. It does not matter
            # in per-uid buffering mode.
            cmd = "./app {} 0 {} {}".format(nb_loop, app_sync_start, app_sync_end)
            app_id = runtime.spawn_subprocess(cmd, cwd=app_path)
            utils.wait_for_file(app_sync_start)

            runtime.run("lttng snapshot record")

            utils.create_empty_file(app_sync_end)

            runtime.run("lttng stop")
            runtime.run("lttng destroy -a")
            runtime.subprocess_terminate(app_id)

            if not utils.path_exists_regex(base_path, test.path_regex):
                failed_tests.append(test)

            os.remove(app_sync_start)
            os.remove(app_sync_end)

        runtime.subprocess_terminate(sessiond)
        if failed_tests:
            s = StringIO()
            utils.tree(base_path, s)
            pytest.fail(pformat(failed_tests) + "\n" + s.getvalue())


@pytest.mark.parametrize("version,mode", runtime_matrix_base)
def test_output_path_snapshot_local_add_output(tmpdir, version, mode):
    """
    Test of output path for local snapshot output created with 'lttng snapshot
    add-output'.
    """
    nb_loop = 10
    datetime_re = "[0-9]{8}-[0-9]{6}"
    snapshot_re = "snapshot-1-{}-0".format(datetime_re)
    trailing = "{}/ust/{}".format(snapshot_re, mode)

    Output_test = namedtuple("Output_test", ["name", "command", "path_regex"])

    # Prepare environment
    lttng_tools = ProjectFactory.get_precook(version)

    app_path = os.path.join(str(tmpdir), "app")
    app_sync_start = os.path.join(app_path, "sync_start")
    app_sync_end = os.path.join(app_path, "sync_end")
    shutil.copytree(Settings.apps_gen_events_folder, app_path)

    with Run.get_runtime(tmpdir) as runtime:
        base_path = runtime.lttng_home
        tests = [
            Output_test(
                "test1",
                "--ctrl-url=file://{}/custom_output".format(str(base_path))
                + " --data-url=''",
                "{}/custom_output/{}".format(str(base_path), trailing),
            ),
            Output_test(
                "test2",
                "file://{}/custom_output2".format(str(base_path)),
                "{}/custom_output2/{}".format(str(base_path), trailing),
            ),
        ]

        runtime.add_project(lttng_tools)

        # Make application using the runtime
        runtime.run("make V=1", cwd=app_path)

        sessiond = utils.sessiond_spawn(runtime)

        # Create session using mi to get path and session name
        failed_tests = []
        for test in tests:
            runtime.run("lttng create {} --snapshot --no-output".format(test.name))
            runtime.run("lttng enable-channel -u --buffers-{} channel".format(mode))
            runtime.run("lttng enable-event -u tp:tptest -c channel")
            runtime.run(
                "lttng snapshot add-output --name snapshot-1 {}".format(test.command)
            )
            runtime.run("lttng start")

            # Run application asynchronously since per-pid and snapshot mode
            # need the application alive at snapshot time. It does not matter
            # in per-uid buffering mode.
            cmd = "./app {} 0 {} {}".format(nb_loop, app_sync_start, app_sync_end)
            app_id = runtime.spawn_subprocess(cmd, cwd=app_path)
            utils.wait_for_file(app_sync_start)

            runtime.run("lttng snapshot record")

            utils.create_empty_file(app_sync_end)

            runtime.run("lttng stop")
            runtime.run("lttng destroy -a")
            runtime.subprocess_terminate(app_id)

            if not utils.path_exists_regex(base_path, test.path_regex):
                failed_tests.append(test)

            os.remove(app_sync_start)
            os.remove(app_sync_end)

        runtime.subprocess_terminate(sessiond)
        if failed_tests:
            s = StringIO()
            utils.tree(base_path, s)
            pytest.fail(pformat(failed_tests) + "\n" + s.getvalue())


@pytest.mark.parametrize("client,server,mode", runtime_matrix_relayd)
def test_output_path_relayd(tmpdir, client, server, mode):

    nb_loop = 10

    datetime_regex = "[0-9]{8}-[0-9]{6}"
    trailing = "ust/{}".format(mode)
    hostname = socket.gethostname()

    Output_test = namedtuple("Output_test", ["name", "command", "path_regex"])

    # Prepare environment
    lttng_tools = ProjectFactory.get_precook(client)
    relay = ProjectFactory.get_precook(server)

    tools_runtime_path = os.path.join(str(tmpdir), "client")
    relayd_runtime_path = os.path.join(str(tmpdir), "relayd")
    app_path = os.path.join(str(tmpdir), "app")
    shutil.copytree(Settings.apps_gen_events_folder, app_path)

    with Run.get_runtime(tools_runtime_path) as rt_tools, Run.get_runtime(
        relayd_runtime_path
    ) as rt_relayd:
        rt_tools.add_project(lttng_tools)
        rt_relayd.add_project(relay)

        # Make application using the lttng_tools runtime
        rt_tools.run("make V=1", cwd=app_path)

        sessiond = utils.sessiond_spawn(rt_tools)
        relayd, ctrl_port, data_port, live_port = utils.relayd_spawn(rt_relayd)

        base_path = "{}/{}/{}".format(rt_relayd.lttng_home, "lttng-traces", hostname)
        tests = [
            Output_test(
                "",
                "--set-url=net://127.0.0.1:{}:{}".format(ctrl_port, data_port),
                "{}/auto-{}/{}".format(base_path, datetime_regex, trailing),
            ),
            Output_test(
                "test",
                "--set-url=net://127.0.0.1:{}:{}".format(ctrl_port, data_port),
                "{}/test-{}/{}".format(base_path, datetime_regex, trailing),
            ),
            Output_test(
                "test1",
                "--set-url=net://127.0.0.1:{}:{}/".format(ctrl_port, data_port),
                "{}/test1-{}/{}".format(base_path, datetime_regex, trailing),
            ),
            Output_test(
                "test-20190319-120000",
                "--set-url=net://127.0.0.1:{}:{}".format(ctrl_port, data_port),
                "{}/test-20190319-120000-{}/{}".format(
                    base_path, datetime_regex, trailing
                ),
            ),
            Output_test(
                "test3",
                "--set-url=net://127.0.0.1:{}:{}/custom_output".format(
                    ctrl_port, data_port
                ),
                "{}/custom_output/{}".format(base_path, trailing),
            ),
            Output_test(
                "test4",
                "--ctrl-url=tcp4://127.0.0.1:{} --data-url=tcp4://127.0.0.1:{}".format(
                    ctrl_port, data_port
                ),
                "{}/test4-{}/{}".format(base_path, datetime_regex, trailing),
            ),
            Output_test(
                "test5",
                "--ctrl-url=tcp4://127.0.0.1:{}/custom_output2 --data-url=tcp4://127.0.0.1:{}".format(
                    ctrl_port, data_port
                ),
                "{}/custom_output2/{}".format(base_path, trailing),
            ),
            Output_test(
                "test6",
                "--ctrl-url=tcp4://127.0.0.1:{} --data-url=tcp4://127.0.0.1:{}/custom_output3".format(
                    ctrl_port, data_port
                ),
                "{}/test6-{}/{}".format(base_path, datetime_regex, trailing),
            ),
        ]

        failed_tests = []
        for test in tests:
            rt_tools.run("lttng create {} {}".format(test.name, test.command))
            rt_tools.run("lttng enable-channel -u --buffers-{} channel".format(mode))
            rt_tools.run("lttng enable-event -u tp:tptest -c channel")
            rt_tools.run("lttng start")

            cmd = "./app {}".format(nb_loop)
            rt_tools.run(cmd, cwd=app_path)

            rt_tools.run("lttng stop")
            rt_tools.run("lttng destroy -a")
            if not utils.path_exists_regex(base_path, test.path_regex):
                failed_tests.append(test)

        rt_tools.subprocess_terminate(sessiond)
        rt_relayd.subprocess_terminate(relayd)
        if failed_tests:
            s = StringIO()
            utils.tree(base_path, s)
            pytest.fail(pformat(failed_tests) + "\n" + s.getvalue())


@pytest.mark.parametrize("client,server,mode,state", runtime_matrix_relayd_snapshot)
def test_output_path_snapshot_relayd_on_create(tmpdir, client, server, mode, state):

    nb_loop = 10
    datetime_re = "[0-9]{8}-[0-9]{6}"
    snapshot_re = "snapshot-1-{}-0".format(datetime_re)
    trailing = "{}/ust/{}".format(snapshot_re, mode)
    hostname = socket.gethostname()

    Output_test = namedtuple("Output_test", ["name", "command", "path_regex"])

    # Prepare environment
    lttng_tools = ProjectFactory.get_precook(client)
    relay = ProjectFactory.get_precook(server)

    app_path = os.path.join(str(tmpdir), "app")
    app_sync_start = os.path.join(app_path, "sync_start")
    app_sync_end = os.path.join(app_path, "sync_end")
    shutil.copytree(Settings.apps_gen_events_folder, app_path)

    tools_runtime_path = os.path.join(str(tmpdir), "client")
    relayd_runtime_path = os.path.join(str(tmpdir), "relayd")
    app_path = os.path.join(str(tmpdir), "app")

    with Run.get_runtime(tools_runtime_path) as rt_tools, Run.get_runtime(
        relayd_runtime_path
    ) as rt_relayd:
        rt_tools.add_project(lttng_tools)
        rt_relayd.add_project(relay)

        # Make application using the runtime
        rt_tools.run("make V=1", cwd=app_path)

        sessiond = utils.sessiond_spawn(rt_tools)
        relayd, ctrl_port, data_port, live_port = utils.relayd_spawn(rt_relayd)

        base_path = "{}/{}/{}".format(rt_relayd.lttng_home, "lttng-traces", hostname)
        path_with_session_name_tests = [
            Output_test(
                "",
                "--set-url=net://127.0.0.1:{}:{}".format(ctrl_port, data_port),
                "{}/auto-{}/{}".format(base_path, datetime_re, trailing),
            ),
            Output_test(
                "test",
                "--set-url=net://127.0.0.1:{}:{}".format(ctrl_port, data_port),
                "{}/test-{}/{}".format(base_path, datetime_re, trailing),
            ),
            Output_test(
                "test1",
                "--set-url=net://127.0.0.1:{}:{}/".format(ctrl_port, data_port),
                "{}/test1-{}/{}".format(base_path, datetime_re, trailing),
            ),
            Output_test(
                "test-20190319-120000",
                "--set-url=net://127.0.0.1:{}:{}".format(ctrl_port, data_port),
                "{}/test-20190319-120000-{}/{}".format(
                    base_path, datetime_re, trailing
                ),
            ),
            Output_test(
                "test4",
                "--ctrl-url=tcp4://127.0.0.1:{} --data-url=tcp4://127.0.0.1:{}".format(
                    ctrl_port, data_port
                ),
                "{}/test4-{}/{}".format(base_path, datetime_re, trailing),
            ),
            Output_test(
                "test6",
                "--ctrl-url=tcp4://127.0.0.1:{} --data-url=tcp4://127.0.0.1:{}/custom_output3".format(
                    ctrl_port, data_port
                ),
                "{}/test6-{}/{}".format(base_path, datetime_re, trailing),
            ),
        ]

        custom_output_tests = [
            Output_test(
                "test3",
                "--set-url=net://127.0.0.1:{}:{}/custom_output".format(
                    ctrl_port, data_port
                ),
                "{}/custom_output/{}".format(base_path, trailing),
            ),
            Output_test(
                "test5",
                "--ctrl-url=tcp4://127.0.0.1:{}/custom_output2 --data-url=tcp4://127.0.0.1:{}".format(
                    ctrl_port, data_port
                ),
                "{}/custom_output2/{}".format(base_path, trailing),
            ),
            Output_test(
                "test7",
                "--ctrl-url=tcp4://127.0.0.1:{}/custom_output4 --data-url=tcp4://127.0.0.1:{}/custom_output4".format(
                    ctrl_port, data_port
                ),
                "{}/custom_output4/{}".format(base_path, trailing),
            ),
        ]

        tests = custom_output_tests
        if state != "buggy_client":
            tests += path_with_session_name_tests

        # Create session using mi to get path and session name
        failed_tests = []
        for test in tests:
            rt_tools.run(
                "lttng create --snapshot {} {}".format(test.name, test.command)
            )
            rt_tools.run("lttng enable-channel -u --buffers-{} channel".format(mode))
            rt_tools.run("lttng enable-event -u tp:tptest -c channel")
            rt_tools.run("lttng start")

            # Run application asynchronously since per-pid and snapshot mode
            # need the application alive at snapshot time. It does not matter
            # in per-uid buffering mode.
            cmd = "./app {} 0 {} {}".format(nb_loop, app_sync_start, app_sync_end)
            app_id = rt_tools.spawn_subprocess(cmd, cwd=app_path)
            utils.wait_for_file(app_sync_start)

            rt_tools.run("lttng snapshot record")

            utils.create_empty_file(app_sync_end)

            rt_tools.run("lttng stop")
            rt_tools.run("lttng destroy -a")
            rt_tools.subprocess_terminate(app_id)

            if not utils.path_exists_regex(base_path, test.path_regex):
                failed_tests.append(test)

            os.remove(app_sync_start)
            os.remove(app_sync_end)

        rt_tools.subprocess_terminate(sessiond)
        rt_relayd.subprocess_terminate(relayd)

        if failed_tests:
            s = StringIO()
            utils.tree(base_path, s)
            pytest.fail(pformat(failed_tests) + "\n" + s.getvalue())


@pytest.mark.parametrize("client,server,mode,state", runtime_matrix_relayd_snapshot)
def test_output_path_snapshot_relayd_add_output(tmpdir, client, server, mode, state):
    """
    Test of output path for relayd snapshot output created with 'lttng snapshot
    add-output'.
    """
    nb_loop = 10
    datetime_re = "[0-9]{8}-[0-9]{6}"
    snapshot_re = "snapshot-1-{}-0".format(datetime_re)
    trailing = "{}/ust/{}".format(snapshot_re, mode)
    hostname = socket.gethostname()

    Output_test = namedtuple("Output_test", ["name", "command", "path_regex"])

    # Prepare environment
    lttng_tools = ProjectFactory.get_precook(client)
    relay = ProjectFactory.get_precook(server)

    app_path = os.path.join(str(tmpdir), "app")
    app_sync_start = os.path.join(app_path, "sync_start")
    app_sync_end = os.path.join(app_path, "sync_end")
    shutil.copytree(Settings.apps_gen_events_folder, app_path)

    tools_runtime_path = os.path.join(str(tmpdir), "client")
    relayd_runtime_path = os.path.join(str(tmpdir), "relayd")
    app_path = os.path.join(str(tmpdir), "app")

    with Run.get_runtime(tools_runtime_path) as rt_tools, Run.get_runtime(
        relayd_runtime_path
    ) as rt_relayd:
        rt_tools.add_project(lttng_tools)
        rt_relayd.add_project(relay)

        # Make application using the runtime
        rt_tools.run("make V=1", cwd=app_path)

        sessiond = utils.sessiond_spawn(rt_tools)
        relayd, ctrl_port, data_port, live_port = utils.relayd_spawn(rt_relayd)

        base_path = "{}/{}/{}".format(rt_relayd.lttng_home, "lttng-traces", hostname)
        path_with_session_name_tests = [
            Output_test(
                "test",
                "net://127.0.0.1:{}:{}".format(ctrl_port, data_port),
                "{}/test-{}/{}".format(base_path, datetime_re, trailing),
            ),
            Output_test(
                "test1",
                "net://127.0.0.1:{}:{}/".format(ctrl_port, data_port),
                "{}/test1-{}/{}".format(base_path, datetime_re, trailing),
            ),
            Output_test(
                "test-20190319-120000",
                "net://127.0.0.1:{}:{}".format(ctrl_port, data_port),
                "{}/test-20190319-120000-{}/{}".format(
                    base_path, datetime_re, trailing
                ),
            ),
            Output_test(
                "test4",
                "--ctrl-url=tcp4://127.0.0.1:{} --data-url=tcp4://127.0.0.1:{}".format(
                    ctrl_port, data_port
                ),
                "{}/test4-{}/{}".format(base_path, datetime_re, trailing),
            ),
            Output_test(
                "test6",
                "--ctrl-url=tcp4://127.0.0.1:{} --data-url=tcp4://127.0.0.1:{}/custom_output3".format(
                    ctrl_port, data_port
                ),
                "{}/test6-{}/{}".format(base_path, datetime_re, trailing),
            ),
        ]

        custom_output_tests = [
            Output_test(
                "test3",
                "net://127.0.0.1:{}:{}/custom_output".format(ctrl_port, data_port),
                "{}/custom_output/{}".format(base_path, trailing),
            ),
            Output_test(
                "test5",
                "--ctrl-url=tcp4://127.0.0.1:{}/custom_output2 --data-url=tcp4://127.0.0.1:{}".format(
                    ctrl_port, data_port
                ),
                "{}/custom_output2/{}".format(base_path, trailing),
            ),
            Output_test(
                "test7",
                "--ctrl-url=tcp4://127.0.0.1:{}/custom_output4 --data-url=tcp4://127.0.0.1:{}/custom_output4".format(
                    ctrl_port, data_port
                ),
                "{}/custom_output4/{}".format(base_path, trailing),
            ),
        ]

        tests = custom_output_tests
        if state != "buggy_client":
            tests += path_with_session_name_tests

        # Create session using mi to get path and session name
        failed_tests = []
        for test in tests:
            rt_tools.run("lttng create {} --snapshot --no-output".format(test.name))
            rt_tools.run("lttng enable-channel -u --buffers-{} channel".format(mode))
            rt_tools.run("lttng enable-event -u tp:tptest -c channel")
            rt_tools.run(
                "lttng snapshot add-output --name snapshot-1 {}".format(test.command)
            )
            rt_tools.run("lttng start")

            # Run application asynchronously since per-pid and snapshot mode
            # need the application alive at snapshot time. It does not matter
            # in per-uid buffering mode.
            cmd = "./app {} 0 {} {}".format(nb_loop, app_sync_start, app_sync_end)
            app_id = rt_tools.spawn_subprocess(cmd, cwd=app_path)
            utils.wait_for_file(app_sync_start)

            rt_tools.run("lttng snapshot record")

            utils.create_empty_file(app_sync_end)

            rt_tools.run("lttng stop")
            rt_tools.run("lttng destroy -a")
            rt_tools.subprocess_terminate(app_id)

            if not utils.path_exists_regex(base_path, test.path_regex):
                failed_tests.append(test)

            os.remove(app_sync_start)
            os.remove(app_sync_end)

        rt_tools.subprocess_terminate(sessiond)
        rt_relayd.subprocess_terminate(relayd)

        if failed_tests:
            s = StringIO()
            utils.tree(base_path, s)
            pytest.fail(pformat(failed_tests) + "\n" + s.getvalue())
