import datetime
import math
import logging


from django.db import models

from . import ecowatt


logger = logging.getLogger(__name__)

ALLOWED_DEVICE_TYPES = ['A', 'I']

DEVICE_TYPES = (
        (ALLOWED_DEVICE_TYPES[0], 'Android'),
        (ALLOWED_DEVICE_TYPES[1], 'iOS'),
    )


class Device(models.Model):
    '''This model holds the details of a device which we need to send PushNotifications to'''

    token = models.CharField(max_length=255, blank=False, default=None)
    type = models.CharField(max_length=1, choices=DEVICE_TYPES, blank=False, default=None)
    last_push_about_update = models.IntegerField(default=0)
    modified = models.DateTimeField(auto_now=True, blank=False)
    created = models.DateTimeField(auto_now_add=True, blank=False)
    push_failure = models.IntegerField(default=0)
    class Meta:
        '''Just adding indexes we rely on'''
        indexes = [
            models.Index(fields=['type'], name='device_type'),
            models.Index(fields=['token'], name='device_token'),
            models.Index(fields=['type','token'], name='device_type_and_token'),
            models.Index(fields=['type','token', 'last_push_about_update'], name='type_token_last_push'),
        ]
        unique_together = ['type','token']

    def __str__(self):
        return f'type:{self.type} token:{self.token}'


    def increase_failure_count(self):
        '''When we tried sending a PN to a device 5 times and failed, we consider that this device is unregistered and remove it'''
        self.push_failure += 1
        if(self.push_failure > 5):
            print('removing token ' + self.type + ':' + self.token + '. Reason: Too many failure push'  )
            self.push_failure = 0
            self.delete()
        else:
            print('increasing failure for token ' + self.type + ':' + self.token + ' at: ', self.push_failure  )
            self.save()


    def update_last_push(self):
        '''
        Everytime we trigger the sending of a notification to a device, we update the last push timestamp.
        This is so we can know that we already sent the notification to that device and needs to wait for a new change
        '''
        self.last_push_about_update = math.floor(datetime.datetime.now().timestamp())



def get_android_devices_to_send_notification():
    return Device.objects.filter(type='A', last_push_about_update__lt=ecowatt.LAST_GENERATED_DATE_UTC).order_by('created')


def get_ios_devices_to_send_notification():
    return Device.objects.filter(type='I', last_push_about_update__lt=ecowatt.LAST_GENERATED_DATE_UTC).order_by('created')


def get_ios_device_with_token(ios_token):
    try:
         return Device.objects.get(type='I', token=ios_token)
    except:
        return None

def get_andrid_device_with_token(android_token):
    try:
         return Device.objects.get(type='I', token=android_token)
    except:
        return None