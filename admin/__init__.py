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

#from domogik.common.plugin import Plugin.get_config ???


### package specific functions
def get_informations(device):
    info = { "device" : False,
             "device_type" : device,
             "1w_devices" : []}
    try:
        ow.init(device)             # initialize ow
        info['device'] = True
        
    except: 
        print(u"### No device found on 1-wire device '%s':  %s" % (device, traceback.format_exc()))
        pass

    if info['device'] == True:
        try:
            for device in ow.Sensor("/").find(all = True):    #.find(type = "DS18B20"):
                info['1w_devices'].append({"type" : device.type, "id" : device.family + '.' + device.id})
        except Exception as error:
            info['1w_devices'].append({"type" : "EXCEPTION ERROR", "id" : error})
    return info


def get_errorlog(cmd):
    print("Command = %s" % cmd)
    errorlog = subprocess.Popen([cmd], stdout=subprocess.PIPE)
    output = errorlog.communicate()[0]
    if isinstance(output, str):
        output = unicode(output, 'utf-8')
    return output



### common tasks
package = "plugin_onewired"
template_dir = "{0}/{1}/admin/templates".format(get_packages_directory(), package)
static_dir = "{0}/{1}/admin/static".format(get_packages_directory(), package)
geterrorlogcmd = "{0}/{1}/admin/geterrorlog.sh".format(get_packages_directory(), package)

plugin_onewired_adm = Blueprint(package, __name__,
                        template_folder = template_dir,
                        static_folder = static_dir)


@plugin_onewired_adm.route('/<client_id>')
def index(client_id):
    detail = get_client_detail(client_id)
    device = str(detail['data']['configuration'][1]['value'])
    try:
        return render_template('plugin_onewired.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            informations = get_informations(device),
            errorlog = get_errorlog(geterrorlogcmd))

    except TemplateNotFound:
        abort(404)

