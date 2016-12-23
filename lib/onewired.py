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
import time
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
    # -------------------------------------------------------------------------------------------------
    def __init__(self, log, dev='u', cache=False):
        """
        Create OneWire instance, allowing to use OneWire Network
        @param dev : device where the interface is connected to,
        default 'u' for USB
        """
        self.log = log
        self._sensors = []
        self.log.info(u"==> OWFS version : %s" % ow.__version__)
        try:
            ow.init(dev)
            self._cache = cache
            if cache:
                self._root = "/"
            else:
                self._root = "/uncached/"

            senseurslist = ow.Sensor("/").sensorList()    # [Sensor("/10.CF8313020800"), Sensor("/28.A05FD7010000"), Sensor("/26.99E4F1000000"), Sensor("/81.E1BC2C000000")]
            for senseur in senseurslist:
                self.log.info(u"==> Senseurs trouvés:  %s   %s" % (senseur.type, senseur.family + '.' + senseur.id))
        except:
            raise OneWireException(u"### Access to onewire device is not possible:  %s" % traceback.format_exc())


    # -------------------------------------------------------------------------------------------------
    def readSensor(self, saddress, sprop):
        """
        ow.Sensor don't work with sensor directory be replace by ow.owfs_get
        """
        try:
            sensor = self._root + saddress + "/" + sprop
            self.log.info(u"==> Reading sensor '%s'" % sensor)
            value = ow.owfs_get(str(sensor)).strip()                # Ex.: ow.owfs_get('/26.D050E7000000/B1-R1-A/pressure')
            if ("temperature" in sprop) and value == '85':          # Error reading thermometer return 85 ! 
                self.log.error(u"### Sensor '%s', BAD read temperature (85°)" % saddress)
                return "failed"
            return value
        except ow.exUnknownSensor:
            self.log.error(u"### Sensor '%s' NOT FOUND." % saddress)
            return "failed"
        except AttributeError:
            self.log.error(u"### Sensor '%s', ERROR while reading value." % sensor)
            return "failed"


    # -------------------------------------------------------------------------------------------------
    def writeSensor(self, saddress, sprop, value):
        """
            Write 1-wire chip 'adress/sprop' with 'value'
        """
        try:
            ow.Sensor(str(saddress))                            # Need it because "owfs_put" don't return error !
            sensor = self._root + saddress + "/" + sprop
            self.log.info(u"==> Writing sensor '%s'" % sensor)
            ow.owfs_put(str(sensor), str(value))                # Ex.: ow.owfs_put('/05.3A9233000000/PIO', '1')
        except ow.exUnknownSensor:
            errorstr = u"### Sensor '%s' NOT FOUND." % saddress
            self.log.error(errorstr)
            return False, errorstr
        except AttributeError:
            errorstr = u"### Sensor '%s', ERROR while writing value." % sensor
            self.log.error(errorstr)
            return False, errorstr
        return True, None

    def add_sensor(self, deviceid, device, address, properties, interval):
        """"Add a sensor to sensors list. """
        self._sensors.append({'deviceid': deviceid, 'device': device, 'address': address, 'properties': properties, 'interval': interval, 'nextread': 0})

    # -------------------------------------------------------------------------------------------------
    def loop_read_sensor(self, send, stop):
        """
        """
        self.log.info(u"Internal loop sensors reading started for {0} registered sensors.".format(len(self._sensors)))
        while not stop.isSet():
            try :  # catch error if self._sensors modify during iteration
                for sensor in self._sensors:
                    if time.time() >= sensor['nextread'] :
                        sensor['nextread'] = time.time() + sensor['interval']
                        val = self.readSensor(sensor['address'], sensor['properties'])
                        if val != "failed":
                            if "temperature" in sensor['properties']:
                                val = "%.1f" % float(val)
                            send(sensor['deviceid'], val)
                        self.log.debug(u"=> '{0}' : wait for {1} seconds".format(sensor['device'], sensor['interval']))
            except:
                pass
            stop.wait(0.1)


