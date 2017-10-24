import pytest

import lttng_ivc.utils.ProjectFactory as ProjectFactory
import lttng_ivc.utils.runtime as Run
import lttng_ivc.settings as Settings

"""

TODO: provide kernel version check for matrix since there is upper and lower
bound to lttng-modules.

TODO:Packet sequence number. 5b3cf4f924befda843a7736daf84f8ecae5e86a4
     LTTNG_RING_BUFFER_GET_SEQ_NUM
TODO:Stream instance id. 5594698f9c8ad13e0964c67946d1867df7757dae
     LTTNG_RING_BUFFER_INSTANCE_ID


FC: Fully Compatible
BC: Feature of the smallest version number will works.

+-------------------------------------------------------+
| LTTng Modules ABI vs LTTng Tools compatibility matrix |
+-------------------------------------------------------+
| Modules / Tools  | 2.7  | 2.8  | 2.9  | 2.10          |
+------------------+------+------+------+---------------+
| 2.7              | FC   | BC   | BC   | BC            |
| 2.8              | BC   | FC   | BC   | BC            |
| 2.9              | BC   | BC   | FC   | BC            |
| 2.10             | BC   | BC   | BC   | FC            |
+------------------+------+------+------+---------------+

"""

"""
First tuple member: lttng-ust label
Second tuple member: lttng-tool label
Third tuple member: expected scenario
"""

test_matrix_regen_metadata = [
    ("lttng-modules-2.7", "lttng-tools-2.7",  "Unsupported by tools"),
    ("lttng-modules-2.7", "lttng-tools-2.8",  "Unsupported by module"),
    ("lttng-modules-2.7", "lttng-tools-2.9",  "Unsupported by module"),
    ("lttng-modules-2.7", "lttng-tools-2.10", "Unsupported by module"),
    ("lttng-modules-2.8", "lttng-tools-2.7",  "Unsupported by tools"),
    ("lttng-modules-2.8", "lttng-tools-2.8",  "Supported"),
    ("lttng-modules-2.8", "lttng-tools-2.9",  "Supported"),
    ("lttng-modules-2.8", "lttng-tools-2.10", "Supported"),
    ("lttng-modules-2.9", "lttng-tools-2.7",  "Unsupported by tools"),
    ("lttng-modules-2.9", "lttng-tools-2.8",  "Supported"),
    ("lttng-modules-2.9", "lttng-tools-2.9",  "Supported"),
    ("lttng-modules-2.9", "lttng-tools-2.10", "Supported"),
    ("lttng-modules-2.10", "lttng-tools-2.7", "Unsupported by tools"),
    ("lttng-modules-2.10", "lttng-tools-2.8", "Supported"),
    ("lttng-modules-2.10", "lttng-tools-2.9", "Supported"),
    ("lttng-modules-2.10", "lttng-tools-2.10", "Supported"),
]

test_matrix_statedump = [
    ("lttng-modules-2.7", "lttng-tools-2.7",  "Unsupported by tools"),
    ("lttng-modules-2.7", "lttng-tools-2.8",  "Unsupported by tools"),
    ("lttng-modules-2.7", "lttng-tools-2.9",  "Unsupported by module"),
    ("lttng-modules-2.7", "lttng-tools-2.10", "Unsupported by module"),
    ("lttng-modules-2.8", "lttng-tools-2.7",  "Unsupported by tools"),
    ("lttng-modules-2.8", "lttng-tools-2.8",  "Unsupported by tools"),
    ("lttng-modules-2.8", "lttng-tools-2.9",  "Unsupported by modules"),
    ("lttng-modules-2.8", "lttng-tools-2.10", "Unsupported by modules"),
    ("lttng-modules-2.9", "lttng-tools-2.7",  "Unsupported by tools"),
    ("lttng-modules-2.9", "lttng-tools-2.8",  "Unsupported by tools"),
    ("lttng-modules-2.9", "lttng-tools-2.9",  "Supported"),
    ("lttng-modules-2.9", "lttng-tools-2.10", "Supported"),
    ("lttng-modules-2.10", "lttng-tools-2.7", "Unsupported by tools"),
    ("lttng-modules-2.10", "lttng-tools-2.8", "Unsupported by tools"),
    ("lttng-modules-2.10", "lttng-tools-2.9", "Supported"),
    ("lttng-modules-2.10", "lttng-tools-2.10", "Supported"),
]

