import boto3
from common_utils.metrics import metrics_check

lambda_fun = boto3.client('lambda')

error_functions = []
unutilized_provision_concurrency = []
non_graviton_functions = []
underutilized_provision_concurrency_functions = []
underutilized_functions = []
all_functions = []


def get_error_rate(function_name):
    error_metric =  metrics_check(function_name, 'Errors', 'Sum', 'Count', 900, True, 'AWS/Lambda', 'FunctionName')
    invocation = metrics_check(function_name, 'Invocations', 'Sum', 'Count', 900, True, 'AWS/Lambda', 'FunctionName')
    if error_metric and invocation:
        total_error = sum(error_metric)
        total_invocation = sum(invocation)
        if total_invocation == 0:
            return 0
        error_rate = (total_error / total_invocation) * 100
        return error_rate
    return -1

def check_lambda():
    #lambda_functions = lambda_fun.list_functions()
    # Create a paginator for list_functions
    paginator = lambda_fun.get_paginator('list_functions')
    global error_functions
    global unutilized_provision_concurrency
    global non_graviton_functions
    global underutilized_provision_concurrency_functions
    global underutilized_functions
    global all_functions
    count = 0
    for page in paginator.paginate():
        lambda_functions = page['Functions']
        for function in lambda_functions:
            function_name = function['FunctionName']
            all_functions.append(function_name)
            architecture = function.get('Architectures')
            memory_allocated = function.get('MemorySize')
            print('checking for :', function_name)
            #checking for error rate
            error_rate = get_error_rate(function_name)
            if error_rate >= 20 and error_rate != -1:
                error_functions.append(function_name)
            if error_rate == -1:
                print(f"lambda function {function_name} has no metrics available")
            # check for provisioned concurrency is configured or not
            lambda_concurrency = lambda_fun.list_provisioned_concurrency_configs(FunctionName = function_name)
            if lambda_concurrency:
                for ProvisionedConcurrencyConfig in lambda_concurrency['ProvisionedConcurrencyConfigs']:
                    provisioned_concurrent_executions = ProvisionedConcurrencyConfig['RequestedProvisionedConcurrentExecutions']
                    print('provisioned_concurrent_executions is :', provisioned_concurrent_executions)
                    #check if currentexecution avg is >= the provisioned concurrency
                    currentexecution_metrics = metrics_check(function_name, 'ConcurrentExecutions', 'Average', 'Count', 900, True, 'AWS/Lambda', 'FunctionName')
                    print('current execution mtrics are', currentexecution_metrics)
                    if currentexecution_metrics:
                        if not sum(currentexecution_metrics)/len(currentexecution_metrics) >= provisioned_concurrent_executions: 
                            unutilized_provision_concurrency.append(function_name)
                        #underutilized provisioned functions
                        if sum(currentexecution_metrics)/len(currentexecution_metrics) <= 0.8 * provisioned_concurrent_executions:
                            underutilized_provision_concurrency_functions.append(function_name)
                
            #is Graviton or not
            if 'arm64' not in architecture:
                non_graviton_functions.append(function_name)
            #checking for underutilized functions
            if memory_allocated >= 1000:
                underutilized_functions.append(function_name)
            count +=1

        

    print('**********************Final Output for Lambda fucntions**************')
    print("Functions with more than 20 percent error rate are: ", error_functions)
    print("Functions with provisioned concurrency with no utilization: ", unutilized_provision_concurrency)
    print("Functions not using Graviton processor: ", non_graviton_functions)
    print("Functions with underutilized provisioned concurrency: ", underutilized_provision_concurrency_functions)
    print("underutilized functions are: ", underutilized_functions)
    print('Total Lambda Functions we have:', count)
    non_graviton_functions.clear()
    print('graviton instances are:', non_graviton_functions)
