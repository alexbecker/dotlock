class PackageResolutionError(Exception):
    pass


class NotFound(PackageResolutionError):
    def __init__(self, name, version):
        self.name = name
        self.version = version


class NoMatchingCandidateError(PackageResolutionError):
    def __init__(self, name, specifier_set):
        self.name = name
        self.specifier_set = specifier_set


class CircularDependencyError(PackageResolutionError):
    def __init__(self, dependency_chain):
        self.dependency_chain = dependency_chain
