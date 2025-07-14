import logging
import requests
import json

from processor.processor import Processor


logger = logging.getLogger(__name__)

class SignozDashboardQueryBuilder:
    def __init__(self, global_step, variables):
        self.global_step = global_step
        self.variables = variables
        self.query_letter_ord = ord("A")

    def _get_next_query_letter(self):
        letter = chr(self.query_letter_ord)
        self.query_letter_ord += 1
        if self.query_letter_ord > ord("Z"):
            self.query_letter_ord = ord("A")
        return letter

    def build_query_dict(self, query_data):
        query_dict = dict(query_data)
        current_letter = self._get_next_query_letter()
        query_dict.pop("step_interval", None)
        query_dict["stepInterval"] = self.global_step
        if "group_by" in query_dict:
            query_dict["groupBy"] = query_dict.pop("group_by")
        query_dict["queryName"] = current_letter
        query_dict["expression"] = current_letter
        query_dict["disabled"] = query_dict.get("disabled", False)
        return current_letter, query_dict

    def build_panel_payload(self, panel_type, panel_queries, start_time, end_time):
        payload = {
            "start": int(start_time),
            "end": int(end_time),
            "step": self.global_step,
            "variables": self.variables,
            "compositeQuery": {
                "queryType": "builder",
                "panelType": panel_type,
                "builderQueries": panel_queries,
            },
        }
        return json.loads(json.dumps(payload, ensure_ascii=False, indent=None))

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

    def query_metrics(self, start_time, end_time, query, step=None, aggregation=None):
        try:
            url = f'{self.__host}/api/v4/query_range'
            
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
            print(f"Response: {response.text}")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to query metrics: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Exception when querying metrics: {e}")
            raise e
    
    def execute_signoz_query(self, query_payload):
        """Execute a Clickhouse SQL query using the Signoz query range API"""
        try:
            logger.debug(f"Executing Clickhouse query with payload: {query_payload}")
            
            response = requests.post(
                f"{self.__host}/api/v4/query_range",
                headers=self.headers,
                json=query_payload,
                timeout=30
            )
            print(f"Response: {response.text}")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to execute Clickhouse query: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Exception when executing Clickhouse query: {e}")
            raise e 

    def fetch_dashboard_data(self, dashboard_name, start_time, end_time, step=None, variables_json=None):
        """
        Fetches dashboard data for all panels in a specified Signoz dashboard by name.
        Returns a dict with panel results.
        """
        try:
            dashboards = self.fetch_dashboards()
            if not dashboards or "data" not in dashboards:
                return {"status": "error", "message": "No dashboards found"}
            dashboard_id = None
            for d in dashboards["data"]:
                dashboard_data = d.get("data", {})
                if dashboard_data.get("title") == dashboard_name:
                    dashboard_id = d.get("id")
                    break
            if not dashboard_id:
                return {"status": "error", "message": f"Dashboard '{dashboard_name}' not found"}
            dashboard_details = self.fetch_dashboard_details(dashboard_id)
            if not dashboard_details:
                return {"status": "error", "message": f"Dashboard details not found for '{dashboard_name}'"}
            # Panels are nested under 'data' in the dashboard details
            panels = dashboard_details.get("data", {}).get("widgets", [])
            if not panels:
                return {"status": "error", "message": f"No panels found in dashboard '{dashboard_name}'"}
            # Parse variables
            variables = {}
            if variables_json:
                try:
                    variables = json.loads(variables_json)
                    if not isinstance(variables, dict):
                        variables = {}
                except Exception:
                    variables = {}
            # Step
            global_step = step if step is not None else 60
            query_builder = SignozDashboardQueryBuilder(global_step, variables)
            panel_results = {}
            print(f"panels: {panels}")
            for panel in panels:
                # Panel title and queries are nested in the panel dict
                panel_title = panel.get("title") or f"Panel_{panel.get('id', '')}"
                panel_type = panel.get("panelType") or panel.get("type") or "graph"
                queries = panel.get("queries") or []
                if not queries:
                    panel_results[panel_title] = {"status": "skipped", "message": "No queries in panel"}
                    continue
                built_queries = {}
                for query_data in queries:
                    if not isinstance(query_data, dict):
                        continue
                    letter, query_dict = query_builder.build_query_dict(query_data)
                    built_queries[letter] = query_dict
                if not built_queries:
                    panel_results[panel_title] = {"status": "skipped", "message": "No valid queries in panel"}
                    continue
                print(f"built_queries: {built_queries}")
                payload = query_builder.build_panel_payload(panel_type, built_queries, start_time, end_time)
                try:
                    result = self.execute_signoz_query(payload)
                    panel_results[panel_title] = {"status": "success", "data": result}
                except Exception as e:
                    panel_results[panel_title] = {"status": "error", "message": str(e)}
            return {"status": "success", "dashboard": dashboard_name, "results": panel_results}
        except Exception as e:
            return {"status": "error", "message": str(e)} 