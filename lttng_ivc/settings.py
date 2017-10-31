# All tests are run if empty
import os

test_only = {}

base_dir = os.path.dirname(os.path.abspath(__file__))

configuration_file = os.path.join(base_dir, "config.yaml")
run_configuration_file = os.path.join(base_dir, "run_configuration.yaml")

projects_cache_folder = os.path.join(base_dir, "runtime/projects_cache")
git_remote_folder = os.path.join(base_dir, "runtime/git_remote")

apps_folder = os.path.join(base_dir, "apps")
apps_gen_events_folder = os.path.join(apps_folder, "gen_ust_events")
apps_preload_provider_folder = os.path.join(apps_folder, "preload_provider")

# Used for checksum validation
project_py_file_location = os.path.join(base_dir, "utils/project.py")

tmp_object_prefix = "lttng-ivc-"

default_babeltrace = "babeltrace-1.5"
