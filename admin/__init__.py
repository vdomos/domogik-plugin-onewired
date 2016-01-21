# -*- coding: utf-8 -*-

### common imports
from flask import Blueprint, abort
from domogik.common.utils import get_packages_directory
from domogik.admin.application import render_template
from domogik.admin.views.clients import get_client_detail
from jinja2 import TemplateNotFound
import ow
import traceback
import sys

### package specific imports
import subprocess



### package specific functions
def get_informations():
    info = { "device" : False,
             "device_model" : None,
             "1w_devices" : []}
    try:
        ow.init("u") # initialize USB
        info['device_model'] = "usb"
        info['device'] = True
        
    except: 
        pass

    if info['device'] == True:
        for device in ow.Sensor("/").find(all = True):    #.find(type = "DS18B20"):
            info['1w_devices'].append({"type" : device.type, "id" : device.family + '.' + device.id})
    return info




### common tasks
package = "plugin_onewired"
template_dir = "{0}/{1}/admin/templates".format(get_packages_directory(), package)
static_dir = "{0}/{1}/admin/static".format(get_packages_directory(), package)

plugin_onewired_adm = Blueprint(package, __name__,
                        template_folder = template_dir,
                        static_folder = static_dir)

@plugin_onewired_adm.route('/<client_id>')
def index(client_id):
    detail = get_client_detail(client_id)
    try:
        return render_template('plugin_onewired.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            informations = get_informations())

    except TemplateNotFound:
        abort(404)

