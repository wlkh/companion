#!/usr/bin/env python3

import socket
import time

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# Set a timeout so the socket does not block
# indefinitely when trying to receive data.
server.settimeout(0.5)
message = b"Discovery"

print("Looking for Ping360...")

while True:
    server.sendto(message, ("192.168.2.255", 30303))
    print("Discovery message sent...")
    time.sleep(0.1)
    try:
        data, client = server.recvfrom(1048)
        print("Got reply:")
        print(client)
        print(data.decode("utf8"))
    except socket.timeout as e:
        print(e)
