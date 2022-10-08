import math
import json
from firebase_admin import messaging, initialize_app, credentials

from pn.models import Device, get_android_devices_to_send_notification
from ecowatt.settings import FIREBASE_KEY_PATH
from . import ecowatt

 # we can send up to FIREBASE_MULTICAST_MAX tokens with the firebase Multicast
FIREBASE_MULTICAST_MAX = 500

class FireBaseHelper():
    '''Utility class to send the push notification to all the registered android devices'''

    def __init__(self):
        self.firebase_app = initialize_app(credentials.Certificate(FIREBASE_KEY_PATH))

    def send_to_all_android_devices(self):
        '''Iterate over all the android registered devices, and send them a multicast message'''

        if ecowatt.LAST_GENERATED_DATE_UTC <= 0:
            return

        devices = get_android_devices_to_send_notification()

        count = devices.count()
        print('We need to send the update to android device count: ', count)

        if count <= 0:
            print('No android devices registered yet.')
            return

        steps = math.floor(count/FIREBASE_MULTICAST_MAX) + 1
        data_to_send = ecowatt.get_dict_to_send()

        for i in range(steps):
            sliced = devices[i*FIREBASE_MULTICAST_MAX: (i+1)*FIREBASE_MULTICAST_MAX]
            registration_tokens = []
            for device in sliced:
                registration_tokens.append(device.token)

            print('sending android PN to tokens: ', registration_tokens)

            message = messaging.MulticastMessage(
                data=data_to_send,
                tokens=registration_tokens,
            )
            response = messaging.send_multicast(message)
            for device in sliced: #TODO batch this call
                device.update_last_push()

            if response.failure_count > 0:
                responses = response.responses
                failed_tokens = []
                for idx, resp in enumerate(responses):
                    if not resp.success:
                        failed_token = registration_tokens[idx]
                        failed_tokens.append(failed_token)

                print(f'List of tokens that caused failures: {failed_tokens}')
                for failed_token in failed_tokens: #TODO batch this call
                    try:
                        failed_device = Device.objects.get(type='A', token=failed_token)
                        failed_device.increase_failure_count()
                    except Device.DoesNotExist:
                        pass