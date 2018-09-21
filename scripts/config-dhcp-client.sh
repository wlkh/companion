#!/bin/bash

#Bring down interface eth0
sudo ifdown eth0
echo "Interface eth0 is down"

#Bring up eth0 with DHCP Client configuration
sudo ifup eth0=config-client
echo "Interface eth0 is up with DHCP Client configuration"
echo "Configuration settings for dhcp-client mode applied to Companion"

#Disable dhcp server from running at boot
sudo update-rc.d -f isc-dhcp-server remove

#Stop dhcp server
sudo service isc-dhcp-server stop

echo "DHCP server disabled from running at boot"

sudo reboot now
