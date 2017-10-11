import os
import shutil
import git
import subprocess
import logging

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

        """ A collection of Project dependencies """
        self.dependencies = {}
        self._immutable = False

        # State
        self.isBuilt = False
        self.isConfigured = False
        self.isInstalled = False

        self.basedir = tmpdir
        self.log_path = os.path.join(tmpdir, "log")
        self.source_path = os.path.join(tmpdir, "source")
        self.installation_path = os.path.join(tmpdir, "install")

        os.makedirs(self.log_path)
        os.makedirs(self.source_path)
        os.makedirs(self.installation_path)

        self.special_env_variables = {}

        # Init the repo for work
        self.checkout()
        self.bootstrap()

    def get_cppflags(self):
        return " -I{}/include".format(self.installation_path)

    def get_ldflags(self):
        return " -L{}/lib".format(self.installation_path)

    def get_ld_library_path(self):
        return "{}/lib".format(self.installation_path)

    def get_env(self):
        """Modify environment to reflect dependency"""
        cpp_flags = ""
        ld_flags = ""
        ld_library_path = ""

        env = os.environ.copy()

        for var, value in self.special_env_variables.items():
            if var in env:
                # Raise for now since no special cases is known
                _logger.warning("% Special var % is already defined",
                                self.label, var)
                raise Exception("Multiple definition of a special environment variable")
            else:
                env[var] = value

        for key, dep in self.dependencies.items():
            # Extra space just in case
            cpp_flags += " {}".format(dep.get_cppflags())
            ld_flags += " {}".format(dep.get_ldflags())
            ld_library_path += "{}:".format(dep.get_ld_library_path())
            for var, value in dep.special_env_variables.items():
                if var in env:
                    # Raise for now since no special cases is known
                    _logger.warning("% Special var % is already defined",
                                    self.label, var)
                    raise Exception("Multiple definition of a special environment variable")
                else:
                    env[var] = value

        if cpp_flags:
            if 'CPPFLAGS' in env:
                cpp_flags = env['CPPFLAGS'] + cpp_flags
            env['CPPFLAGS'] = cpp_flags
            _logger.debug("% CPPFLAGS= %s", self.label, cpp_flags)
        if ld_flags:
            if 'LDFLAGS' in env:
                ld_flags = env['LDFLAGS'] + ld_flags
            env['LDFLAGS'] = ld_flags
            _logger.debug("% LDFLAGS= %s", self.label, ld_flags)
        if ld_library_path:
            if 'LD_LIBRARY_PATH' in env:
                ld_library_path = env['LD_LIBRARY_PATH'] + ":" + ld_library_path
            env['LD_LIBRARY_PATH'] = ld_library_path
            _logger.debug("% LD_LIBRARY_PATH= %s", self.label, ld_library_path)
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

        _logger.debug("% Autobuild configure", self.label)
        self.configure()
        _logger.debug("% Autobuild build", self.label)
        self.build()
        _logger.debug("% Autobuild install", self.label)
        self.install()

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

        os.chdir(self.source_path)
        args = ['./configure']
        prefix = '--prefix={}'.format(self.installation_path)
        args.append(prefix)
        args.extend(self.custom_configure_flags)

        # TODO: log output and add INFO log point
        with open(out, 'w') as stdout, open(err, 'w') as stderr:
            p = subprocess.run(args, env=self.get_env(), stdout=stdout,
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
        env['CFLAGS'] = '-g -O0'

        # Number of usable cpu
        # https://docs.python.org/3/library/os.html#os.cpu_count
        num_cpu = str(len(os.sched_getaffinity(0)))
        args.append('-j')
        args.append(num_cpu)

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

        out = os.path.join(self.log_path, "build.out")
        err = os.path.join(self.log_path, "build.err")

        os.chdir(self.source_path)
        args = ['make', 'install']

        # TODO: log output and add INFO log point
        with open(out, 'w') as stdout, open(err, 'w') as stderr:
            p = subprocess.run(args, env=self.get_env(), stdout=stdout,
                               stderr=stderr)
        p.check_returncode()
        self.isInstalled = True
        return p

    def cleanup(self):
        if os.path.exists(self.source_path):
            shutil.rmtree(self.source_path)
        if os.path.exists(self.installation_path):
            shutil.rmtree(self.installation_path)


class Lttng_modules(Project):
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


class Lttng_ust(Project):
    def __init__(self, label, git_path, sha1, tmpdir):
        super(Lttng_ust, self).__init__(label=label, git_path=git_path,
                                        sha1=sha1, tmpdir=tmpdir)
        self.custom_configure_flags.extend(['--disable-man-pages'])


class Lttng_tools(Project):
    pass


class Babeltrace(Project):
    pass
