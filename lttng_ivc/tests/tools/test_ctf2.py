#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: 2025 Kienan Stewart <kstewart@efficios.com>
# SPDX-License-Identifier: GPL-2.0-only
#

import pathlib
import os
import shutil
import signal
import subprocess
import time
import socket

import pytest

import lttng_ivc.utils.ProjectFactory as ProjectFactory
import lttng_ivc.utils.utils as utils
import lttng_ivc.utils.runtime as Run
import lttng_ivc.settings as Settings

"""
Validate the behaviour of sessions configured with CTF2 against previous
versions of the relayd from lttng-tools.

CTF 2 support is available as an experimental feature in stable-2.14,
activated by setting the environment variable "LTTNG_EXPERIMENTAL_FORCE_CTF_2=1"

However, in stable-2.14 CTF2 network streaming is not supported and session creation
should fail.

The expected behaviour with stable-2.15 is that CTF 2 will be activated per-session,
and will be the default CTF version for sessions.

FC: Fully Compatible
I: Incompatible
UN: Untested

+-------------------------------------------------+
| LTTng relayd vs. LTTng consumerd - CTF2         |
+---------------------+------+------+------+------+
|           Consumerd | 2.13 | 2.14 | 2.15 | 2.16 |
| Relayd              |      |      |      |      |
+---------------------+------+------+------+------+
| 2.13                | I    | I    | I    | I    |
| 2.14                | I    | I    | I    | I    |
| 2.15                | I    | I    | FC   | FC   |
| 2.16                | I    | I    | FC   | FC   |
+---------------------+------+------+------+------+
"""

test_ctf2_matrix = [
    # (relayd via tools, consumerd via tools)
    pytest.param(
        "lttng-tools-2.13",
        "lttng-tools-2.13",
        marks=pytest.mark.xfail(reason="Relayd and sessiond do not support CTF2"),
    ),
    pytest.param(
        "lttng-tools-2.13",
        "lttng-tools-2.14",
        marks=pytest.mark.xfail(reason="Relayd does not support CTF2"),
    ),
    pytest.param(
        "lttng-tools-2.13",
        "lttng-tools-2.15",
        marks=pytest.mark.xfail(reason="Relayd does not support CTF2"),
    ),
    pytest.param(
        "lttng-tools-2.13",
        "lttng-tools-2.16",
        marks=pytest.mark.xfail(reason="Relayd does not support CTF2"),
    ),
    pytest.param(
        "lttng-tools-2.13",
        "lttng-tools-master",
        marks=pytest.mark.xfail(reason="Relayd does not support CTF2"),
    ),
    pytest.param(
        "lttng-tools-2.14",
        "lttng-tools-2.13",
        marks=pytest.mark.xfail(reason="Sessiond does not support CTF2"),
    ),
    pytest.param(
        "lttng-tools-2.14",
        "lttng-tools-2.14",
        marks=pytest.mark.xfail(reason="Sessiond does not support CTF2 via network"),
    ),
    pytest.param(
        "lttng-tools-2.14",
        "lttng-tools-2.15",
        marks=pytest.mark.xfail(reason="Sessiond does not support CTF2 via network"),
    ),
    pytest.param(
        "lttng-tools-2.14",
        "lttng-tools-2.16",
        marks=pytest.mark.xfail(reason="Sessiond does not support CTF2 via network"),
    ),
    pytest.param(
        "lttng-tools-2.14",
        "lttng-tools-master",
        marks=pytest.mark.xfail(reason="Sessiond does not support CTF2 via network"),
    ),
    pytest.param(
        "lttng-tools-2.15",
        "lttng-tools-2.13",
        marks=pytest.mark.xfail(reason="Sessiond does not support CTF2"),
    ),
    pytest.param(
        "lttng-tools-2.15",
        "lttng-tools-2.14",
        marks=pytest.mark.xfail(reason="Sessiond does not support CTF2 via network"),
    ),
    pytest.param(
        "lttng-tools-2.15",
        "lttng-tools-2.15",
    ),
    pytest.param(
        "lttng-tools-2.15",
        "lttng-tools-2.16",
    ),
    pytest.param(
        "lttng-tools-2.15",
        "lttng-tools-master",
    ),
    pytest.param(
        "lttng-tools-2.16",
        "lttng-tools-2.13",
        marks=pytest.mark.xfail(reason="Sessiond does not support CTF2"),
    ),
    pytest.param(
        "lttng-tools-2.16",
        "lttng-tools-2.14",
        marks=pytest.mark.xfail(reason="Sessiond does not support CTF2 via network"),
    ),
    pytest.param(
        "lttng-tools-2.16",
        "lttng-tools-2.15",
    ),
    pytest.param(
        "lttng-tools-2.16",
        "lttng-tools-2.16",
    ),
    pytest.param(
        "lttng-tools-2.16",
        "lttng-tools-master",
    ),
    pytest.param(
        "lttng-tools-master",
        "lttng-tools-2.13",
        marks=pytest.mark.xfail(reason="Sessiond does not support CTF2"),
    ),
    pytest.param(
        "lttng-tools-master",
        "lttng-tools-2.14",
        marks=pytest.mark.xfail(reason="Sessiond does not support CTF2 via network"),
    ),
    pytest.param(
        "lttng-tools-master",
        "lttng-tools-2.15",
    ),
    pytest.param(
        "lttng-tools-master",
        "lttng-tools-2.16",
    ),
    pytest.param(
        "lttng-tools-master",
        "lttng-tools-master",
    ),
]


