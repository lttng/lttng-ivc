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
import shutil
import git
import subprocess
import logging
import lttng_ivc.settings as Settings
import pprint
import magic

from lttng_ivc.utils.utils import sha256_checksum
from lttng_ivc.utils.utils import find_dir, find_file

_logger = logging.getLogger('project')

class Project(object):

    def __init__(self, label, git_path, sha1, tmpdir):
        self.label = label
        self.git_path = git_path
        self.sha1 = sha1

        """ Custom configure flags in the for of ['-x', 'arg']"""
        self.custom_configure_flags = []
        ccache = shutil.which("ccache")
        if ccache is not None:
            self.custom_configure_flags.append("CC={} gcc".format(ccache))
            self.custom_configure_flags.append("CXX={} g++".format(ccache))

        self.custom_configure_flags.append("CFLAGS=-g -O0")

        # A collection of Project dependencies
        self.dependencies = {}
        # used for project cache and pickle validation
        self._immutable = False
        self._py_file_checksum = sha256_checksum(Settings.project_py_file_location)

        # State
        self.isBuilt = False
        self.isConfigured = False
        self.isInstalled = False
        self.skip = False

        self.basedir = tmpdir
        self.log_path = os.path.join(tmpdir, "log")
        self.source_path = os.path.join(tmpdir, "source")
        self.installation_path = os.path.join(tmpdir, "install")

        if os.path.isdir(self.basedir):
            # Perform cleanup since it should not happen
            shutil.rmtree(self.basedir)

        os.makedirs(self.log_path)
        os.makedirs(self.source_path)
        os.makedirs(self.installation_path)
        os.makedirs(os.path.join(self.installation_path, "include"))
        os.makedirs(os.path.join(self.installation_path, "lib"))

        self.special_env_variables = {}

        # Init the repo for work
        self.checkout()
        self.bootstrap()

    def add_special_env_variable(self, key, value):
        if key in self.special_env_variables:
            _logger.warning("{} Special var {} is already defined".format(
                                self.label, key))
            raise Exception("Multiple definition of a special environment variable")
        self.special_env_variables[key] = value

    def get_cppflags(self):
        cppflags = ["-I{}/include".format(self.installation_path)]
        for key, dep in self.dependencies.items():
            cppflags.append(dep.get_cppflags())

        return " ".join(cppflags)

    def get_ldflags(self):
        ldflags = ["-L{}/lib".format(self.installation_path)]
        for key, dep in self.dependencies.items():
            ldflags.append(dep.get_ldflags())
        return " ".join(ldflags)

    def get_ld_library_path(self):
        library_path = ["{}/lib".format(self.installation_path)]
        for key, dep in self.dependencies.items():
            library_path.append(dep.get_ld_library_path())
        return ":".join(library_path)

    def get_pkg_config_path(self):
        pkgconfig_paths = ["{}/lib/pkgconfig".format(self.installation_path)]
        for key, dep in self.dependencies.items():
            pkgconfig_paths.append(dep.get_pkg_config_path())
        return ":".join(pkgconfig_paths)

    def get_bin_path(self):
        bin_path = ["{}/bin".format(self.installation_path)]
        for key, dep in self.dependencies.items():
            bin_path.append(dep.get_bin_path())
        return ":".join(bin_path)

    def get_env(self):
        """Modify environment to reflect dependency"""
        env_var = {"CPPFLAGS": (self.get_cppflags(), " "),
                   "LDFLAGS": (self.get_ldflags(), " "),
                   "LD_LIBRARY_PATH": (self.get_ld_library_path(), ":"),
                   "PKG_CONFIG_PATH": (self.get_pkg_config_path(), ":"),
                   }

        env = os.environ.copy()

        for var, value in self.special_env_variables.items():
            if var in env:
                if var == "LD_LIBRARY_PATH":
                    env[var] = ":".join([env[var], value])
                elif var == "CPPFLAGS" or var == "CFLAGS" or var == "LDFLAGS":
                    env[var] = " ".join([env[var], value])
                else:
                    _logger.warning("{} Special var {} is already defined".format(
                                    self.label, var))
                    raise Exception("Multiple definition of a special environment variable")
            else:
                env[var] = value

        for key, dep in self.dependencies.items():
            # Extra space just in case
            for var, value in dep.special_env_variables.items():
                if var in env:
                    # Raise for now since no special cases is known
                    _logger.warning("{} Special var {} is already defined".format(
                                self.label, var))
                    raise Exception("Multiple definition of a special environment variable")
                else:
                    env[var] = value

        for var, (value, delimiter) in env_var.items():
            tmp = [value]
            if var in env:
                tmp.append(env[var])
            env[var] = delimiter.join(tmp)

        return env

    def autobuild(self):
        """
        Perform the bootstrap, configuration, build and install the
        project. Build dependencies if not already built
        """
        if (self.isConfigured and self.isBuilt and self.isInstalled):
            return

        if self._immutable:
            raise Exception("Object is immutable. Illegal autobuild")

        for key, dep in self.dependencies.items():
            dep.autobuild()

        if self.isConfigured ^ self.isBuilt ^ self.isInstalled:
            raise Exception("Project steps where manually triggered. Can't autobuild")
        _logger.debug("{} Autobuild configure".format(self.label))
        try:
            self.configure()
        except subprocess.CalledProcessError as e:
            _logger.error("{} Configure failed. See {} for more details.".format(self.label, self.log_path))
            raise e

        _logger.debug("{} Autobuild build".format(self.label))
        try:
            self.build()
        except subprocess.CalledProcessError as e:
            _logger.error("{} Build failed. See {} for more details.".format(self.label, self.log_path))
            raise e

        _logger.debug("{} Autobuild install".format(self.label))
        try:
            self.install()
        except subprocess.CalledProcessError as e:
            _logger.error("{} Install failed. See {} for more details.".format(self.label, self.log_path))
            raise e

        _logger.debug("{} Autobuild rpath strip".format(self.label))
        try:
            self.rpath_strip()
        except subprocess.CalledProcessError as e:
            _logger.error("{} Rpath stripping failed. See {} for more details.".format(self.label, self.log_path))
            raise e

    def checkout(self):
        if self._immutable:
            raise Exception("Object is immutable. Illegal checkout")

        repo = git.Repo.clone_from(self.git_path, self.source_path)
        commit = repo.commit(self.sha1)
        repo.head.reference = commit
        assert repo.head.is_detached
        repo.head.reset(index=True, working_tree=True)

    def bootstrap(self):
        """
        Bootstap the project. Raise subprocess.CalledProcessError on
        bootstrap error.
        """
        if self._immutable:
            raise Exception("Object is immutable. Illegal bootstrap")

        out = os.path.join(self.log_path, "bootstrap.out")
        err = os.path.join(self.log_path, "bootstrap.err")

        os.chdir(self.source_path)
        with open(out, 'w') as stdout, open(err, 'w') as stderr:
            p = subprocess.run(['./bootstrap'], stdout=stdout, stderr=stderr)
        p.check_returncode()
        return p

    def configure(self):
        """
        Configure the project.
        Raises subprocess.CalledProcessError on configure error
        """
        if self._immutable:
            raise Exception("Object is immutable. Illegal configure")

        # Check that all our dependencies were actually installed
        for key, dep in self.dependencies.items():
            if not dep.isInstalled:
                # TODO: Custom exception here Dependency Error
                raise Exception("Dependency project flagged as not installed")


        out = os.path.join(self.log_path, "configure.out")
        err = os.path.join(self.log_path, "configure.err")
        env_file = os.path.join(self.log_path, "configure.env")

        env = self.get_env()

        with open(env_file, 'w') as tmp:
            pprint.pprint(env, stream=tmp)

        os.chdir(self.source_path)
        args = ['./configure']
        prefix = '--prefix={}'.format(self.installation_path)
        args.append(prefix)
        args.extend(self.custom_configure_flags)

        # TODO: log output and add INFO log point
        with open(out, 'w') as stdout, open(err, 'w') as stderr:
            p = subprocess.run(args, env=env, stdout=stdout,
                               stderr=stderr)
        p.check_returncode()
        self.isConfigured = True
        return p

    def build(self):
        """
        Build the project. Raise subprocess.CalledProcessError on build
        error.
        """
        if self._immutable:
            raise Exception("Object is immutable. Illegal build")

        out = os.path.join(self.log_path, "build.out")
        err = os.path.join(self.log_path, "build.err")

        os.chdir(self.source_path)
        args = ['make']
        env = self.get_env()

        # Number of usable cpu
        # https://docs.python.org/3/library/os.html#os.cpu_count
        num_cpu = str(len(os.sched_getaffinity(0)))
        args.append('-j')
        args.append(num_cpu)
        args.append('V=1')

        # TODO: log output and add INFO log point with args
        with open(out, 'w') as stdout, open(err, 'w') as stderr:
            p = subprocess.run(args, env=env, stdout=stdout,
                               stderr=stderr)
        p.check_returncode()
        self.isBuilt = True
        return p

    def install(self):
        """
        Install the project. Raise subprocess.CalledProcessError on
        bootstrap error
        """
        if self._immutable:
            raise Exception("Object is immutable. Illegal install")

        out = os.path.join(self.log_path, "install.out")
        err = os.path.join(self.log_path, "install.err")

        os.chdir(self.source_path)
        args = ['make', 'install']

        # TODO: log output and add INFO log point
        with open(out, 'w') as stdout, open(err, 'w') as stderr:
            p = subprocess.run(args, env=self.get_env(), stdout=stdout,
                               stderr=stderr)
        p.check_returncode()
        self.isInstalled = True
        return p

    def rpath_strip(self):
        to_strip = [os.path.join(self.installation_path, "bin"),
                    os.path.join(self.installation_path, "lib")]

        out = os.path.join(self.log_path, "rpath-strip.out")
        err = os.path.join(self.log_path, "rpath-strip.err")

        for path in to_strip:
            for base, dirs, files in os.walk(path):
                for tmp in files:
                    abs_path = os.path.abspath(os.path.join(base, tmp))
                    magic_str = magic.from_file(abs_path)
                    # Skip all non-elf file
                    if "ELF" not in magic_str.split():
                        with open(err, 'a') as stderr:
                            stderr.write("{} skip, is not an ELF, file type: {}\n".format(abs_path, magic_str))
                        continue
                    cmd = ["chrpath", "-d", abs_path]
                    with open(out, 'a') as stdout, open(err, 'a') as stderr:
                        stdout.write("Running {}\n".format(cmd))
                        stderr.write("Running {}\n".format(cmd))
                        p = subprocess.run(cmd, stdout=stdout, stderr=stderr)
                        p.check_returncode()

    def cleanup(self):
        if os.path.exists(self.source_path):
            shutil.rmtree(self.source_path)
        if os.path.exists(self.installation_path):
            shutil.rmtree(self.installation_path)


