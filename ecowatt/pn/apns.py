

from ast import excepthandler
import math
import json


from pyapns_client import APNSClient, IOSPayloadAlert, IOSPayload, IOSNotification, APNSDeviceException, APNSServerException, APNSProgrammingException, UnregisteredException

from pn.models import  get_ios_devices_to_send_notification
from ecowatt.settings import APNS_CERT_PATH, APNS_AUTH_KEY_PATH, APNS_AUTH_KEY_ID, APNS_TEAM_ID
from . import ecowatt


IOS_PACKAGE = 'com.audric.ecowatt'


class APNSHelper():
    '''Utility class to send the push notification to all the registered android devices'''

    def __init__(self):
        print('APNS_CERT_PATH', APNS_CERT_PATH)
        if not APNS_CERT_PATH :
            print('APNS ios configuration is not set in the environment')
        else:
            self.apns_app = APNSClient(mode=APNSClient.MODE_PROD, root_cert_path=APNS_CERT_PATH, auth_key_path=APNS_AUTH_KEY_PATH, auth_key_id=APNS_AUTH_KEY_ID, team_id=APNS_TEAM_ID)

    def send_to_all_ios_devices(self):
        if ecowatt.LAST_GENERATED_DATE_UTC <= 0:
            return
        devices = get_ios_devices_to_send_notification()

        count = devices.count()
        print('We need to send the update to iOS device count: ', count)

        if count <= 0:
            print('No iOS devices registered yet.')
            return


        ios_devices = get_ios_devices_to_send_notification()
        alert = IOSPayloadAlert(title='Ecowatt', body=ecowatt.get_dict_to_send()) #FIXME https://developer.apple.com/documentation/usernotifications/setting_up_a_remote_notification_server/generating_a_remote_notification#2943365
        payload = IOSPayload(alert=alert)
        notification = IOSNotification(payload=payload, topic=IOS_PACKAGE)

        for ios_device in ios_devices:

            try:
                ios_device.last_push_about_update
                self.apns_app.push(notification=notification, device_token=ios_device.token)
            except UnregisteredException as e:
                ios_device.delete()
                print(f'device is unregistered, compare timestamp {e.timestamp_datetime} and remove from db')
            except APNSDeviceException:
                ios_device.push_failure()
            except APNSServerException:
                print('APNSServerException: try again later')
            except APNSProgrammingException:
                print('APNSProgrammingException: check your code and try again later')

