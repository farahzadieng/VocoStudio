"""Persian local web interface for ClearVoice Studio."""


def create_app(*args, **kwargs):
    """Import the Flask application lazily so utility modules stay lightweight."""
    from .app import create_app as factory

    return factory(*args, **kwargs)


__all__ = ["create_app"]
