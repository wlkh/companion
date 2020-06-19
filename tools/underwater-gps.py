#!/usr/bin/python

import time
import socket
import json
import argparse
import requests
from pymavlink import mavutil
from datetime import datetime
from os import system
import operator
import urllib2
from math import floor

STATUS_REPORT_URL = "http://192.168.2.2:2770/report_service_status"
MAVLINK2REST_URL = "http://192.168.2.2:4777"

# holds the last status so we dont flood it
last_status = ""

def report_status(*args):
    """
    reports the current status of this service
    """
    # Do not report the same status multiple times
    global last_status
    if args == last_status:
        return
    last_status = args
    print(" ".join(args))
    try:
        requests.post(STATUS_REPORT_URL, data={"waterlinked": " ".join(args)})
    except:
        print("Unable to talk to webui! Could not report status")


def request(url):
    try:
        return urllib2.urlopen(url, timeout=1).read()
    except Exception as error:
        print(error)
        return None


class NMEAFormatter:
    """
    Class responsible for holding the NMEA templates and formatting data into them
    """

    # Nmea messages templates
    # https://www.trimble.com/oem_receiverhelp/v4.44/en/NMEA-0183messages_GGA.html
    gpgga = ("$GPGGA,"                                    # Message ID
        + "{hours:02d}{minutes:02d}{seconds:02.4f},"   # UTC Time
        + "{lat:02.0f}{latmin:02.6f},"                 # Latitude (degrees + minutes)
        + "{latdir},"                                  # Latitude direction (N/S)
        + "{lon:03.0f}{lonmin:02.6},"                  # Longitude (degrees + minutes)
        + "{londir},"                                  # Longitude direction (W/E)
        + "1,"                                         # Fix? (0-5)
        + "06,"                                        # Number of Satellites
        + "1.2,"                                       # HDOP
        + "0,"                                         # MSL altitude
        + "M,"                                         # MSL altitude unit (Meters)
        + "0,"                                         # Geoid separation
        + "M,"                                         # Geoid separation unit (Meters)
        + "00,"                                        # Age of differential GPS data, N/A
        + "0000"                                       # Age of differential GPS data, N/A
        + "*")                                         # Checksum

    # https://www.trimble.com/oem_receiverhelp/v4.44/en/NMEA-0183messages_RMC.html
    gprmc = ("$GPRMC,"                                  # Message ID
        + "{hours:02d}{minutes:02d}{seconds:02.4f}," # UTC Time
        + "A,"                                       # Status A=active or V=void
        + "{lat:02.0f}{latmin:02.6f},"               # Latitude (degrees + minutes)
        + "{latdir},"                                # Latitude direction (N/S)
        + "{lon:03.0f}{lonmin:02.6},"                # Longitude (degrees + minutes)
        + "{londir},"                                # Longitude direction (W/E)
        + "0.0,"                                     # Speed over the ground in knots
        + "{orientation:03.2f},"                     # Track angle in degrees
        + "{date},"                                  # Date
        + ","                                        # Magnetic variation in degrees
        + ","                                        # Magnetic variation direction
        + "A"                                        # A=autonomous, D=differential,
                                                        # E=Estimated, N=not valid, S=Simulator.
        + "*")                                       # Checksum

    # https://www.trimble.com/oem_receiverhelp/v4.44/en/NMEA-0183messages_VTG.html
    gpvtg = ("$GPVTG,"                    # Message ID
        + "{orientation:03.2f},"       # Track made good (degrees true)
        + "T,"                         # T: track made good is relative to true north
        + ","                          # Track made good (degrees magnetic)1
        + "M,"                         # M: track made good is relative to magnetic north
        + "0.0,"                       # Speed, in knots
        + "N,"                         # N: speed is measured in knots
        + "0.0,"                       # Speed over ground in kilometers/hour (kph)
        + "K,"                         # K: speed over ground is measured in kph
        + "A"                          # A=autonomous, D=differential,
                                        # E=Estimated, N=not valid, S=Simulator.
        + "*")                         # Checksum


    def calculateNmeaChecksum(self, string):
        """
        Calculates the checksum of an Nmea string
        """
        data, checksum = string.split("*")
        calculated_checksum = reduce(operator.xor, bytearray(data[1:]), 0)
        return calculated_checksum


    def format(self, message, now=0, lat=0, lon=0, orientation=0):
        """
        Formats data into nmea message
        """

        now = datetime.now()
        latdir = "N" if lat > 0 else "S"
        londir = "E" if lon > 0 else "W"
        lat = abs(lat)
        lon = abs(lon)
        msg = message.format(date=now.strftime("%d%m%y"),
                            hours=now.hour,
                            minutes=now.minute,
                            seconds=(now.second + now.microsecond/1000000.0),
                            lat=floor(lat),
                            latmin=(lat % 1) * 60,
                            latdir=latdir,
                            lon=floor(lon),
                            lonmin=(lon % 1) * 60,
                            londir=londir,
                            orientation=orientation)

        return msg + ("%02x\r\n" % self.calculateNmeaChecksum(msg)).upper()

    def generate_messages(self, time, lat, lon, orientation):
        """
        Generates populated NMEA messages with the given time, lat, lon and orientation
        """
        messages = []
        for message in [self.gpgga, self.gprmc, self.gpvtg]:
            messages.append(
                self.format(message, time, lat, lon, orientation)
            )
        return messages


