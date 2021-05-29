from enum import Enum
import functools
import glob
import logging
import os
import pyudev
import re
import select
import time
from .device import Device

logging.basicConfig(level=logging.DEBUG)

class DeviceManager:

    VENDOR_LOGITECH = '046d'
    VENDOR_THRUSTMASTER = '044f'

    LG_G29 = '046d:c24f'
    LG_G920 = '046d:c262'
    LG_G923 = '046d:c266'
    LG_DF = '046d:c294'
    LG_MOMO = '046d:c295'
    LG_DFP = '046d:c298'
    LG_G25 = '046d:c299'
    LG_DFGT = '046d:c29a'
    LG_G27 = '046d:c29b'
    LG_SFW = '046d:c29c'
    LG_MOMO2 = '046d:ca03'
    TM_T300RS = '044f:b66e'

    def __init__(self):
        self.supported_wheels = [
            self.LG_G29,
            self.LG_G920,
            self.LG_G923,
            self.LG_DF,
            self.LG_MOMO,
            self.LG_DFP,
            self.LG_G25,
            self.LG_DFGT,
            self.LG_G27,
            self.LG_SFW,
            self.LG_MOMO2,
            self.TM_T300RS,
        ]
        self.devices = {}
        self.changed = True

    def start(self):
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by('input')
        self.observer = pyudev.MonitorObserver(monitor, self.register_event)
        self.init_device_list()
        self.observer.start()

    def stop(self):
        self.observer.stop()

    def register_event(self, action, udevice):
        usb_id = str(udevice.get('ID_VENDOR_ID')) + ':' + str(udevice.get('ID_MODEL_ID'))
        if usb_id not in self.supported_wheels:
            return
        seat_id = udevice.get('ID_FOR_SEAT')
        logging.debug("{}: {}".format(action, seat_id))
        if action == 'add':
            self.update_device_list(udevice)
            device = self.get_device(seat_id)
            device.reconnect()
            self.changed = True
        if action == 'remove':
            device = self.get_device(seat_id)
            device.disconnect()
            self.changed = True

    def init_device_list(self):
        context = pyudev.Context()
        for udevice in context.list_devices(subsystem='input', ID_INPUT_JOYSTICK=1):
            usb_id = str(udevice.get('ID_VENDOR_ID')) + ':' + str(udevice.get('ID_MODEL_ID'))
            if usb_id in self.supported_wheels:
                self.update_device_list(udevice)

        logging.debug('Devices:' + str(self.devices))

    def update_device_list(self, udevice):
        seat_id = udevice.get('ID_FOR_SEAT')

        if seat_id not in self.devices:
            self.devices[seat_id] = Device(self, {
                'seat_id': seat_id,
            })

        device = self.devices[seat_id]

        if 'DEVNAME' in udevice:
            if 'event' in udevice.get('DEVNAME'):
                device.set({
                    'vendor': udevice.get('ID_VENDOR_ID'),
                    'model': udevice.get('ID_MODEL_ID'),
                    'usb_id': udevice.get('ID_VENDOR_ID') + ':' + udevice.get('ID_MODEL_ID'),
                    'dev_name': udevice.get('DEVNAME'),
                })
        else:
            device.set({
                'dev_path': os.path.join(udevice.sys_path, 'device'),
                'name': udevice.get('NAME').strip('"'),
            })

    def first_device(self):
        if self.devices:
            return self.get_device(next(iter(self.devices)))
        return None

    def get_devices(self):
        self.changed = False
        return list(self.devices.values())

    def get_device(self, id):
        if id is None:
            return None
        if id in self.devices:
            return self.devices[id]
        else:
            return next((item for item in self.devices.values() if item.dev_name == id), None)

    def is_changed(self):
        return self.changed
