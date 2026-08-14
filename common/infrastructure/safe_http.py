from __future__ import annotations

import http.client
import ipaddress
import socket
from urllib import request as url_request


class UnsafeHostError(ValueError):
    """El host resuelve (o podria resolver) a una direccion no publica."""


def _is_unsafe_ip(raw_ip: str) -> bool:
    ip = ipaddress.ip_address(raw_ip)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def resolve_and_validate_host(host: str) -> str:
    """Resuelve `host` y devuelve UNA sola IP publica ya validada, para que el
    caller conecte contra esa IP en vez de dejar que la libreria HTTP vuelva a
    resolver el hostname por su cuenta.

    Sin esto hay una ventana de DNS rebinding: `_validate_url` valida el
    hostname, pero si `urlopen` resuelve el DNS de nuevo al momento de
    conectar, un atacante que controla el DNS de su propio dominio puede
    devolver una IP publica en la validacion y una IP interna (ej. el
    endpoint de metadata de la nube, 169.254.169.254) en la conexion real.
    """
    try:
        addr_infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeHostError("No fue posible resolver el host de la URL") from exc

    if not addr_infos:
        raise UnsafeHostError("No fue posible resolver el host de la URL")

    resolved_ip = None
    for _family, _type, _proto, _canonname, sockaddr in addr_infos:
        candidate_ip = sockaddr[0]
        if _is_unsafe_ip(candidate_ip):
            raise UnsafeHostError("No se permite consumir hosts locales o privados")
        if resolved_ip is None:
            resolved_ip = candidate_ip

    return resolved_ip


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host, *, pinned_ip: str, **kwargs):
        super().__init__(host, **kwargs)
        self._pinned_ip = pinned_ip

    def connect(self):
        self.sock = socket.create_connection(
            (self._pinned_ip, self.port), self.timeout, self.source_address
        )


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, *, pinned_ip: str, **kwargs):
        super().__init__(host, **kwargs)
        self._pinned_ip = pinned_ip

    def connect(self):
        sock = socket.create_connection(
            (self._pinned_ip, self.port), self.timeout, self.source_address
        )
        # server_hostname=self.host preserva SNI y la verificacion del
        # certificado contra el hostname real, aunque el socket TCP se haya
        # conectado directo a la IP ya validada.
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


class _PinnedHTTPHandler(url_request.HTTPHandler):
    def __init__(self, pinned_ip: str):
        super().__init__()
        self._pinned_ip = pinned_ip

    def http_open(self, req):
        return self.do_open(
            lambda host, **kw: _PinnedHTTPConnection(host, pinned_ip=self._pinned_ip, **kw), req
        )


class _PinnedHTTPSHandler(url_request.HTTPSHandler):
    def __init__(self, pinned_ip: str):
        super().__init__()
        self._pinned_ip = pinned_ip

    def https_open(self, req):
        return self.do_open(
            lambda host, **kw: _PinnedHTTPSConnection(host, pinned_ip=self._pinned_ip, **kw), req
        )


def build_pinned_opener(pinned_ip: str) -> url_request.OpenerDirector:
    """Devuelve un opener de urllib que ignora la resolucion DNS normal y
    conecta siempre a `pinned_ip`, preservando el Host header y el SNI/
    verificacion de certificado del hostname original."""
    return url_request.build_opener(_PinnedHTTPHandler(pinned_ip), _PinnedHTTPSHandler(pinned_ip))
