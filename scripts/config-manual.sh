#!/bin/bash

S1="iface eth0 inet manual"

#Remove existing settings for all other configurations from /network/interfaces
# e.g. sed -i -e '/pattern/,+#d', deletes any line containing the pattern and # number of lines after that.
sudo sed -i -e '/iface eth0 inet manual/,+1d' /etc/network/interfaces
sudo sed -i -e '/eth0 inet static/,+3d' /etc/network/interfaces
sudo sed -i -e '/eth0 inet dhcp/,+1d' /etc/network/interfaces
echo "Previous configuration settings removed from /network/interfaces"

#Delete ip address if already present to avoid multiple entries in /boot/cmdline.txt
# e.g. sed command removes any ip address with any combination of digits [0-9] between decimal points
sudo sed -i -e 's/\s*ip=[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*//' /boot/cmdline.txt
echo "Static ip removed from /boot/cmdline.txt"

#Append configuration settings for manual mode at the end of /network/interfaces file
sudo sed -i -e "\$a$S1" /etc/network/interfaces
echo "Manual settings applied to /network/interfaces"

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


