"""
Utility functions for robust LLM evaluation using langevals.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
from langevals import expect
from langevals_langevals.llm_boolean import (
    CustomLLMBooleanEvaluator,
    CustomLLMBooleanSettings,
)

class SignozResponseEvaluator:
    """Evaluator for SigNoz MCP Server responses."""
    
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
    
    def contains_services_info(self, prompt: str, response: str) -> bool:
        """Check if response contains valid service information."""
        evaluator = CustomLLMBooleanEvaluator(
            settings=CustomLLMBooleanSettings(
                prompt="Does the response contain specific information about services from SigNoz, including service names like 'Recommendation Service', 'Shipping Service', or 'Email Service'?",
                model=self.model,
            )
        )
        
        try:
            expect(input=prompt, output=response).to_pass(evaluator)
            return True
        except AssertionError:
            return False
    
    def contains_connection_status(self, prompt: str, response: str) -> bool:
        """Check if response contains connection test information."""
        evaluator = CustomLLMBooleanEvaluator(
            settings=CustomLLMBooleanSettings(
                prompt="Does the response contain connection status information with details like 'success', 'host', and 'SSL verification'?",
                model=self.model,
            )
        )
        
        try:
            expect(input=prompt, output=response).to_pass(evaluator)
            return True
        except AssertionError:
            return False
    
    def contains_dashboard_info(self, prompt: str, response: str) -> bool:
        """Check if response contains dashboard information."""
        evaluator = CustomLLMBooleanEvaluator(
            settings=CustomLLMBooleanSettings(
                prompt="Does the response contain specific information about dashboards from SigNoz, mentioning dashboard names like 'Python Microservices' or 'Go Microservices'?",
                model=self.model,
            )
        )
        
        try:
            expect(input=prompt, output=response).to_pass(evaluator)
            return True
        except AssertionError:
            return False
    
    def contains_dashboard_data(self, prompt: str, response: str, dashboard_name: str) -> bool:
        """Check if response contains specific dashboard data."""
        evaluator = CustomLLMBooleanEvaluator(
            settings=CustomLLMBooleanSettings(
                prompt=f"Does the response contain specific data for the '{dashboard_name}' dashboard, including metrics like 'Total Calls', 'Latencies', or 'Traces by Service'?",
                model=self.model,
            )
        )
        
        try:
            expect(input=prompt, output=response).to_pass(evaluator)
            return True
        except AssertionError:
            return False
    
    def contains_apm_metrics(self, prompt: str, response: str, service_name: str) -> bool:
        """Check if response contains APM metrics for a specific service."""
        evaluator = CustomLLMBooleanEvaluator(
            settings=CustomLLMBooleanSettings(
                prompt=f"Does the response contain APM metrics for the '{service_name}' service, including metrics like 'Latency', 'Error Rate', 'Request Count', or 'Request Rate'?",
                model=self.model,
            )
        )
        
        try:
            expect(input=prompt, output=response).to_pass(evaluator)
            return True
        except AssertionError:
            return False
    
    def is_helpful_response(self, prompt: str, response: str) -> bool:
        """Check if response is helpful and addresses the user's question."""
        evaluator = CustomLLMBooleanEvaluator(
            settings=CustomLLMBooleanSettings(
                prompt="Is this response helpful and does it appropriately address the user's question about SigNoz monitoring data?",
                model=self.model,
            )
        )
        
        try:
            expect(input=prompt, output=response).to_pass(evaluator)
            return True
        except AssertionError:
            return False
    
    def is_structured_response(self, prompt: str, response: str) -> bool:
        """Check if response is well-structured and readable."""
        evaluator = CustomLLMBooleanEvaluator(
            settings=CustomLLMBooleanSettings(
                prompt="Is this response well-structured, clearly formatted, and easy to read for monitoring data?",
                model=self.model,
            )
        )
        
        try:
            expect(input=prompt, output=response).to_pass(evaluator)
            return True
        except AssertionError:
            return False

def create_test_dataset(test_cases: List[Dict[str, Any]]) -> pd.DataFrame:
    """Create a pandas DataFrame from test cases for evaluation."""
    return pd.DataFrame(test_cases)

def evaluate_response_quality(
    prompt: str, 
    response: str, 
    evaluator: SignozResponseEvaluator,
    specific_checks: Optional[List[str]] = None
) -> Dict[str, bool]:
    """
    Evaluate response quality using multiple criteria.
    
    Args:
        prompt: The input prompt/question
        response: The generated response
        evaluator: SignozResponseEvaluator instance
        specific_checks: List of specific checks to run
    
    Returns:
        Dictionary with evaluation results
    """
    results = {}
    
    # Always check these basic qualities
    results["is_helpful"] = evaluator.is_helpful_response(prompt, response)
    results["is_structured"] = evaluator.is_structured_response(prompt, response)
    
    # Run specific checks if provided
    if specific_checks:
        for check in specific_checks:
            if check == "services_info":
                results["contains_services"] = evaluator.contains_services_info(prompt, response)
            elif check == "connection_status":
                results["contains_connection"] = evaluator.contains_connection_status(prompt, response)
            elif check == "dashboard_info":
                results["contains_dashboards"] = evaluator.contains_dashboard_info(prompt, response)
            elif check.startswith("dashboard_data:"):
                dashboard_name = check.split(":", 1)[1]
                results[f"contains_data_{dashboard_name}"] = evaluator.contains_dashboard_data(
                    prompt, response, dashboard_name
                )
            elif check.startswith("apm_metrics:"):
                service_name = check.split(":", 1)[1]
                results[f"contains_apm_{service_name}"] = evaluator.contains_apm_metrics(
                    prompt, response, service_name
                )
    
    return results

def assert_evaluation_passes(
    evaluation_results: Dict[str, bool], 
    min_pass_rate: float = 0.8,
    required_checks: Optional[List[str]] = None
) -> None:
    """
    Assert that evaluation results meet quality standards.
    
    Args:
        evaluation_results: Results from evaluate_response_quality
        min_pass_rate: Minimum percentage of checks that must pass
        required_checks: Specific checks that must pass (100% requirement)
    """
    total_checks = len(evaluation_results)
    passed_checks = sum(evaluation_results.values())
    pass_rate = passed_checks / total_checks if total_checks > 0 else 0.0
    
    # Check required checks first (must be 100%)
    if required_checks:
        for check in required_checks:
            if check in evaluation_results and not evaluation_results[check]:
                failed_details = [k for k, v in evaluation_results.items() if not v]
                raise AssertionError(
                    f"Required check '{check}' failed. "
                    f"Failed checks: {failed_details}. "
                    f"Overall pass rate: {pass_rate:.2%}"
                )
    
    # Check overall pass rate
    if pass_rate < min_pass_rate:
        failed_details = [k for k, v in evaluation_results.items() if not v]
        raise AssertionError(
            f"Evaluation pass rate {pass_rate:.2%} below minimum {min_pass_rate:.2%}. "
            f"Failed checks: {failed_details}"
        ) 