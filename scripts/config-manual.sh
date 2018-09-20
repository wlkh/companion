#!/bin/bash

#Bring down interface eth0
sudo ifdown eth0
echo "Interface eth0 is down"

#Copy network configuration file from Companion directory to /etc/network/interfaces.d/
cp /home/pi/companion/manual_eth0 /etc/network/interfaces.d/
echo "Manual mode configuration file copied to /etc/network/interfaces.d directory"

#Bring up eth0 with Manual mode configuration
sudo ifup eth0=config-manual
echo "Interface eth0 is up with Manual mode configuration"

#Delete ip address if already present to avoid multiple entries in /boot/cmdline.txt
# e.g. sed command removes any ip address with any combination of digits [0-9] between decimal points
sudo sed -i -e 's/\s*ip=[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*//' /boot/cmdline.txt
echo "Static ip removed from /boot/cmdline.txt"

#Add static ip to cmdline.txt
# e.g. sed command adds the ip address at the end of first line in /boot/cmdline.txt 
sudo sed -i -e '1{s/$/ ip=192.168.2.2/}' /boot/cmdline.txt
echo "Static ip added to /boot/cmdline.txt"

echo "Configuration settings for manual mode applied to Companion"

#Disable dhcp server from running at boot
sudo update-rc.d -f isc-dhcp-server remove

#Stop dhcp server
sudo service isc-dhcp-server stop

echo "DHCP server disabled from running at boot"

sudo reboot now
