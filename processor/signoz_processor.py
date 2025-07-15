import logging
import requests
import re

from processor.processor import Processor


logger = logging.getLogger(__name__)

# Hardcoded builder query templates for standard APM metrics (matching SigNoz frontend)
APM_METRIC_QUERIES = {
    "request_rate": {
        "dataSource": "metrics",
        "aggregateOperator": "sum_rate",
        "aggregateAttribute": {"key": "signoz_latency.count", "dataType": "float64", "isColumn": True, "type": ""},
        "timeAggregation": "rate",
        "spaceAggregation": "sum",
        "functions": [],
        "filters": None,  # Fill dynamically
        "expression": "A",
        "disabled": False,
        "stepInterval": None,  # Fill dynamically
        "having": [],
        "limit": None,
        "orderBy": [],
        "groupBy": [],
        "legend": "Request Rate",
        "reduceTo": "avg"
    },
    "error_rate": {
        "dataSource": "metrics",
        "aggregateOperator": "sum_rate",
        "aggregateAttribute": {"key": "signoz_errors.count", "dataType": "float64", "isColumn": True, "type": ""},
        "timeAggregation": "rate",
        "spaceAggregation": "sum",
        "functions": [],
        "filters": None,  # Fill dynamically
        "expression": "B",
        "disabled": False,
        "stepInterval": None,  # Fill dynamically
        "having": [],
        "limit": None,
        "orderBy": [],
        "groupBy": [],
        "legend": "Error Rate",
        "reduceTo": "avg"
    },
    # Latency metrics use a multi-query structure: sum, count, then quantile/avg
    "latency": {
        "sum": {
            "dataSource": "metrics",
            "aggregateOperator": "sum",
            "aggregateAttribute": {"key": "signoz_latency.sum", "dataType": "float64", "isColumn": True, "type": ""},
            "timeAggregation": "sum",
            "spaceAggregation": "sum",
            "functions": [],
            "filters": None,  # Fill dynamically
            "expression": "C",
            "disabled": False,
            "stepInterval": None,  # Fill dynamically
            "having": [],
            "limit": None,
            "orderBy": [],
            "groupBy": [],
            "legend": "Latency Sum",
            "reduceTo": "avg"
        },
        "count": {
            "dataSource": "metrics",
            "aggregateOperator": "sum",
            "aggregateAttribute": {"key": "signoz_latency.count", "dataType": "float64", "isColumn": True, "type": ""},
            "timeAggregation": "sum",
            "spaceAggregation": "sum",
            "functions": [],
            "filters": None,  # Fill dynamically
            "expression": "D",
            "disabled": False,
            "stepInterval": None,  # Fill dynamically
            "having": [],
            "limit": None,
            "orderBy": [],
            "groupBy": [],
            "legend": "Latency Count",
            "reduceTo": "avg"
        },
        "avg": {
            "dataSource": "metrics",
            "aggregateOperator": "divide",
            "aggregateAttribute": {"key": "signoz_latency.sum", "dataType": "float64", "isColumn": True, "type": ""},
            "timeAggregation": "avg",
            "spaceAggregation": "avg",
            "functions": [],
            "filters": None,
            "expression": "C/D",
            "disabled": False,
            "stepInterval": None,
            "having": [],
            "limit": None,
            "orderBy": [],
            "groupBy": [],
            "legend": "Latency Avg",
            "reduceTo": "avg"
        }
    }
}

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

    def _post_query_range(self, payload):
        """
        Helper method to POST to /api/v4/query_range and handle response.
        """
        url = f'{self.__host}/api/v4/query_range'
        print(f"Querying: {payload}")
        print(f"URL: {url}")
        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                verify=self.__ssl_verify,
                timeout=30
            )
            if response.status_code == 200:
                try:
                    resp_json = response.json()
                    print('response json:::', resp_json)
                    return resp_json
                except Exception as e:
                    logger.error(f"Failed to parse JSON: {e}, response text: {response.text}")
                    return {"error": f"Failed to parse JSON: {e}", "raw_response": response.text}
            else:
                logger.error(f"Failed to query metrics: {response.status_code} - {response.text}")
                return {"error": f"HTTP {response.status_code}", "raw_response": response.text}
        except Exception as e:
            logger.error(f"Exception when posting to query_range: {e}")
            raise e

    def query_metrics(self, start_time, end_time, query, step=None, aggregation=None):
        try:
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
            return self._post_query_range(payload)
        except Exception as e:
            logger.error(f"Exception when querying metrics: {e}")
            raise e

    def fetch_apm_metrics(self, service_name, start_time, end_time, window="1m", operation_names=None, metrics=None):
        """
        Fetches standard APM metrics for a given service and time range using hardcoded builder query templates.
        metrics: list of metric keys to fetch (e.g., ["request_rate", "error_rate", "latency_avg"])
        operation_names: list of operation names to filter (optional)
        """
        from_time = int(start_time * 1000) if start_time < 1e12 else int(start_time)
        to_time = int(end_time * 1000) if end_time < 1e12 else int(end_time)
        step_val = self._parse_step(window)
        if not metrics:
            metrics = ["request_rate", "error_rate", "latency_avg"]
        builder_queries = {}
        query_name_counter = 65  # ASCII 'A'
        for metric_key in metrics:
            if metric_key == "latency_avg":
                # Add sum, count, and avg queries for latency
                for subkey, template in APM_METRIC_QUERIES["latency"].items():
                    import copy
                    q = copy.deepcopy(template)
                    q["stepInterval"] = step_val
                    # Fill filters
                    filters = [
                        {
                            "key": {
                                "key": "service.name",
                                "dataType": "string",
                                "isColumn": False,
                                "type": "resource"
                            },
                            "op": "IN",
                            "value": [service_name]
                        }
                    ]
                    if operation_names:
                        filters.append({
                            "key": {
                                "key": "operation",
                                "dataType": "string",
                                "isColumn": False,
                                "type": "tag"
                            },
                            "op": "IN",
                            "value": operation_names
                        })
                    if subkey in ("sum", "count"):
                        q["filters"] = {"items": filters, "op": "AND"}
                    q["queryName"] = q.get("expression")  # Use C, D, or C/D
                    builder_queries[q["queryName"]] = q
            elif metric_key in APM_METRIC_QUERIES:
                import copy
                q = copy.deepcopy(APM_METRIC_QUERIES[metric_key])
                q["stepInterval"] = step_val
                filters = [
                    {
                        "key": {
                            "key": "service.name",
                            "dataType": "string",
                            "isColumn": False,
                            "type": "resource"
                        },
                        "op": "IN",
                        "value": [service_name]
                    }
                ]
                if operation_names:
                    filters.append({
                        "key": {
                            "key": "operation",
                            "dataType": "string",
                            "isColumn": False,
                            "type": "tag"
                        },
                        "op": "IN",
                        "value": operation_names
                    })
                q["filters"] = {"items": filters, "op": "AND"}
                q["queryName"] = chr(query_name_counter)
                query_name_counter += 1
                builder_queries[q["queryName"]] = q
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
        return self._post_query_range(payload)
        

# if __name__ == "__main__":
#     signoz_processor = SignozApiProcessor(
#         signoz_host="https://microservices-signoz.demo.drdroid.io",
#         signoz_api_key="hrCw98ObIexp5Irl36H7D+qRlnaWuoPPXknozXyBtJI="
#     )
#     result = signoz_processor.fetch_apm_metrics(
#         service_name="emailservice",
#         start_time=1752505980000,
#         end_time=1752507660000,
#         window="5m"
#     )