class MissingExtraError(Exception):
    """Exception raised when an extra is missing in the extras list."""

    def __init__(self, extra: str, package: str = "weather-data-fetchers") -> None:
        """Initialize the exception with the name of the missing extra.

        Args:
            extra: Name of the missing extra package.
            package: Name of the package requiring the extra.
        """
        self.extra = extra
        super().__init__(
            f"Optional package {extra} is missing. Please install it to use this module using `pip install {extra}` "
            f"or install all optional features using `pip install {package}[all]`."
        )
