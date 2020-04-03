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
import subprocess
import platform
import shutil
import os

import lttng_ivc.utils.ProjectFactory as ProjectFactory
import lttng_ivc.utils.utils as utils
import lttng_ivc.utils.runtime as Run
import lttng_ivc.settings as Settings

"""
FC: Fully Compatible
I: Incompatible

+------------------------------------------------------------------------+
|                 LTTng consumer daemon vs LTTng session daemon          |
+--------------------------+------------+------------+------------+------+-----+-----+
| Consumerd/Sessiond       | 2.7        | 2.8        | 2.9        | 2.10 | 2.11| 2.12|
+--------------------------+------------+------------+------------+------+-----+-----+
| 2.7                      | FC         | I          | I          | I    | I   | I   |
| 2.8                      | I          | FC         | I          | I    | I   | I   |
| 2.9                      | I          | I          | FC         | I    | I   | I   |
| 2.10                     | I          | I          | I          | FC   | I   | I   |
| 2.11                     | I          | I          | I          | I    | FC  | I   |
| 2.12                     | I          | I          | I          | I    | I   | FC  |
+--------------------------+------------+------------+------------+------+-----+-----+

"""

test_matrix_consumerd = [
    ("lttng-tools-2.7", "lttng-tools-2.7", True),
    ("lttng-tools-2.7", "lttng-tools-2.8", False),
    ("lttng-tools-2.7", "lttng-tools-2.9", False),
    ("lttng-tools-2.7", "lttng-tools-2.10", False),
    ("lttng-tools-2.7", "lttng-tools-2.11", False),
    ("lttng-tools-2.7", "lttng-tools-2.12", False),
    ("lttng-tools-2.8", "lttng-tools-2.7", False),
    ("lttng-tools-2.8", "lttng-tools-2.8", True),
    ("lttng-tools-2.8", "lttng-tools-2.9", True),
    ("lttng-tools-2.8", "lttng-tools-2.10", False),
    ("lttng-tools-2.8", "lttng-tools-2.11", False),
    ("lttng-tools-2.8", "lttng-tools-2.12", False),
    ("lttng-tools-2.9", "lttng-tools-2.7", False),
    ("lttng-tools-2.9", "lttng-tools-2.8", True),
    ("lttng-tools-2.9", "lttng-tools-2.9", True),
    ("lttng-tools-2.9", "lttng-tools-2.10", False),
    ("lttng-tools-2.9", "lttng-tools-2.11", False),
    ("lttng-tools-2.9", "lttng-tools-2.12", False),
    ("lttng-tools-2.10", "lttng-tools-2.7", False),
    ("lttng-tools-2.10", "lttng-tools-2.8", False),
    ("lttng-tools-2.10", "lttng-tools-2.9", False),
    ("lttng-tools-2.10", "lttng-tools-2.10", True),
    ("lttng-tools-2.10", "lttng-tools-2.11", False),
    ("lttng-tools-2.10", "lttng-tools-2.12", False),
    ("lttng-tools-2.11", "lttng-tools-2.7", False),
    ("lttng-tools-2.11", "lttng-tools-2.8", False),
    ("lttng-tools-2.11", "lttng-tools-2.9", False),
    ("lttng-tools-2.11", "lttng-tools-2.10", False),
    ("lttng-tools-2.11", "lttng-tools-2.11", True),
    ("lttng-tools-2.11", "lttng-tools-2.12", False),
    ("lttng-tools-2.12", "lttng-tools-2.7", False),
    ("lttng-tools-2.12", "lttng-tools-2.8", False),
    ("lttng-tools-2.12", "lttng-tools-2.9", False),
    ("lttng-tools-2.12", "lttng-tools-2.10", False),
    ("lttng-tools-2.12", "lttng-tools-2.11", False),
    ("lttng-tools-2.12", "lttng-tools-2.12", True),
]

runtime_matrix_consumerd = Settings.generate_runtime_test_matrix(
    test_matrix_consumerd, [0, 1]
)


@pytest.mark.parametrize("consumerd_l,tools_l,should_work", runtime_matrix_consumerd)
def test_consumerd_vs_sessiond(tmpdir, consumerd_l, tools_l, should_work):
    """
    Scenario:
        Point a lttng-tools to a consumerd of another version and see what
        happen. We do not expect anything good to come out of this since for
        now lttng-tools(2.10) no versioning exist between sessiond and
        consumerd.
    """

    nb_event = 100

    consumerd = ProjectFactory.get_precook(consumerd_l)
    tools = ProjectFactory.get_precook(tools_l)
    babeltrace = ProjectFactory.get_precook(Settings.default_babeltrace)

    app_path = os.path.join(str(tmpdir), "app")

    replacement_consumerd = utils.find_file(
        consumerd.installation_path, "lttng-consumerd"
    )
    assert replacement_consumerd

    c_dict = {"32bit": "--consumerd32-path", "64bit": "--consumerd64-path"}
    platform_type = platform.architecture()[0]

    sessiond_opt_args = "{}={}".format(c_dict[platform_type], replacement_consumerd)

    with Run.get_runtime(str(tmpdir)) as runtime:
        runtime.add_project(tools)
        runtime.add_project(babeltrace)

        shutil.copytree(Settings.apps_gen_events_folder, app_path)
        runtime.run("make V=1", cwd=app_path)

        utils.sessiond_spawn(runtime, sessiond_opt_args)

        # Consumer is only called on channel creation
        runtime.run("lttng create")
        try:
            runtime.run("lttng enable-event -u tp:tptest", timeout=5)
            runtime.run("lttng start", timeout=5)

            # Run application
            cmd = "./app {}".format(100)
            runtime.run(cmd, cwd=app_path)

            runtime.run("lttng stop", timeout=5)
            runtime.run("lttng destroy -a", timeout=5)
            cp, cp_out, cp_err = runtime.run("babeltrace {}".format(runtime.lttng_home))
            assert utils.line_count(cp_out) == nb_event
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            if should_work:
                raise e
            else:
                # Expecting some error
                return
        if not should_work:
            raise Exception("Supposed to fail")
