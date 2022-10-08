import logging


from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from pn.models import Device

logger = logging.getLogger(__name__)

def register(request, device_type):
    device_token = request.GET['device_token']

    try:
        found = Device.objects.get(type=device_type, token=device_token)
        if found.push_failure > 0:
            found.push_failure = 0
            logger.info('Reseting device %s:%s.' % (device_type, device_token))

            found.save()
        logger.info('Registered device %s:%s.' % (device_type, device_token))

        return HttpResponse("Device already registered %s:%s." % (device_type, device_token))
    except Device.DoesNotExist:
        device = Device(type=device_type, token=device_token)
        device.save()
        logger.info('Registered device %s:%s.' % (device_type, device_token))
        return HttpResponse("Device registered %s:%s." % (device_type, device_token))

def unregister(request, device_type):
    device_token = request.GET['device_token']

    found = get_object_or_404(Device, type=device_type, token=device_token)

    found.delete()
    logger.info('Unregistered device %s:%s.' % (device_type, device_token))

    return HttpResponse("Device unregsitered %s:%s." % (device_type, device_token))

