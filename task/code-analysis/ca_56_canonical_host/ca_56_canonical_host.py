from typing import List, Tuple

_DEFAULT_PORTS = (":80", ":443")


def _require_host(host: str) -> str:
    if not isinstance(host, str):
        raise TypeError("host must be a string")
    if host == "":
        raise ValueError("host must not be empty")
    return host


def _split_port(text: str) -> Tuple[str, str]:
    name, colon, port = text.rpartition(":")
    if not colon:
        return text, ""
    if port == "" or not all(ch in "0123456789" for ch in port):
        raise ValueError("a port must be one or more ASCII digits")
    suffix = colon + port
    if suffix in _DEFAULT_PORTS:
        return name, ""
    return name, suffix


def _without_www(labels: List[str]) -> List[str]:
    if labels[0] == "www" and len(labels) >= 3:
        return labels[1:]
    return labels


def _without_root(labels: List[str]) -> List[str]:
    if len(labels) > 1 and labels[-1] == "":
        return labels[:-1]
    return labels


def canonical_host(host: str) -> str:
    """Return the canonical form of a host string.

    host is a hostname made of dot-separated labels, optionally followed by a
    colon and a port number written with one or more ASCII digits. The
    canonical form is built as follows. The text is lowercased as str.lower
    does. A port
    of 80 or 443 is removed along with its colon; any other port is kept as
    written. A single dot at the very end of the hostname, if present, is
    removed. A first label "www" is removed when the hostname, without its
    port and without such a final dot, has three or more labels; otherwise
    the hostname keeps it. An empty hostname, an empty label anywhere else,
    or a colon that is not followed by digits raises ValueError.
    """
    text = _require_host(host).lower()
    name, port = _split_port(text)
    labels = _without_root(_without_www(name.split(".")))
    if any(label == "" for label in labels):
        raise ValueError("labels must not be empty")
    return ".".join(labels) + port
