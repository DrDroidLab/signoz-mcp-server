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
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if self.__api_key:
            self.headers['SIGNOZ-API-KEY'] = f'{self.__api_key}'

    def test_connection(self):
        try:
            url = f'{self.__host}/api/v1/health'
            response = requests.get(url, headers=self.headers, verify=self.__ssl_verify, timeout=20)
            if response and response.status_code == 200:
                return True
            else:
                status_code = response.status_code if response else None
                raise Exception(
                    f"Failed to connect with Signoz. Status Code: {status_code}. Response Text: {response.text}")
        except Exception as e:
            logger.error(f"Exception occurred while fetching signoz health with error: {e}")
            raise e

    def fetch_dashboards(self):
        try:
            url = f'{self.__host}/api/v1/dashboards'
            response = requests.get(url, headers=self.headers, verify=self.__ssl_verify, timeout=60)
            print(response)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch dashboards: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Exception when fetching dashboards: {e}")
            raise e

    def fetch_dashboard_details(self, dashboard_id):
        try:
            url = f'{self.__host}/api/v1/dashboards/{dashboard_id}'
            response = requests.get(url, headers=self.headers, verify=self.__ssl_verify, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                return response_data.get("data", response_data)
            else:
                logger.error(f"Failed to fetch dashboard details: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Exception when fetching dashboard details: {e}")
            raise e

    def query_metrics(self, start_time, end_time, query, step=None, aggregation=None):
        try:
            url = f'{self.__host}/api/v1/metrics/query'
            
            from_time = int(start_time * 1000) if start_time < 1e12 else int(start_time)
            to_time = int(end_time * 1000) if end_time < 1e12 else int(end_time)
            
            payload = {
                "query": query,
                "start": from_time,
                "end": to_time
            }
            
            if step:
                payload["step"] = step
                
            if aggregation:
                payload["aggregation"] = aggregation
            
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                verify=self.__ssl_verify,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to query metrics: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Exception when querying metrics: {e}")
            raise e