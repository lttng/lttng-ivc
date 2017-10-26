# All tests are run if empty
import os

test_only = {}

configuration_file = os.path.dirname(os.path.abspath(__file__)) + "/config.yaml"
run_configuration_file = os.path.dirname(os.path.abspath(__file__)) + "/run_configuration.yaml"

projects_cache_folder = os.path.dirname(os.path.abspath(__file__)) + "/runtime/projects_cache"
git_remote_folder = os.path.dirname(os.path.abspath(__file__)) + "/runtime/git_remote"
app_folder = os.path.dirname(os.path.abspath(__file__)) + "/runtime/git_remote"
apps_folder = os.path.dirname(os.path.abspath(__file__)) + "/apps"
apps_gen_events_folder = os.path.join(apps_folder, "gen_ust_events")
apps_preload_provider_folder = os.path.join(apps_folder, "preload_provider")

tmp_object_prefix = "lttng-ivc-"

default_babeltrace = "babeltrace-1.5"
