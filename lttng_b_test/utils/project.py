import os
import shutil
import git
import subprocess
import logging


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
        self.dependencies = []

        # State
        self.isCheckedOut = False
        self.isBootStrapped = False
        self.isBuilt = False
        self.isConfigured = False
        self.isInstalled = False

        self.source_path = tmpdir + "/source"
        self.installation_path = tmpdir + "/install"
        os.makedirs(self.source_path)
        os.makedirs(self.installation_path)
        self.logger = logging.getLogger('project.{}'.format(self.label))

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
                # TODO: WARNING log point
                # Raise for now since no special cases is known
                self.logger.warning("Special var % is already defined", var)
                raise Exception("Multiple definition of a special environment variable")
            else:
                env[var] = value

        for dep in self.dependencies:
            # Extra space just in case
            cpp_flags += " {}".format(dep.get_cppflags())
            ld_flags += " {}".format(dep.get_ldflags())
            ld_library_path += "{}:".format(dep.get_ld_library_path())
            for var, value in dep.special_env_variables.items():
                if var in env:
                    # TODO: WARNING log point
                    # Raise for now since no special cases is known
                    self.logger.warning("Special var % is already defined", var)
                    raise Exception("Multiple definition of a special environment variable")
                else:
                    env[var] = value

        # TODO: INFO log point for each variable with project information
        if cpp_flags:
            if 'CPPFLAGS' in env:
                cpp_flags = env['CPPFLAGS'] + cpp_flags
            env['CPPFLAGS'] = cpp_flags
        if ld_flags:
            if 'LDFLAGS' in env:
                ld_flags = env['LDFLAGS'] + ld_flags
            env['LDFLAGS'] = ld_flags
        if ld_library_path:
            if 'LD_LIBRARY_PATH' in env:
                ld_library_path = env['LD_LIBRARY_PATH'] + ":" + ld_library_path
            env['LD_LIBRARY_PATH'] = ld_library_path
        return env

    def autobuild(self):
        """
        Perform the bootstrap, configuration, build and install the
        project. Build dependencies if not already built
        """
        for dep in self.dependencies:
            dep.autobuild()

        if self.isCheckedOut ^ self.isBootStrapped ^ self.isBootStrapped ^ self.isBuilt ^ self.isConfigured ^ self.isInstalled:
            raise Exception("Project steps where manually triggered. Can't autobuild")

        self.configure()
        self.build()
        self.install()

    def checkout(self):
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
        os.chdir(self.source_path)
        p = subprocess.run(['./bootstrap'], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
        p.check_returncode()
        return p

    def configure(self):
        """
        Configure the project.
        Raises subprocess.CalledProcessError on configure error
        """
        # Check that all our dependencies were actually installed
        for dep in self.dependencies:
            if not dep.isInstalled:
                # TODO: Custom exception here Dependency Error
                raise Exception("Dependency project flagged as not installed")

        os.chdir(self.source_path)
        args = ['./configure']
        prefix = '--prefix={}'.format(self.installation_path)
        args.append(prefix)
        args.extend(self.custom_configure_flags)

        # TODO: log output and add INFO log point
        p = subprocess.run(args, env=self.get_env(), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
        p.check_returncode()
        self.isConfigured = True
        return p

    def build(self):
        """
        Build the project. Raise subprocess.CalledProcessError on build
        error.
        """
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
        p = subprocess.run(args, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
        p.check_returncode()
        self.isBuilt = True
        return p

    def install(self):
        """
        Install the project. Raise subprocess.CalledProcessError on
        bootstrap error
        """
        os.chdir(self.source_path)
        args = ['make', 'install']

        # TODO: log output and add INFO log point
        p = subprocess.run(args, env=self.get_env(), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
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
