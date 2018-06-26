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

import lttng_ivc.utils.ProjectFactory as ProjectFactory
import lttng_ivc.utils.utils as utils
import lttng_ivc.utils.runtime as Run
import lttng_ivc.settings as Settings

"""
Backward compatibility testing for lttng-ctl
"""

"""
First tuple member: lttng-tools label from which the client (lttng bin) is sourced
Second tuple member: lttng-tools label for runtime sessiond and lttng-ctl
Third tuple member: expected scenario
"""

test_matrix_basic_listing = [
    ("lttng-tools-2.7", "lttng-tools-2.7",   "Success"),
    ("lttng-tools-2.7", "lttng-tools-2.8",   "Success"),
    ("lttng-tools-2.7", "lttng-tools-2.9",   "Success"),
    ("lttng-tools-2.7", "lttng-tools-2.10",  "Success"),
    ("lttng-tools-2.7", "lttng-tools-2.11",  "Success"),
    ("lttng-tools-2.8", "lttng-tools-2.7",   "Missing symbol"),
    ("lttng-tools-2.8", "lttng-tools-2.8",   "Success"),
    ("lttng-tools-2.8", "lttng-tools-2.9",   "Success"),
    ("lttng-tools-2.8", "lttng-tools-2.10",  "Success"),
    ("lttng-tools-2.8", "lttng-tools-2.11",  "Success"),
    ("lttng-tools-2.9", "lttng-tools-2.7",   "Missing symbol"),
    ("lttng-tools-2.9", "lttng-tools-2.8",   "Missing symbol"),
    ("lttng-tools-2.9", "lttng-tools-2.9",   "Success"),
    ("lttng-tools-2.9", "lttng-tools-2.10",  "Success"),
    ("lttng-tools-2.9", "lttng-tools-2.11",  "Success"),
    ("lttng-tools-2.10", "lttng-tools-2.7",  "Missing symbol"),
    ("lttng-tools-2.10", "lttng-tools-2.8",  "Missing symbol"),
    ("lttng-tools-2.10", "lttng-tools-2.9",  "Missing symbol"),
    ("lttng-tools-2.10", "lttng-tools-2.10", "Success"),
    ("lttng-tools-2.10", "lttng-tools-2.11", "Success"),
    ("lttng-tools-2.11", "lttng-tools-2.7",  "Missing symbol"),
    ("lttng-tools-2.11", "lttng-tools-2.8",  "Missing symbol"),
    ("lttng-tools-2.11", "lttng-tools-2.9",  "Missing symbol"),
    ("lttng-tools-2.11", "lttng-tools-2.10", "Missing symbol"),
    ("lttng-tools-2.11", "lttng-tools-2.11", "Success"),

]

runtime_matrix_basic_listing = []

if not Settings.test_only:
    runtime_matrix_basic_listing = test_matrix_basic_listing
else:
    for tup in test_matrix_basic_listing:
        if (tup[0] in Settings.test_only or tup[1] in
                Settings.test_only):
            runtime_matrix_basic_listing.append(tup)

@pytest.mark.parametrize("client_label,tools_label,outcome", runtime_matrix_basic_listing)
def test_tools_liblttng_ctl_vs_sessiond_basic_listing(tmpdir, client_label, tools_label, outcome):

    # Prepare environment
    client = ProjectFactory.get_precook(client_label)
    tools = ProjectFactory.get_precook(tools_label)

    tools_runtime_path = os.path.join(str(tmpdir), "tools")

    lttng_client = os.path.join(client.installation_path, "bin/lttng")

    with Run.get_runtime(tools_runtime_path) as runtime_tools:
        runtime_tools.add_project(tools)

        sessiond = utils.sessiond_spawn(runtime_tools)

        cp, out, err = runtime_tools.run('{} create trace'.format(lttng_client), check_return=False, ld_debug=True)
        if outcome == "Missing symbol":
            assert(cp.returncode != 0)
            assert(utils.file_contains(err, "Missing symbol"))
            return

        assert(cp.returncode == 0)

        runtime_tools.run('{} enable-event -u tp:tptest'.format(lttng_client))
        runtime_tools.run('{} start'.format(lttng_client))

        # Stop tracing
        runtime_tools.run('{} stop'.format(lttng_client))
        runtime_tools.run('{} destroy -a'.format(lttng_client))
        cp = runtime_tools.subprocess_terminate(sessiond)
        if cp.returncode != 0:
            pytest.fail("Sessiond return code")
