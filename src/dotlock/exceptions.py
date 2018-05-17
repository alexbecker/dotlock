class PackageResolutionError(Exception):
    pass


class NotFound(PackageResolutionError):
    def __init__(self, name, version):
        self.name = name
        self.version = version


class NoMatchingCandidateError(PackageResolutionError):
    def __init__(self, requirement_info):
        self.requirement_info = requirement_info


class CircularDependencyError(PackageResolutionError):
    def __init__(self, dependency_chain):
        self.dependency_chain = dependency_chain


class LockEnvironmentMismatch(PackageResolutionError):
    def __init__(self, env_key, locked_value, env_value):
        self.env_key = env_key
        self.locked_value = locked_value
        self.env_value = env_value
