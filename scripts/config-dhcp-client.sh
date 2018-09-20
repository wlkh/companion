#!/bin/bash

#Bring down interface eth0
sudo ifdown eth0
echo "Interface eth0 is down"

#Copy network configuration file from Companion directory to /etc/network/interfaces.d/
cp /home/pi/companion/client_eth0 /etc/network/interfaces.d/
echo "DHCP Client configuration file copied to /etc/network/interfaces.d directory"

#Bring up eth0 with DHCP Client configuration
sudo ifup eth0=config-client
echo "Interface eth0 is up with DHCP Client configuration"

#Delete ip address if already present to avoid multiple entries in /boot/cmdline.txt
# e.g. sed command removes any ip address with any combination of digits [0-9] between decimal points
sudo sed -i -e 's/\s*ip=[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*//' /boot/cmdline.txt 
echo "Static ip removed from /boot/cmdline.txt"

echo "Configuration settings for dhcp-client mode applied to Companion"

#Disable dhcp server from running at boot
sudo update-rc.d -f isc-dhcp-server remove

#Stop dhcp server
sudo service isc-dhcp-server stop

echo "DHCP server disabled from running at boot"

sudo reboot now
