import boto3
from datetime import datetime, timedelta
import json
from typing import Dict, Any
import pandas as pd

ce = boto3.client('ce')


def get_today_date() -> str:
    """Gets date in YYYY-MM-DD format."""
    return {'today_date': datetime.now().strftime('%Y-%m-%d'),
            'current_month': datetime.now().strftime('%Y-%m')}


def get_dimension_values(key: str, billing_period_start: str, billing_period_end: str) -> Dict[str, Any]:
    """Get available values for a specific dimension."""
    try:
        response = ce.get_dimension_values(
            TimePeriod={
                'Start': billing_period_start,
                'End': billing_period_end
            },
            Dimension=key.upper()
        )
        dimension_values = response['DimensionValues']
        values = [value['Value'] for value in dimension_values]
        return {'dimension': key.upper(), 'values': values}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {'error': str(e)}


def generate_cost_report(params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a cost report based on the provided parameters."""

    # Initialize default values
    granularity = params.get('granularity', 'MONTHLY').upper()
    billing_period_start = params.get('billing_period_start')
    billing_period_end = params.get('billing_period_end')
    billing_period_end = datetime.strptime(
        billing_period_end, '%Y-%m-%d') + timedelta(days=1)
    billing_period_end = billing_period_end.strftime('%Y-%m-%d')
    filter_dimensions = []
    group_by_dimension = params.get('group_by_dimension', 'SERVICE')
    metrics = params.get('metric', 'UnblendedCost')

    # Construct filters based on provided parameters
    for key, value in params.items():
        if key in ['granularity', 'billing_period_start', 'billing_period_end', 'group_by_dimension', 'dimension_key', 'metric']:
            continue
        if value.lower() not in ['all', 'none', '', 'all_services', 'allservices', 'all services']:
            dimension_values = get_dimension_values(
                key, billing_period_start, billing_period_end)
            if 'error' in dimension_values:
                return {'error': dimension_values['error']}
            # check if each filter value is in the list of dimension values
            valid_values = []
            for each_value in value.split(','):
                if each_value not in dimension_values['values']:
                    return {'error': f'the filter value {each_value} is not in the list of valid dimension values for {key}. Please get the valid value using getDimensionValues function and try again'}
                valid_values.append(each_value)
            filter_dimensions.append({
                'Dimensions': {
                    'Key': key.upper(),
                    'Values': valid_values,
                    'MatchOptions': ['EQUALS']
                }
            })

    filter_criteria = None
    if filter_dimensions:
        if len(filter_dimensions) > 1:
            filter_criteria = {'And': filter_dimensions}
        else:
            filter_criteria = filter_dimensions[0]
    # Validate group_by_dimension
    if group_by_dimension.lower() in ['','none']:
        group_by_dimension = 'SERVICE'
    if group_by_dimension not in ['AZ', 'INSTANCE_TYPE', 'LINKED_ACCOUNT', 'OPERATION', 'PURCHASE_TYPE', 'SERVICE', 'USAGE_TYPE', 'PLATFORM', 'TENANCY', 'RECORD_TYPE', 'LEGAL_ENTITY_NAME', 'INVOICING_ENTITY', 'DEPLOYMENT_OPTION', 'DATABASE_ENGINE', 'CACHE_ENGINE', 'INSTANCE_TYPE_FAMILY', 'REGION', 'BILLING_ENTITY', 'RESERVATION_ID', 'SAVINGS_PLANS_TYPE', 'SAVINGS_PLAN_ARN', 'OPERATING_SYSTEM']:
        return {'error': 'Invalid group_by_dimension, check the group_by_dimension and try again. Valid values are AZ, INSTANCE_TYPE, LINKED_ACCOUNT, OPERATION, PURCHASE_TYPE, SERVICE, USAGE_TYPE, PLATFORM, TENANCY, RECORD_TYPE, LEGAL_ENTITY_NAME, INVOICING_ENTITY, DEPLOYMENT_OPTION, DATABASE_ENGINE, CACHE_ENGINE, INSTANCE_TYPE_FAMILY, REGION, BILLING_ENTITY, RESERVATION_ID, SAVINGS_PLANS_TYPE, SAVINGS_PLAN_ARN, OPERATING_SYSTEM'}

    print(f'filter_criteria: {filter_criteria}')
    print(f'group_by_dimension: {group_by_dimension}')
    # Get costs for the specified billing period with filter

    common_params = {
        'TimePeriod': {
            'Start': billing_period_start,
            'End': billing_period_end
        },
        'Granularity': granularity,
        'GroupBy': [
            {
                'Type': 'DIMENSION',
                'Key': group_by_dimension.upper()
            }
        ],
        'Metrics': [metrics]
    }
    grouped_costs = {}
    next_token = None
    while True:
        if next_token:
            common_params['NextPageToken'] = next_token
        try:
            if filter_criteria:
                common_params['Filter'] = filter_criteria
            response = ce.get_cost_and_usage(**common_params)
        except Exception as e:
            print(f"An error occurred: {e}")
            return {'error': str(e)}

        # Extract grouped costs for the billing period
        for result_by_time in response['ResultsByTime']:
            date = result_by_time['TimePeriod']['Start']
            for group in result_by_time['Groups']:
                group_key = group['Keys'][0]
                cost = float(group['Metrics'][metrics]['Amount'])
                grouped_costs.setdefault(date, {}).update({group_key: cost})
        next_token = response.get('NextPageToken')
        if not next_token:
            break
    # change the response to Dataframe, add total to row and column by cost and sort desc by cost
    df = pd.DataFrame.from_dict(grouped_costs)
    df.fillna(0, inplace=True)
    if df.empty:
        return {"GroupedCosts": "No cost data found for the specified parameters."}

    df['Total'] = df.sum(axis=1)
    df.loc['Total'] = df.sum()
    df = df.sort_values(by='Total', ascending=False).drop('Total', axis=1)

    return {'GroupedCosts': df.to_dict()}


def lambda_handler(event, context):
    """Handle the Lambda function invocation."""

    print(f'Event received from Bedrock Agent: {event}')
    response_code = 200
    action = event['actionGroup']
    api_path = event['apiPath']

    if api_path == '/get_cost_and_usage':
        try:
            parameters = {param['name']: param['value']
                          for param in event.get('parameters', [])}
            body = generate_cost_report(parameters)
        except Exception as e:
            body = {
                'error': str(e)
            }
            response_code = 500
    elif api_path == '/get-dimension-values':
        try:
            parameters = {param['name']: param['value']
                          for param in event.get('parameters', [])}
            billing_period_start = parameters.get('billing_period_start')
            billing_period_end = parameters.get('billing_period_end')
            billing_period_end = datetime.strptime(
                billing_period_end, '%Y-%m-%d') + timedelta(days=1)
            billing_period_end = billing_period_end.strftime('%Y-%m-%d')
            key = parameters.get('dimension_key', 'SERVICE')
            body = get_dimension_values(
                key, billing_period_start, billing_period_end)
        except Exception as e:
            body = {
                'error': str(e)
            }
            response_code = 500
    elif api_path == '/get-date':
        try:
            body = get_today_date()
        except Exception as e:
            body = {
                'error': str(e)
            }
            response_code = 500
    else:
        body = {
            "error": f"{action}::{api_path} is not a valid API, try another one."
        }
        response_code = 400
    # Check if the response body is greater than 25KB
    if len(json.dumps(body)) > 25000:
        body = {
            "error": "The response size is larger than the agent can support. Please update the filter or billing period and try again."
        }
        response_code = 400
        print(f"The response is larger than the agent can support. Please update the filter or billing period and try again.")
    response_body = {
        'application/json': {
            'body': json.dumps(body)
        }
    }

    print(f'Response sent to Bedrock Agent: {response_body}')
    action_response = {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action,
            "apiPath": api_path,
            "httpMethod": event['httpMethod'],
            "httpStatusCode": response_code,
            "responseBody": response_body
        }
    }

    return action_response


event = {'messageVersion': '1.0', 'agent': {'alias': 'DEU24EPUI8', 'name': 'aws-billing-agent', 'version': '7', 'id': 'HNBIBVOVAM'}, 'sessionId': '1713911535.493059', 'sessionAttributes': {}, 'promptSessionAttributes': {}, 'inputText': ' The total spend across all AWS services', 'apiPath': '/get_cost_and_usage', 'actionGroup': 'AWSBillingAgent', 'httpMethod': 'GET', 'parameters': [{'name': 'linked_account', 'type': 'string', 'value': '004889159502'}, {
    'name': 'group_by_dimension', 'type': 'string', 'value': ''}, {'name': 'metric', 'type': 'string', 'value': 'UnblendedCost'}, {'name': 'billing_period_end', 'type': 'string', 'value': '2024-03-31'}, {'name': 'granularity', 'type': 'string', 'value': 'MONTHLY'}, {'name': 'service', 'type': 'string', 'value': ''}, {'name': 'billing_period_start', 'type': 'string', 'value': '2024-03-01'}]}
lambda_handler(event, None)