class Mavlink2RestHelper:
    """
    Responsible for interfacing with Mavlink2Rest
    """

    def get_mavlink(self, path):
        """
        Helper to get mavlink data from mavlink2rest
        Example: get_mavlink('/VFR_HUD')
        Returns the data as text
        """
        response = request(MAVLINK2REST_URL + '/mavlink' + path)
        if not response:
            report_status("Error trying to access mavlink2rest!")
            return "0.0"
        return response


    def get_message_frequency(self, message_name):
        """
        Returns the frequency at which message "message_name" is being received, 0 if unavailable
        """
        return float(self.get_mavlink('/{0}/message_information/frequency'.format(message_name)))



    # TODO: Find a way to run this check for every message received without overhead
    # check https://github.com/patrickelectric/mavlink2rest/issues/9
    def ensure_message_frequency(self, message_name, frequency):
        """
        Makes sure that a mavlink message is being received at least at "frequency" Hertz
        Returns true if successful, false otherwise
        """
        message_name = message_name.upper()
        current_frequency = self.get_message_frequency(message_name)

        # load message template from mavlink2rest helper
        try:
            data = json.loads(requests.get(MAVLINK2REST_URL + '/helper/message/COMMAND_LONG').text)
        except:
            return False

        msg_id = getattr(mavutil.mavlink, 'MAVLINK_MSG_ID_' + message_name)
        data["message"]["command"] = {"type": 'MAV_CMD_SET_MESSAGE_INTERVAL'}
        data["message"]["param1"] = msg_id
        data["message"]["param2"] = int(1000/frequency)

        try:
            result = requests.post(MAVLINK2REST_URL + '/mavlink', json=data)
            return result.status_code == 200
        except Exception as error:
            report_status("error setting message frequency: " + str(error))
            return False


    def set_param(self, param_name, param_type, param_value):
        """
        Sets parameter "param_name" of type param_type to value "value" in the autpilot
        Returns True if succesful, False otherwise
        """
        try:
            data = json.loads(requests.get(MAVLINK2REST_URL + '/helper/message/PARAM_SET').text)

            for i, char in enumerate(param_name):
                data["message"]["param_id"][i] = char

            data["message"]["param_type"] = {"type": param_type}
            data["message"]["param_value"] = param_value

            result = requests.post(MAVLINK2REST_URL + '/mavlink', json=data)
            return result.status_code == 200
        except Exception as error:
            print("error setting parameter: " + str(error))
            return False


    def get_depth(self):
        """
        returns ROV depth. Limited between [0, +inf] as this is the range The underwater gps
        expects to receive
        """
        return max(0, -float(self.get_mavlink('/VFR_HUD/alt')))


    def get_orientation(self):
        """
        fetches ROV orientation
        """
        return float(self.get_mavlink('/VFR_HUD/heading'))


    def get_temperature(self):
        """
        fetches Water temperature from ROV sensors
        """
        return float(self.get_mavlink('/SCALED_PRESSURE2/temperature'))/100.0


