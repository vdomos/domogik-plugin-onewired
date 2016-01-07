# -*- coding: utf-8 -*-

""" This file is part of B{Domogik} project (U{http://www.domogik.org}).

License
=======

B{Domogik} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Domogik} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Plugin purpose
==============

Plugin for onewire bus

Implements
==========

class OneWireNetwork, OneWireException

@author:
@copyright: (C) 2007-2015 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

import traceback
import subprocess
import ow


class OneWireException(Exception):
    """
    OneWire exception
    """

    def __init__(self, value):
        Exception.__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)


class OneWireNetwork:
    """
    Get informations about 1wire network
    """

    def __init__(self, log, dev='u', cache=False):
        """
        Create OneWire instance, allowing to use OneWire Network
        @param dev : device where the interface is connected to,
        default 'u' for USB
        """
        self.log = log
        self.log.info("==> OWFS version : %s" % ow.__version__)
        try:
            ow.init(dev)
            self._cache = cache
            if cache:
                self._root = "/"
            else:
                self._root = "/uncached/"

            senseurslist = ow.Sensor("/").sensorList()    # [Sensor("/10.CF8313020800"), Sensor("/28.A05FD7010000"), Sensor("/26.99E4F1000000"), Sensor("/81.E1BC2C000000")]
            for senseur in senseurslist:
                self.log.info("==> Senseurs trouvés:  %s   %s" % (senseur.type, senseur.family + '.' + senseur.id))
        except:
            raise OneWireException("### Access to onewire device is not possible:  %s" % traceback.format_exc())

        # self.sensortype2datatype = {"temperature" : "temp", "temperature9" : "temp", "humidity" : "humidity", "VAD" : "voltage", "vis" : "voltage", "B1-R1-A/pressure": "pressure" }


    def readSensor(self, saddress, sprop):
        """
        ow.Sensor don't work withe sensor directory be replace by ow.owfs_get
        """
        try:
            sensor = self._root + saddress + "/" + sprop
            self.log.info("==> Reading sensor '%s'" % sensor)
            value = ow.owfs_get(str(sensor)).strip()                    # Ex.: ow.owfs_get('/26.D050E7000000/B1-R1-A/pressure')
            return value
        except AttributeError:
            raise OneWireException("### Error while reading value: '%s'" % traceback.format_exc())



class OnewireRead:
    """
    To read onewire sensor
    """

    def __init__(self, log, onewire, devid, device, address, properties, interval, send, stop):
        """
        """
        self.log = log
        self.onewire = onewire
        self.device_id = devid
        self.device_name = device
        self.sensor_address = address
        self.sensor_properties = properties
        self.interval = interval
        self.send = send
        self.stop = stop

        self.start_read_sensor()


    def start_read_sensor(self):
        """
        """
        while not self.stop.isSet():
            val = self.onewire.readSensor(self.sensor_address, self.sensor_properties)
            if "temperature" in self.sensor_properties:
                val = "%.1f" % float(val)
            self.send(self.device_id, self.device_name, val)
            self.log.debug("=> '{0}' : wait for {1} seconds".format(self.device_name, self.interval))
            self.stop.wait(self.interval)