test_matrix_starglobing = [
    ("lttng-modules-2.7", "lttng-tools-2.7",  "Unsupported by tools"),
    ("lttng-modules-2.7", "lttng-tools-2.8",  "Unsupported by tools"),
    ("lttng-modules-2.7", "lttng-tools-2.9",  "Unsupported by tools"),
    ("lttng-modules-2.7", "lttng-tools-2.10", "Unsupported by module"),
    ("lttng-modules-2.8", "lttng-tools-2.7",  "Unsupported by tools"),
    ("lttng-modules-2.8", "lttng-tools-2.8",  "Unsupported by tools"),
    ("lttng-modules-2.8", "lttng-tools-2.9",  "Unsupported by tools"),
    ("lttng-modules-2.8", "lttng-tools-2.10", "Unsupported by modules"),
    ("lttng-modules-2.9", "lttng-tools-2.7",  "Unsupported by tools"),
    ("lttng-modules-2.9", "lttng-tools-2.8",  "Unsupported by tools"),
    ("lttng-modules-2.9", "lttng-tools-2.9",  "Unsupported by tools"),
    ("lttng-modules-2.9", "lttng-tools-2.10", "Unsupported by modules"),
    ("lttng-modules-2.10", "lttng-tools-2.7", "Unsupported by tools"),
    ("lttng-modules-2.10", "lttng-tools-2.8", "Unsupported by tools"),
    ("lttng-modules-2.10", "lttng-tools-2.9", "Unsupported by tools"),
    ("lttng-modules-2.10", "lttng-tools-2.10", "Supported"),
]


runtime_matrix_regen_metadata = []
runtime_matrix_statedump = []
runtime_matrix_starglobing = []

if not Settings.test_only:
    runtime_matrix_regen_metadata = test_matrix_regen_metadata
    runtime_matrix_statedump = test_matrix_statedump
    runtime_matrix_starglobing = test_matrix_starglobing
else:
    for tup in test_matrix_regen_metadata:
        if (tup[0] in Settings.test_only or tup[1] in
                Settings.test_only):
            runtime_matrix_regen_metadata.append(tup)
    for tup in test_matrix_statedump:
        if (tup[0] in Settings.test_only or tup[1] in
                Settings.test_only):
            runtime_matrix_statedump.append(tup)
    for tup in test_matrix_starglobing:
        if (tup[0] in Settings.test_only or tup[1] in
                Settings.test_only):
            runtime_matrix_starglobing.append(tup)


@pytest.mark.parametrize("modules_label,tools_label,outcome", runtime_matrix_regen_metadata)
def test_modules_regen_metadata(tmpdir, modules_label, tools_label, outcome):
    pytest.xfail("Not implemented yet. Need to perform version checking for lttng-modules validity")
    modules = ProjectFactory.get_precook(modules_label)
    tools = ProjectFactory.get_precook(tools_label)
    runtime = Run.Runtime(str(tmpdir))
    runtime.add_project(modules)
    runtime.add_project(tools)


@pytest.mark.parametrize("modules_label,tools_label,outcome", runtime_matrix_statedump)
def test_modules_statedump(tmpdir, modules_label, tools_label, outcome):
    pytest.xfail("Not implemented yet. Need to perform version checking for lttng-modules validity")
    modules = ProjectFactory.get_precook(modules_label)
    tools = ProjectFactory.get_precook(tools_label)
    runtime = Run.Runtime(str(tmpdir))
    runtime.add_project(modules)
    runtime.add_project(tools)


@pytest.mark.parametrize("modules_label,tools_label,outcome", runtime_matrix_starglobing)
def test_modules_starglobing(tmpdir, modules_label, tools_label, outcome):
    pytest.xfail("Not implemented yet. Need to perform version checking for lttng-modules validity")
    modules = ProjectFactory.get_precook(modules_label)
    tools = ProjectFactory.get_precook(tools_label)
    runtime = Run.Runtime(str(tmpdir))
    runtime.add_project(modules)
    runtime.add_project(tools)
