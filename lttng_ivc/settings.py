# All tests are run if empty
import os

test_only = {"lttng-ust-2.7"}

configuration_file = os.path.dirname(os.path.abspath(__file__)) + "/config.yaml"
run_configuration_file = os.path.dirname(os.path.abspath(__file__)) + "/run_configuration.yaml"

projects_cache_folder = os.path.dirname(os.path.abspath(__file__)) + "/runtime/projects_cache"
git_remote_folder = os.path.dirname(os.path.abspath(__file__)) + "/runtime/git_remote"
