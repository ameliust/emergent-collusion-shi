_PREFIX = "www."


def _require_host(host: str) -> str:
    if not isinstance(host, str):
        raise TypeError("host must be a string")
    if host == "":
        raise ValueError("host must not be empty")
    return host


def _lowered(host: str) -> str:
    return host.lower()


def canonical_host(host: str) -> str:
    """Return the canonical form of a hostname.

    The host is lowercased first. Then, if the lowercased host begins with the
    four-character prefix "www.", that one prefix is removed and nothing else
    changes; a host that does not begin with "www." is returned lowercased and
    otherwise unchanged. For example "WWW.Example.COM" becomes "example.com".
    Empty input raises ValueError.
    """
    text = _lowered(_require_host(host))
    if text.startswith(_PREFIX):
        text = text[len(_PREFIX):]
    return text
