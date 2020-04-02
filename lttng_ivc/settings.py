import os
import yaml
import itertools
import pytest
import _pytest

test_only = {}

projects_deprecated = {"lttng-ust-2.7", "lttng-modules-2.7", "lttng-tools-2.7",
                       "lttng-ust-2.8", "lttng-modules-2.8", "lttng-tools-2.8",
                       "lttng-ust-2.9", "lttng-modules-2.9", "lttng-tools-2.9"}
projects_under_test = {}

base_dir = os.path.dirname(os.path.abspath(__file__))

configuration_file = os.path.join(base_dir, "config.yaml")
run_configuration_file = os.path.join(base_dir, "run_configuration.yaml")

projects_cache_folder = os.path.join(base_dir, "runtime/projects_cache")
git_remote_folder = os.path.join(base_dir, "runtime/git_remote")

apps_folder = os.path.join(base_dir, "apps")
apps_gen_events_folder = os.path.join(apps_folder, "gen_ust_events")
apps_preload_provider_folder = os.path.join(apps_folder, "preload_provider")
apps_jul_1 = os.path.join(apps_folder, "jul-1.0")
apps_jul_2 = os.path.join(apps_folder, "jul-2.0")
apps_python = os.path.join(apps_folder, "python")

traces_folder = os.path.join(base_dir, "traces")
trace_lost_packet = os.path.join(traces_folder, "packet_lost_2_stream")

# Used for checksum validation
project_py_file_location = os.path.join(base_dir, "utils/project.py")

tmp_object_prefix = "lttng-ivc-"

default_babeltrace = "babeltrace-1.5"


lttng_test_procfile = "/proc/lttng-test-filter-event"

save_ext = ".lttng"

mi_xsd_file_name = ['mi_lttng.xsd', 'mi-lttng-3.0.xsd', 'mi-lttng-4.0.xsd']

# Fetch the project under test
# We start with the complete set and substract deprecated projects
with open(run_configuration_file, 'r') as stream:
    projects_under_test = set(yaml.load(stream, Loader=yaml.FullLoader))

projects_under_test = projects_under_test.difference(projects_deprecated)

def generate_runtime_test_matrix(base_matrix, indexes_of_criteria_list):
    result_matrix = []
    for tup in base_matrix:
        criteria = []
        for index in indexes_of_criteria_list:
            crit = tup[index]
            if isinstance(crit, (list, tuple)):
                # Single level flattening
                for i in crit:
                    if isinstance(i, _pytest.mark.structures.MarkDecorator):
                        # This is necessary due to the presence of
                        # MarkDecorator allowing identification of flaky test
                        # etc. In such case the first "member" of our tuple
                        # actually contains all the criteria
                        continue
                    criteria.append(i)
            else:
                criteria.append(crit)

        if any(i in projects_deprecated for i in criteria):
            continue
        if test_only and not any(i in test_only for i in criteria):
            continue
        result_matrix.append(tup)
    return result_matrix
