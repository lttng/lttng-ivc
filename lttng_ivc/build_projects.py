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

import os
import sys
import logging

import yaml

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(dir_path, ".."))

import utils.ProjectFactory as ProjectFactory
import settings as Settings

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger('project.cache_builder')

projects_under_test = {}

# Fetch the project under test
# We start with the complete set and substract deprecated projects
with open(Settings.run_configuration_file, 'r') as stream:
    projects_under_test = set(yaml.load(stream, Loader=yaml.FullLoader))

projects_under_test = projects_under_test.difference(Settings.projects_deprecated)

# Prebuild all projects
for key in projects_under_test:
    _logger.info('Preparing and building %s', key)
    ProjectFactory.get_precook(key)
    _logger.info('Done: %s', key)
