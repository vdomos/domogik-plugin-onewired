#!/usr/bin/python
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


@author: domos  (domos dt vesta at gmail dt com)
@copyright: (C) 2007-2015 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

from domogik.common.plugin import Plugin
from domogikmq.message import MQMessage

from domogik_packages.plugin_onewired.lib.onewired import OneWireException
from domogik_packages.plugin_onewired.lib.onewired import OneWireNetwork

import threading
import time


class OnewireNetManager(Plugin):

    # -------------------------------------------------------------------------------------------------
    def __init__(self):
        """
            Init plugin
        """
        Plugin.__init__(self, name='onewired')

        # check if the plugin is configured. If not, this will stop the plugin and log an error
        if not self.check_configured():
            return

        # ### get all config keys
        onewire_device = str(self.get_config('1-wire_device'))
        onewire_cache = self.get_config('1-wire_cache')


        # ### get the devices list
        # for this plugin, if no devices are created we won't be able to use devices.
        self.devices = self.get_device_list(quit_if_no_device=True)
        # self.log.info(u"==> device:   %s" % format(self.devices))

        # get the sensors id per device :
        self.sensors = self.get_sensors(self.devices)
        # self.log.info(u"==> sensors:   %s" % format(self.sensors))        # ==> sensors:   {'device id': 'sensor name': 'sensor id'}
        # Affiche: INFO ==> sensors:   {4: {u'1-wire temperature': 36}, 5: {u'1-wire counter diff': 38, u'1-wire counter': 37}}


        # ### Open one wire network
        try:
            self.onewire = OneWireNetwork(self.log, onewire_device, onewire_cache)
        except OneWireException as e:
            self.log.error(e.value)
            print(e.value)
            self.force_leave()
            return


        # ### For each device
        self.device_list = {}
        threads = {}
        for a_device in self.devices:
            # self.log.info(u"a_device:   %s" % format(a_device))

            device_name = a_device["name"]                                      # Ex.: "Temp vesta"
            device_id = a_device["id"]                                          # Ex.: "73"
            device_type = a_device["device_type_id"]                            # Ex.: "onewire.thermometer_temp | onewire.batterymonitor_voltage"
            sensor_properties = self.get_parameter(a_device, "properties")
            sensor_address = self.get_parameter(a_device, "device")
            self.device_list.update({device_id : {'name': device_name, 'address': sensor_address, 'properties': sensor_properties}})

            if device_type != "onewire.pio_output_switch":
                sensor_interval = self.get_parameter(a_device, "interval")
                self.log.info(u"==> Device '{0}' (id:{1}/{2}), sensor = {3}/{4}".format(device_name, device_id, device_type, sensor_address, sensor_properties))
                # Affiche: INFO ==> Device 'TempExt' (id:4/onewire.thermometer_temp), sensor = 28.7079D0040000/temperature
                # self.log.debug(u"==> Sensor list of device '{0}': '{1}'".format(device_id, self.sensors[device_id]))
                # Affiche: INFO ==> Sensor list of device id:5: '{u'onewire counter diff': 38, u'onewire counter': 37}'

                if sensor_interval > 0:
                    self.log.debug(u"==> Launch reading thread for '%s' device !" % device_name)
                    thr_name = "dev_{0}".format(device_id)
                    threads[thr_name] = threading.Thread(None,
                                                            self.onewire.loop_read_sensor,
                                                            thr_name,
                                                                (device_id,
                                                                device_name,
                                                                sensor_address,
                                                                sensor_properties,
                                                                sensor_interval,
                                                                self.send_pub_data,
                                                                self.get_stop()),
                                                            {})
                    threads[thr_name].start()
                    self.register_thread(threads[thr_name])
                    self.log.info(u"==> Wait some time before running the next scheduled threads ...")
                    time.sleep(5)        # Wait some time to not start the threads with the same interval et the same time.
                else:
                    self.log.debug(u"==> Reading thread for '%s' device is DISABLED (interval < 0) !" % device_name)

            else:
                self.log.info(u"==> Device '{0}' (id:{1}/{2}), command = {3}/{4}".format(device_name, device_id, device_type, sensor_address, sensor_properties))

        self.ready()


    # -------------------------------------------------------------------------------------------------
    def send_pub_data(self, device_id, value):
        """ Send the sensors values over MQ
        """
        data = {}
        for sensor in self.sensors[device_id]:                  # "for" nécessaire pour les 2 sensors counter : '1-wire counter diff' et '1-wire counter'
            data[self.sensors[device_id][sensor]] = value       # sensor = sensor name in info.json file
        self.log.debug(u"==> Update Sensor '%s' for device id %s (%s)" % (format(data), device_id, self.device_list[device_id]["name"]))    # {u'id': u'value'}

        try:
            self._pub.send_event('client.sensor', data)
        except:
            # We ignore the message if some values are not correct
            self.log.debug(u"Bad MQ message to send. This may happen due to some invalid rainhour data. MQ data is : {0}".format(data))
            pass


    # -------------------------------------------------------------------------------------------------
    def on_mdp_request(self, msg):
        """ Called when a MQ req/rep message is received
        """
        Plugin.on_mdp_request(self, msg)
        # self.log.info(u"==> Received 0MQ messages: %s" % format(msg))
        if msg.get_action() == "client.cmd":
            reason = None
            status = True
            data = msg.get_data()
            
            device_id = data["device_id"]
            command_id = data["command_id"]
            if device_id not in self.device_list:
                self.log.error(u"### MQ REQ command, Device ID '%s' unknown, Have you restarted the plugin after device creation ?" % device_id)
                status = False
                reason = u"Plugin onewired: Unknown device ID %d" % device_id
                self.send_rep_ack(status, reason, command_id, "unknown") ;                      # Reply MQ REP (acq) to REQ command
                return

            device_name = self.device_list[device_id]["name"]
            self.log.info(u"==> Received for device '%s' MQ REQ command message: %s" % (device_name, format(data)))         # {u'command_id': 70, u'value': u'1', u'device_id': 169}

            status, reason = self.onewire.writeSensor(self.device_list[device_id]["address"], self.device_list[device_id]["properties"], data["value"])
            if status:
                self.send_pub_data(device_id, data["value"])    # Update sensor command.
            
            # Reply MQ REP (acq) to REQ command
            self.send_rep_ack(status, reason, command_id, device_name) ;

    # -------------------------------------------------------------------------------------------------
    def send_rep_ack(self, status, reason, cmd_id, dev_name):
        """ Send MQ REP (acq) to command
        """
        self.log.info(u"==> Reply MQ REP (acq) to REQ command id '%s' for device '%s'" % (cmd_id, dev_name))
        reply_msg = MQMessage()
        reply_msg.set_action('client.cmd.result')
        reply_msg.add_data('status', status)
        reply_msg.add_data('reason', reason)
        self.reply(reply_msg.get())


if __name__ == "__main__":
    OnewireNetManager()
