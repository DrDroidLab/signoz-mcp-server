import logging
import requests
import re

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

    def _parse_step(self, step):
        """Parse step interval from string like '5m', '1h', or integer seconds."""
        if isinstance(step, int):
            return step
        if isinstance(step, str):
            match = re.match(r"^(\d+)([smhd])$", step)
            if match:
                value, unit = match.groups()
                value = int(value)
                if unit == "s":
                    return value
                elif unit == "m":
                    return value * 60
                elif unit == "h":
                    return value * 3600
                elif unit == "d":
                    return value * 86400
            else:
                # fallback: try to parse as int
                try:
                    return int(step)
                except Exception:
                    pass
        return 60  # default

    def query_metrics(self, start_time, end_time, query, step=None, aggregation=None):
        try:
            url = f'{self.__host}/api/v4/query_range'

            from_time = int(start_time * 1000) if start_time < 1e12 else int(start_time)
            to_time = int(end_time * 1000) if end_time < 1e12 else int(end_time)

            step_val = self._parse_step(step) if step else 60

            if not query or not isinstance(query, str) or not query.strip():
                return {"error": "Query string is required and must be non-empty."}

            payload = {
                "start": from_time,
                "end": to_time,
                "step": step_val,
                "formatForWeb": False,
                "compositeQuery": {
                    "queryType": "promql",
                    "promqlQuery": {
                        "query": query
                    }
                }
            }

            print(f"Querying: {payload}")
            print(f"URL: {url}")

            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                verify=self.__ssl_verify,
                timeout=30
            )

            if response.status_code == 200:
                try:
                    return response.json()
                except Exception as e:
                    logger.error(f"Failed to parse JSON: {e}, response text: {response.text}")
                    return {"error": f"Failed to parse JSON: {e}", "raw_response": response.text}
            else:
                logger.error(f"Failed to query metrics: {response.status_code} - {response.text}")
                return {"error": f"HTTP {response.status_code}", "raw_response": response.text}
        except Exception as e:
            logger.error(f"Exception when querying metrics: {e}")
            raise e

    def fetch_apm_metrics(self, service_name, start_time, end_time, window="1m"):
        """
        Fetches standard APM metrics for a given service and time range using builder queries.
        Returns a dict of {metric_name: result}
        """
        from_time = int(start_time * 1000) if start_time < 1e12 else int(start_time)
        to_time = int(end_time * 1000) if end_time < 1e12 else int(end_time)
        step_val = self._parse_step(window)

        # Builder queries for APM metrics
        builder_queries = {
            "A": {
                "queryName": "A",
                "dataSource": "metrics",
                "aggregateAttribute": {
                    "key": "signoz_calls_total",
                    "dataType": "float64",
                    "type": "Sum",
                    "isColumn": True,
                    "isJSON": False
                },
                "timeAggregation": "rate",
                "spaceAggregation": "sum",
                "expression": "A",
                "disabled": False,
                "stepInterval": step_val,
                "functions": [],
                "filters": {
                    "items": [
                        {
                            "key": {
                                "key": "service_name",
                                "dataType": "string",
                                "type": "tag",
                                "isColumn": False,
                                "isJSON": False
                            },
                            "op": "=",
                            "value": service_name
                        }
                    ],
                    "op": "AND"
                },
                "groupBy": [
                    {
                        "key": "service_name",
                        "dataType": "string",
                        "type": "tag",
                        "isColumn": False,
                        "isJSON": False
                    }
                ],
                "legend": "{{service_name}}"
            },
            "B": {
                "queryName": "B",
                "dataSource": "metrics",
                "aggregateAttribute": {
                    "key": "signoz_calls_total",
                    "dataType": "float64",
                    "type": "Sum",
                    "isColumn": True,
                    "isJSON": False
                },
                "timeAggregation": "rate",
                "spaceAggregation": "sum",
                "expression": "B",
                "disabled": False,
                "stepInterval": step_val,
                "functions": [],
                "filters": {
                    "items": [
                        {
                            "key": {
                                "key": "service_name",
                                "dataType": "string",
                                "type": "tag",
                                "isColumn": False,
                                "isJSON": False
                            },
                            "op": "=",
                            "value": service_name
                        },
                        {
                            "key": {
                                "key": "status_code",
                                "dataType": "string",
                                "type": "tag",
                                "isColumn": False,
                                "isJSON": False
                            },
                            "op": "=",
                            "value": "STATUS_CODE_ERROR"
                        }
                    ],
                    "op": "AND"
                },
                "groupBy": [
                    {
                        "key": "service_name",
                        "dataType": "string",
                        "type": "tag",
                        "isColumn": False,
                        "isJSON": False
                    }
                ],
                "legend": "{{service_name}}"
            },
            "C": {
                "queryName": "C",
                "dataSource": "metrics",
                "aggregateAttribute": {
                    "key": "signoz_duration_bucket",
                    "dataType": "float64",
                    "type": "Histogram",
                    "isColumn": True,
                    "isJSON": False
                },
                "timeAggregation": "",
                "spaceAggregation": "p50",
                "expression": "C",
                "disabled": False,
                "stepInterval": step_val,
                "functions": [],
                "filters": {
                    "items": [
                        {
                            "key": {
                                "key": "service_name",
                                "dataType": "string",
                                "type": "tag",
                                "isColumn": False,
                                "isJSON": False
                            },
                            "op": "=",
                            "value": service_name
                        }
                    ],
                    "op": "AND"
                },
                "groupBy": [
                    {
                        "key": "service_name",
                        "dataType": "string",
                        "type": "tag",
                        "isColumn": False,
                        "isJSON": False
                    }
                ],
                "legend": "{{service_name}}"
            },
            "D": {
                "queryName": "D",
                "dataSource": "metrics",
                "aggregateAttribute": {
                    "key": "signoz_duration_bucket",
                    "dataType": "float64",
                    "type": "Histogram",
                    "isColumn": True,
                    "isJSON": False
                },
                "timeAggregation": "",
                "spaceAggregation": "p95",
                "expression": "D",
                "disabled": False,
                "stepInterval": step_val,
                "functions": [],
                "filters": {
                    "items": [
                        {
                            "key": {
                                "key": "service_name",
                                "dataType": "string",
                                "type": "tag",
                                "isColumn": False,
                                "isJSON": False
                            },
                            "op": "=",
                            "value": service_name
                        }
                    ],
                    "op": "AND"
                },
                "groupBy": [
                    {
                        "key": "service_name",
                        "dataType": "string",
                        "type": "tag",
                        "isColumn": False,
                        "isJSON": False
                    }
                ],
                "legend": "{{service_name}}"
            },
            "E": {
                "queryName": "E",
                "dataSource": "metrics",
                "aggregateAttribute": {
                    "key": "signoz_duration_bucket",
                    "dataType": "float64",
                    "type": "Histogram",
                    "isColumn": True,
                    "isJSON": False
                },
                "timeAggregation": "",
                "spaceAggregation": "p99",
                "expression": "E",
                "disabled": False,
                "stepInterval": step_val,
                "functions": [],
                "filters": {
                    "items": [
                        {
                            "key": {
                                "key": "service_name",
                                "dataType": "string",
                                "type": "tag",
                                "isColumn": False,
                                "isJSON": False
                            },
                            "op": "=",
                            "value": service_name
                        }
                    ],
                    "op": "AND"
                },
                "groupBy": [
                    {
                        "key": "service_name",
                        "dataType": "string",
                        "type": "tag",
                        "isColumn": False,
                        "isJSON": False
                    }
                ],
                "legend": "{{service_name}}"
            }
        }

        payload = {
            "start": from_time,
            "end": to_time,
            "step": step_val,
            "variables": {},
            "compositeQuery": {
                "queryType": "builder",
                "panelType": "graph",
                "builderQueries": builder_queries
            }
        }

        url = f'{self.__host}/api/v4/query_range'
        print(f"Querying: {payload}")
        print(f"URL: {url}")
        response = requests.post(
            url,
            headers=self.headers,
            json=payload,
            verify=self.__ssl_verify,
            timeout=30
        )
        if response.status_code == 200:
            try:
                return response.json()
            except Exception as e:
                logger.error(f"Failed to parse JSON: {e}, response text: {response.text}")
                return {"error": f"Failed to parse JSON: {e}", "raw_response": response.text}
        else:
            logger.error(f"Failed to query metrics: {response.status_code} - {response.text}")
            return {"error": f"HTTP {response.status_code}", "raw_response": response.text}