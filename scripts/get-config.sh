#!/bin/bash

if grep "iface eth0 inet manual" /etc/network/interfaces 1>/dev/null; then
	echo "Manual"
	exit 0
fi
if grep "iface eth0 inet static" /etc/network/interfaces 1>/dev/null; then
	echo "DHCP Server"
	exit 0
fi
if grep "iface eth0 inet dhcp" /etc/network/interfaces 1>/dev/null; then 
	echo "DHCP Client"
	exit 0
fi