@pytest.mark.parametrize(
    "relayd_version,consumerd_version",
    Settings.generate_runtime_test_matrix(test_ctf2_matrix, [0, 1]),
)
def test_ctf2_relayd_vs_consumerd(tmpdir, relayd_version, consumerd_version):
    """ """
    nb_loop = 100
    app_path = os.path.join(str(tmpdir), "app")
    babeltrace = ProjectFactory.get_precook(Settings.default_babeltrace)
    consumerd = ProjectFactory.get_precook(consumerd_version)
    consumerd_runtime_path = os.path.join(str(tmpdir), "consumerd")
    consumerd_extra_env = {}
    if consumerd_version.split("-")[2] in ["stable-2.14"]:
        consumerd_extra_env["LTTNG_EXPERIMENTAL_FORCE_CTF_2"] = "1"

    relayd = ProjectFactory.get_precook(relayd_version)
    relayd_runtime_path = os.path.join(str(tmpdir), "relayd")
    relayd_extra_env = {}
    if relayd_version.split("-")[2] in ["stable-2.14"]:
        relayd_extra_env["LTTNG_EXPERIMENTAL_FORCE_CTF_2"] = "1"

    with Run.get_runtime(consumerd_runtime_path) as consumerd_runtime, Run.get_runtime(
        relayd_runtime_path
    ) as relayd_runtime:
        consumerd_runtime.add_project(consumerd)
        if "urcu" in consumerd.dependencies:
            consumerd_runtime.add_project(consumerd.dependencies["urcu"])

        relayd_runtime.add_project(relayd)
        if "urcu" in relayd.dependencies:
            relayd_runtime.add_project(relayd.dependencies["urcu"])

        # Make application using the ust runtime
        shutil.copytree(Settings.apps_gen_events_folder, app_path)
        consumerd_runtime.run(["make", "V=1"], cwd=app_path)

        # Spawn the relayd
        relayd, ctrl_port, data_port, live_port = utils.relayd_spawn(
            relayd_runtime, extra_env=relayd_extra_env
        )

        # Spawn the sessiond
        sessiond = utils.sessiond_spawn(
            consumerd_runtime, extra_env=consumerd_extra_env
        )
        consumerd_runtime.run(
            [
                "lttng",
                "create",
                "--set-url=net://localhost:{}:{}".format(ctrl_port, data_port),
                "trace",
            ]
        )
        consumerd_runtime.run(["lttng", "enable-event", "-u", "tp:tptest"])
        consumerd_runtime.run(["lttng", "start"])
        consumerd_runtime.run(["./app", str(nb_loop)], cwd=app_path)
        consumerd_runtime.run(["lttng", "stop"])
        consumerd_runtime.run(["lttng", "destroy", "-a", "--no-wait"])
        consumerd_runtime.subprocess_terminate(sessiond)
        relayd_runtime.subprocess_terminate(relayd)

        # Read trace with babeltrace and check for event count via number of line
        cmd = "babeltrace2 {}".format(relayd_runtime.lttng_home)
        cp_process, cp_out, cp_err = relayd_runtime.run(cmd)
        assert utils.line_count(cp_out) == nb_loop

        # Confirm that the saved trace is CTF 2
        # 1. Find the directory that contains the metadata
        at_least_one_metadata_file = False
        for metadata_file in pathlib.Path(relayd_runtime.lttng_home).glob(
            "**/metadata"
        ):
            at_least_one_metadata_file = True
            # 2. babeltrace2 query src.ctf.fs metadata-info -p 'path="xxx"'
            trace_dir = metadata_file.parents[0]
            process, out, err = relayd_runtime.run(
                [
                    "babeltrace2",
                    "query",
                    "src.ctf.fs",
                    "metadata-info",
                    "-p",
                    'path="{}"'.format(str(trace_dir)),
                ]
            )
            # 3. Output should contain:
            #   - "is-packetized: no"
            assert utils.file_contains(out, ["is-packetized: no"])
            assert not utils.file_contains(out, ["text: /* CTF 1.8 */"])
            #   - '"version": 2'
            assert utils.file_contains(out, ['  "version": 2'])

        assert at_least_one_metadata_file