class UnderwaterGpsDriver:
    """
    Integration of Waterlinked Underwater GPS with Ardusub and Companion
    """
    def __init__(self, args):
        # Socket to send GPS data to mavproxy
        self.socket_mavproxy = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket_mavproxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket_mavproxy.setblocking(0)

        # Use UDP port 14401 to send NMEA data to QGC for topside location
        self.qgc_nmea_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.qgc_nmea_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.qgc_nmea_socket.setblocking(0)

        self.mav = Mavlink2RestHelper()
        self.formatter = NMEAFormatter()
        self.gpsUrl = "http://" + args.ip + ":" + args.port

        self.depth_endpoint = self.gpsUrl + "/api/v1/external/depth"
        self.orientation_endpoint = self.gpsUrl + "/api/v1/external/orientation"
        self.locator_endpoint = self.gpsUrl + "/api/v1/position/global"
        self.master_endpoint = self.gpsUrl + "/api/v1/position/master"
        self.status_endpoint = self.gpsUrl + "/api/v1/about/status"

        # Update at 5Hz
        self.update_period = 0.2

    def send_depth_and_orientation(self):
        # send depth and temprature information
        ext_depth = {
            "depth": self.mav.get_depth(),
            "temp": self.mav.get_temperature()
        }
        # Equivalent
        # curl -X PUT -H "Content-Type: application/json" -d '{"depth":1,"temp":2}' "http://37.139.8.112:8000/api/v1/external/depth"
        requests.put(self.depth_endpoint, json=ext_depth, timeout=0.5)

        # Send heading to external/orientation api
        ext_orientation = {
            "orientation": max(min(360, self.mav.get_orientation()), 0)
        }
        requests.put(self.orientation_endpoint, json=ext_orientation, timeout=1)
        print(ext_depth, ext_orientation)

    def check_waterlinked_status(self):
        """
        Checks the status reported by the Underwater GPS.
        Returns True if everything ok, False if something is wrong
        or connection is lost.
        """
        errors = ""
        try:
            status = json.loads(request(self.status_endpoint))
            if status["gps"] == 3 and status["imu"] == 3:
                return True
            if status["gps"] != 3:
                errors += "Bad GPS signal"
            if status["imu"] != 3:
                errors += "Bad IMU calibration"
            if errors:
                report_status(errors)
            return False
        except Exception as error:
            print(error)
            report_status("Connection to Underwater GPS lost!")
            return False

    def run(self):
        self.setup_streamrates()
        self.wait_for_waterlinked()

        # Sets GPS type to MAVLINK
        self.mav.set_param("GPS_TYPE", "MAV_PARAM_TYPE_UINT8", 14)

        last_master_update = 0
        last_locator_update = 0
        last_position_update = 0

        waterlinked_ok = False

        # TODO: upgrade this to async once we have Python >= 3.6
        while True:
            if not waterlinked_ok:
                waterlinked_ok = self.check_waterlinked_status()

            time.sleep(0.02)

            # Only try to read final position if everything is ok
            if waterlinked_ok:
                if time.time() > last_locator_update + self.update_period:
                    last_locator_update = time.time()
                    waterlinked_ok = self.processLocatorPosition()

                if time.time() > last_master_update + self.update_period:
                    last_master_update = time.time()
                    waterlinked_ok = self.processMasterPosition()

            # Attempt to send Depth and Temperature anyway so the Underwater GPS GUI doesn't complain
            if time.time() > last_position_update + self.update_period:
                try:
                    last_position_update = time.time()
                    self.send_depth_and_orientation()
                except requests.exceptions.RequestException as error:
                    print(error)
                    waterlinked_ok = False


    def setup_streamrates(self):
        """
        Setup message streams to get Orientation(VFR_HUD), Depth(VFR_HUD), and temperature(SCALED_PRESSURE2)
        """
        # VFR_HUD at at least 5Hz
        while not self.mav.ensure_message_frequency("VFR_HUD", 5):
            time.sleep(2)

        # SCALED_PRESSURE2 at at least 1Hz
        while not self.mav.ensure_message_frequency("SCALED_PRESSURE2", 1):
            time.sleep(2)


    def wait_for_waterlinked(self):
        """
        Waits until the Underwater GPS system is available
        Returns when it is found
        """
        while True:
            report_status("scanning for Water Linked underwater GPS...")
            try:
                requests.get(self.gpsUrl + '/api/v1/about/', timeout=1)
                break
            except requests.exceptions.RequestException as error:
                print(error)
            time.sleep(5)

    def processMasterPosition(self):
        """
        Callback to handle the Master position request. This sends the topside position and orientation
        to QGroundControl via UDP port 14401
        """
        response = request(self.master_endpoint)
        if not response:
            report_status("Unable to fetch Master position from Waterlinked API")
            return False

        result = json.loads(response)
        if 'lat' not in result or 'lon' not in result or 'orientation' not in result:
            report_status('master(topside) response is not valid:')
            return False
        # new approach: nmea messages to port 14401
        try:
            for msg in self.formatter.generate_messages(
                datetime.now(),
                result['lat'],
                result['lon'],
                orientation=result['orientation']):
                self.qgc_nmea_socket.sendto(msg, ('192.168.2.1', 14401))
        except Exception as error:
            raise error
            report_status("Error reading master position: {0}".format(error))
            return False
        report_status("Running")
        return True

    def processLocatorPosition(self):
        """
        Callback to handle the Locator position request.
        Forwards the locator(ROV) position to mavproxy's GPSInput module
        TODO: Change this too to use mavlink2rest
        """
        response = request(self.locator_endpoint)
        if not response:
            report_status("Unable to fetch Locator position from Waterlinked API")
            return False

        result = json.loads(response)
        if 'lat' not in result or 'lon' not in result:
            report_status('global response is not valid!')
            print(json.dumps(result, indent=4, sort_keys=True))
            return False

        result['lat'] = result['lat'] * 1e7
        result['lon'] = result['lon'] * 1e7
        result['fix_type'] = 3
        result['hdop'] = 1.0
        result['vdop'] = 1.0
        result['satellites_visible'] = 10
        result['ignore_flags'] = 8 | 16 | 32
        result = json.dumps(result)
        self.socket_mavproxy.sendto(result, ('0.0.0.0', 25100))
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Driver for the Water Linked Underwater GPS system.")
    parser.add_argument('--ip', action="store", type=str, default="demo.waterlinked.com", help="remote ip to query on.")
    parser.add_argument('--port', action="store", type=str, default="80", help="remote port to query on.")
    args = parser.parse_args()

    waterlinked = UnderwaterGpsDriver(args)
    waterlinked.run()