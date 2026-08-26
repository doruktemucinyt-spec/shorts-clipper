"""Sunucuyu baslatir. run.bat bunu cagiriyor.

Neden dogrudan `uvicorn server:app` degil: Windows'ta `localhost` once IPv6
adresine (::1) cozuluyor. Sadece 127.0.0.1 dinlenirse Chrome sessizce IPv4'e
duserek acabiliyor ama diger tarayicilar "baglanti kurulamadi" diyor. Burada
iki ayri yerel soket aciliyor -- biri IPv4, biri IPv6 -- ve ikisi de ayni
uygulamaya bagli. Disari acilan bir sey yok, ikisi de sadece bu bilgisayar.
"""
import socket
import sys

import uvicorn

from server import app

PORT = 8000
HOSTS = [(socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")]


def _listen(family, host):
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if family == socket.AF_INET6:
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
    sock.bind((host, PORT))
    sock.listen(2048)
    sock.set_inheritable(True)
    return sock


def main():
    sockets = []
    for family, host in HOSTS:
        try:
            sockets.append(_listen(family, host))
        except OSError as exc:
            # Adreslerden biri kullanilamiyorsa (ornegin IPv6 kapali) digeriyle devam
            print(f"[uyari] {host}:{PORT} dinlenemedi: {exc}")

    if not sockets:
        print(f"HATA: {PORT} portu zaten kullaniliyor olabilir. "
              f"Acik bir Shorts Clipper penceresi varsa once onu kapat.")
        return 1

    print(f"Shorts Clipper hazir:  http://localhost:{PORT}")
    server = uvicorn.Server(uvicorn.Config(app, log_level="info"))
    server.run(sockets=sockets)
    return 0


if __name__ == "__main__":
    sys.exit(main())
