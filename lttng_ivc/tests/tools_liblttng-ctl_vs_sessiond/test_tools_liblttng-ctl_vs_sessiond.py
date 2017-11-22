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
    ("lttng-tools-2.8", "lttng-tools-2.7",   "Missing symbol"),
    ("lttng-tools-2.8", "lttng-tools-2.8",   "Success"),
    ("lttng-tools-2.8", "lttng-tools-2.9",   "Success"),
    ("lttng-tools-2.8", "lttng-tools-2.10",  "Success"),
    ("lttng-tools-2.9", "lttng-tools-2.7",   "Missing symbol"),
    ("lttng-tools-2.9", "lttng-tools-2.8",   "Missing symbol"),
    ("lttng-tools-2.9", "lttng-tools-2.9",   "Success"),
    ("lttng-tools-2.9", "lttng-tools-2.10",  "Success"),
    ("lttng-tools-2.10", "lttng-tools-2.7",  "Missing symbol"),
    ("lttng-tools-2.10", "lttng-tools-2.8",  "Missing symbol"),
    ("lttng-tools-2.10", "lttng-tools-2.9",  "Missing symbol"),
    ("lttng-tools-2.10", "lttng-tools-2.10", "Success"),
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

        cp, out, err = runtime_tools.run('{} create trace'.format(lttng_client), check_return=False)
        if outcome == "Missing symbol":
            assert(cp.returncode != 0)
            assert(utils.file_contains(err, "Missing symbol"))
            return

        assert(cp.returncode == 0)

        runtime_tools.run('lttng enable-event -u tp:tptest')
        runtime_tools.run('lttng start')

        # Stop tracing
        runtime_tools.run('lttng stop')
        runtime_tools.run('lttng destroy -a')
        cp = runtime_tools.subprocess_terminate(sessiond)
        if cp.returncode != 0:
            pytest.fail("Sessiond return code")