class Lttng_modules(Project):
    def __init__(self, label, git_path, sha1, tmpdir):
        super(Lttng_modules, self).__init__(label=label, git_path=git_path,
                                            sha1=sha1, tmpdir=tmpdir)
        self.add_special_env_variable("MODPROBE_OPTIONS","-v -d {}".format(self.installation_path))

    def bootstrap(self):
        pass

    def configure(self):
        pass

    def install(self):
        if self._immutable:
            raise Exception("Object is immutable. Illegal install")
        os.chdir(self.source_path)
        args = ['make', 'INSTALL_MOD_PATH={}'.format(self.installation_path),
                'modules_install']
        p = subprocess.run(args, env=self.get_env(), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
        p.check_returncode()

        # Perform a local depmod
        args = ['depmod', '-b', self.installation_path]
        p = subprocess.run(args, env=self.get_env())
        p.check_returncode()
        self.isInstalled = True

    def autobuild(self):
        try:
            super(Lttng_modules, self).autobuild()
        except subprocess.CalledProcessError as e:
            self.skip = True

    def rpath_strip(self):
        pass


class Lttng_ust(Project):
    def __init__(self, label, git_path, sha1, tmpdir):
        super(Lttng_ust, self).__init__(label=label, git_path=git_path,
                                        sha1=sha1, tmpdir=tmpdir)
        self.custom_configure_flags.extend(['--disable-man-pages'])
        self.custom_configure_flags.extend(['--enable-python-agent'])
        self.custom_configure_flags.extend(['--enable-java-agent-jul'])

        jul_path = os.path.join(self.installation_path,
                "share/java/liblttng-ust-agent.jar")
        classpath = ":".join([jul_path, '.'])
        self.add_special_env_variable("CLASSPATH", classpath)

    def install(self):
        super(Lttng_ust, self).install()
        python_path = find_dir(self.installation_path, "lttngust")
        if python_path:
            # Fetch the parent of lttngust folder
            python_path = os.path.dirname(python_path)
            self.add_special_env_variable("PYTHONPATH", python_path)



class Lttng_tools(Project):
    def __init__(self, label, git_path, sha1, tmpdir):
        super(Lttng_tools, self).__init__(label=label, git_path=git_path,
                                        sha1=sha1, tmpdir=tmpdir)
        self.add_special_env_variable("LTTNG_SESSION_CONFIG_XSD_PATH",
                os.path.join(self.installation_path, "share/xml/lttng/"))

        # Find the mi xsd
        for xsd in Settings.mi_xsd_file_name:
            mi = find_file(self.source_path, xsd)
            if mi:
                break
        if not mi:
            raise Exception("MI xsd not found")
        self.mi_xsd = mi


class Babeltrace(Project):
    pass

class Urcu(Project):
    pass
