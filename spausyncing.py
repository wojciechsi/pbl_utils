from .mapping import GpsData, Point, GPSConnection, select_points, calculate_position
from .ranging import UwbConnection, UwbDataPair
from .inercing import AhrsConnection, AhrsData

from time import time

import signal
import sys
import json
import pandas as pd
import numpy as np

class SpauData:
    def __init__(self,
                 uwb: UwbDataPair,
                 ahrs: AhrsData,
                 gps: GpsData):
        self.uwb_data_pair = uwb
        self.ahrs_data = ahrs
        self.gps_data = gps
        self._validate_intupts()
        self.calculated_position = Point(0.0, 0.0, "NOT_CALCULATED")

    def __repr__(self) -> str:
        val =   "                FRAME VALID\n"
        val +=  str(self.is_valid) + "\n"
        val +=  "                   TIME\n"
        val +=  str(time()) + "\n"
        val +=  "                   UWB\n"
        val +=  str(self.uwb_data_pair) + "\n"
        val +=  "                   AHRS\n"
        val +=  str(self.ahrs_data) + "\n"
        val +=  "                   GPS\n"
        val +=  str(self.gps_data) + "\n"
        val +=  "             CALCULATED_POSITION\n"
        val +=  str(self.calculated_position) + "\n\n"
        return val

    def _validate_intupts(self):
        try:
            if  self.uwb_data_pair.nearest.validate_age() \
            and self.uwb_data_pair.second.validate_age() \
            and self.ahrs_data.validate_age() \
            and self.gps_data.validate_age():
                self.is_valid = True
            else:
                self.is_valid = False
        except AttributeError: # when some conversion failed
            self.is_valid = False

    def calculate(self, points_pair):
        self.calculated_position = calculate_position(self.gps_data, self.uwb_data_pair, points_pair)


class Spausync:
    def __init__(self):
        self.uwb_connection = UwbConnection()
        self.ahrs_connection = AhrsConnection(mock=True)
        self.gps_connection = GPSConnection()
        signal.signal(signal.SIGINT,self.end)
        self.collected_data = ""
        #self.UwBdata = pd.DataFrame(columns=['timestamp_first','timestamp_second', 'tag_adress_first', 'tag_adress_second', 'distance_first', 'distance_second'])

    def launch(self):
        """
        Method initializing all submodules
        """
        self.uwb_connection.connect()
        self.gps_connection.begin()
        # the rest is connected via consructors

    def get_all_data(self) -> SpauData | None:
        """
        Method invoked when final user ask

        MPerforming calculations and data exchange
        """
        points_to_talk = select_points(self.gps_connection.get_last_value())
        self.uwb_connection.ask_for_distances(points_to_talk[0].address, points_to_talk[1].address)
        uwb_data = self.uwb_connection.get_last_UwbDataPair()
        if uwb_data == None:
            return None
        else:
            data = SpauData(
                uwb_data,
                self.ahrs_connection.get_last_value(),
                self.gps_connection.get_last_value()
            )
        data.calculate(points_to_talk)
        self.collected_data+=data.__repr__()
        #self.collected_data.append(data)
        return data

    def end(self, sig, frame):
        """
        Handle CTRL+C signal.
        """
        print("We requested for an end.")
        self.ahrs_connection.end()
        self.uwb_connection.end()
        self.gps_connection.end()
        with open('data.txt', 'w') as outfile:
            outfile.write(self.collected_data)
        sys.exit(0)
