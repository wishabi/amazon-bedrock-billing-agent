# Amazon Bedrock Billing Agent


This sample Amazon Bedrock Agent assist users in understanding and optimizing their AWS costs and usage. The agent leverages AWS Cost Explorer data to generate cost reports, provide recommendations, and answer questions related to AWS billing and spend.

## Prerequisites

- An AWS account with permission to create the necessary resources (IAM roles, Lambda functions, etc.)
- Access to Amazon Bedrock
- You must [request access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) to the desired Claude model before you can use it.

## Template Parameters

The template accepts the following parameters:

- `AgentName` - The name of the Bedrock agent.
- `AgentAliasName` - An alias for the agent.
- `AgentDescription` - A description of the agent's purpose.
- `AgentFoundationalModel` - The foundation model (FM) the agent is based on.
- `AgentInstruction` - The instruction text for the agent.
- `ActionGroupName` - The name of the agent's action group.
- `ActionGroupDescription` - A description of the agent's action group.

## Resources

The following resources are created:

- `BillingAgentLambdaRole` - An IAM role for the Lambda function to assume, allowing access to AWS Cost Explorer.
- `BillingAgentLambdaFunction` - The Lambda function powering the agent. It responds to the foundational model and generates cost and usage reports from AWS Cost Explorer data.
- `BillingAgentBedrockAgentRole` - An IAM role for the Bedrock Agent to assume, allowing it to invoke the foundation model.
- `BillingAgent` - The Amazon Bedrock Agent resource itself, configured with the provided parameters and an action group that includes the Lambda function as the executor.
- `AgentLambdaPermission` - Grants the Bedrock Agent permission to invoke the Lambda function.

## API Schema

The agent's action group includes an API schema defining the following endpoints:

- `/get_cost_and_usage` - Retrieves AWS cost and usage data based on user-provided filters and grouping parameters.
- `/get-dimension-values` - Retrieves available values for a specified dimension (e.g., service, region) within a billing period.
- `/get-date` - Retrieves the current date and month for reference.

## Usage

1. Launch [this](agent_template.yaml) CloudFormation stack, providing values for the template parameters.
2. Interact with the agent in Amazon Bedrock. It will respond to questions about AWS costs and usage, generate cost reports, and provide recommendations for cost optimization.


    ![Agent Demo](static/agent-demo.gif)

## Contributing

If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.


## License

This project is licensed under the [MIT License](LICENSE).
