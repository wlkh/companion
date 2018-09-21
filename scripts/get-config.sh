#!/bin/bash

if [ ! -f /var/lib/dhcpcd5/dhcpcd-eth0.lease ]; then
	echo "Manual"
	exit 0
fi
if sudo service isc-dhcp-server status | grep "active (running)" 1>/dev/null; then
	echo "DHCP Server"
	exit 0
fi
if [ -f /var/lib/dhcpcd5/dhcpcd-eth0.lease ]; then 
	echo "DHCP Client"
	exit 0
fi
