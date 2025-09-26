def not_none[T](value: T | None) -> T:
    """Unwrap an optional value, raising ValueError if None.

    Args:
        value: The value to unwrap.

    Returns:
        The unwrapped value.

    Raises:
        ValueError: If value is None.
    """
    if value is None:
        raise ValueError("Unexpected None value")

    return value
