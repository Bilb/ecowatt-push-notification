

import threading
import time
import logging
import datetime
import json
import os
import traceback
from dateutil.parser import parse

from schedule import Scheduler,CancelJob

from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
from ecowatt.settings import ECOWATT_CLIENT_ID, ECOWATT_CLIENT_SECRET
from . import ecowatt, firebase, apns

logger = logging.getLogger(__name__)

DOMAIN = 'https://digital.iservices.rte-france.com'
SIGNALS_BASE_PATH = '/open_api/ecowatt/v4/signals'
TOKEN_BASE_PATH = '/token/oauth/'

SIGNALS_URL = DOMAIN + SIGNALS_BASE_PATH
TOKEN_URL = DOMAIN + TOKEN_BASE_PATH

if os.environ.get('RUN_MAIN', None) != 'true':
    firebase_app = firebase.FireBaseHelper()
    apns_app = apns.APNSHelper()


class StubSignalFetched():
    status_code= 200
    text = json.dumps(ecowatt.LAST_VALID_RESPONSE)


def update_from_ecowatt_api():
    '''
    Called every few seconds from a background thread to fetch the latest details from ecowatt and trigger PN if a change is detected
    '''
    try:
        print('update_from_ecowatt_api')

        if not ECOWATT_CLIENT_ID or not ECOWATT_CLIENT_SECRET:
            logger.info('cannot run ecowatt update, clientId and secret are not set')

        auth = HTTPBasicAuth(ECOWATT_CLIENT_ID, ECOWATT_CLIENT_SECRET)
        client = BackendApplicationClient(client_id=ECOWATT_CLIENT_ID)
        ecowatt_session = OAuth2Session(client=client)
        ecowatt_session.fetch_token(token_url=TOKEN_URL, auth=auth)

        signals_fetched = ecowatt_session.get(SIGNALS_URL)

        # signals_fetched = StubSignalFetched()
        if signals_fetched.status_code == 200 and len(signals_fetched.text) > 100:
            print(signals_fetched.status_code)
            parsed = json.loads(signals_fetched.text)
            if not parsed or not parsed['signals'] or len(parsed['signals']) < 1 or not parsed['signals'][0]['GenerationFichier']:
                print('could not parse ecowatt response')
                return
            generated_at = parsed['signals'][0]['GenerationFichier']
            generated_at_utc = datetime.datetime.timestamp(parse(generated_at))
            print('generated_at_utc ', generated_at_utc)

            has_changed = generated_at_utc != ecowatt.LAST_GENERATED_DATE_UTC
            if not has_changed:
                print('no change detected: ' + str(generated_at_utc))
                return
            print('change detected: ' + str(generated_at_utc) + ' vs ' + str(ecowatt.LAST_GENERATED_DATE_UTC))
            ecowatt.LAST_GENERATED_DATE_UTC = generated_at_utc
            ecowatt.LAST_VALID_RESPONSE = parsed
            # trigger the PN sending to all the devices we have registered
            try:
                firebase_app.send_to_all_android_devices()
            except Exception as e:
                print('An error happened while sending update to android devices', traceback.format_exc())

            try:
                apns_app.send_to_all_ios_devices()
            except Exception as e :
                print('An error happened while sending update to ios devices', traceback.format_exc())
        else:
            print('got ecowatt status code: ', signals_fetched.status_code)
    except Exception as e:
        print('An error happened while fetching data from ecowatt', traceback.format_exc())



def update_from_ecowatt_api_startup():
    '''Trigger one fetch from API on this application startup'''
    update_from_ecowatt_api()
    return CancelJob


def run_continuously(self, interval=1):
    """Continuously run, while executing pending jobs at each elapsed
    time interval.
    @return cease_continuous_run: threading.Event which can be set to
    cease continuous run.
    Please note that it is *intended behavior that run_continuously()
    does not run missed jobs*. For example, if you've registered a job
    that should run every minute and you set a continuous run interval
    of one hour then your job won't be run 60 times at each interval but
    only once.
    """

    cease_continuous_run = threading.Event()

    class ScheduleThread(threading.Thread):

        @classmethod
        def run(cls):
            while not cease_continuous_run.is_set():
                self.run_pending()
                time.sleep(interval)

    continuous_thread = ScheduleThread(daemon=True)
    continuous_thread.start()
    return cease_continuous_run

Scheduler.run_continuously = run_continuously

def start_scheduler():
    '''start running events scheduled in the background thread'''
    scheduler = Scheduler()
    scheduler.every(5).seconds.do(update_from_ecowatt_api_startup)
    scheduler.every(60).seconds.do(update_from_ecowatt_api)
    scheduler.run_continuously()
