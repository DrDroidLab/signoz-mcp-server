import logging
import requests
from processor.processor import Processor

logger = logging.getLogger(__name__)

class SignozApiProcessor(Processor):
    client = None

    def __init__(self, signoz_host, signoz_api_key=None, ssl_verify='true'):
        self.__host = signoz_host
        self.__api_key = signoz_api_key
        self.__ssl_verify = False if ssl_verify and ssl_verify.lower() == 'false' else True
        self.headers = {}
        if self.__api_key:
            self.headers['Authorization'] = f'Bearer {self.__api_key}'

    def test_connection(self):
        try:
            url = f'{self.__host}/api/v1/health'
            response = requests.get(url, headers=self.headers, verify=self.__ssl_verify, timeout=20)
            print(f"Response: {response.text}")
            logger.info(f"Response: {response.text}")
            if response and response.status_code == 200:
                return True
            else:
                status_code = response.status_code if response else None
                raise Exception(
                    f"Failed to connect with Signoz. Status Code: {status_code}. Response Text: {response.text}")
        except Exception as e:
            logger.error(f"Exception occurred while fetching signoz health with error: {e}")
            raise e 