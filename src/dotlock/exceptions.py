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


class PackageIndexError(PackageResolutionError):
    def __init__(self, msg):
        super().__init__(msg)


class UnsupportedHashFunctionError(PackageIndexError):
    def __init__(self, hash_function):
        self.hash_function = hash_function


class VCSException(PackageResolutionError):
    pass


class SystemException(Exception):
    pass


class HashMismatchError(PackageResolutionError):
    def __init__(self, name, version, actual, expected):
        self.name = name
        self.version = version
        self.actual = actual
        self.expected = expected
        super().__init__(f'Hash mismatch for {name} {version}: {actual} (actual) != {expected} (expected)')
