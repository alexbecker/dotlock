import packaging.markers


class Marker(packaging.markers.Marker):
    """Subclass packaging.markers.Marker to make it hashable."""
    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return str(self) == str(other)
