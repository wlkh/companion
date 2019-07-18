#!/usr/bin/env python3

"""
This manage socat sessions so that every Ping360 device has a screen session
running socat to expose it to an UDP port.
"""
import time
import subprocess
import re
import os


def screen_name_for_device(device_path):
    """
    extracts 'Ping360-id-1' from '/dev/serial/ping/Ping360-id-1-r-67-v-3.0.1'
    Works similarly for Ping1D
    """
    return "-".join(device_path.split("/")[-1].split("-")[:3])


def list_ping_devices():
    """
    List devices in dev/serial/ping/ping360*
    """
    try:
        # Note: we could easily support Ping1D here.
        output = subprocess.check_output("ls /dev/serial/ping/Ping360*", shell=True)
        output = [line for line in output.decode().split("\n") if len(line) > 0]
        return output
    except subprocess.CalledProcessError as e:
        print("Error listing devices at '/dev/serial/ping/ping360*':", e)
        return []


def device_has_screen(device):
    """
    Checks if 'device' has an associated screen session
    returns true if so
    """
    screen_name = screen_name_for_device(device)
    try:
        output = subprocess.check_output(["sudo", "-Au", "pi", "screen", "-ls"], universal_newlines=True)
        return output.decode()
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            output = e.output  # screen v4.2.x always gives exit code of 1 for 'screen -ls'
            if not output:  # no stdout, just stderr (which we don't capture the contents)
                raise Exception("Error: Could not read 'screen'!")

    regex_string = r"((?P<idNum>[0-9]+)\.(?P<idName>[^\t]+))(\t\(*(?P<time>[0-9][^\)]*)?\))?\t\((?P<state>[A-z]+)\)"
    regex = re.compile(regex_string)
    matches = regex.finditer(output)

    sessions = [match.groupdict()['idName'] for match in matches]
    return screen_name in sessions


def create_device_screen(device, port):
    """
    Creates a screen session for 'device' running socat to expose
    at UDP port 'port'
    """
    try:
        # Follow link to actual device
        target_device = subprocess.check_output(' '.join(["readlink", "-f", "%s" % device]), shell=True)
        # Strip newline from output
        target_device = target_device.decode().split('\n')[0]
    except Exception as e:
        print("Error reading symlink: %s" % e)
        return False
    path = os.path.dirname(os.path.abspath(__file__))
    screen_name = screen_name_for_device(device)
    command = "sudo -H -u pi screen -dm -S %s %s/bridges -u 0.0.0.0:%s -p %s:2000000"  # Ignores EOF if it shows in the data in the serial sid
    command = command % (screen_name, path, port, target_device)
    print("Launching: ", command)
    try:
        subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError as exception:
        print("error calling screen:", exception)
        return False
    return True


# Checks for devices forever
while True:
    for i, device in enumerate(list_ping_devices()):
        try:
            if not device_has_screen(device):
                create_device_screen(device, 9092+i)
        except Exception as e:
            print(e)
    time.sleep(1)
