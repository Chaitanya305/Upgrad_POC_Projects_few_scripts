import env
import requests
import sys
from openai import AzureOpenAI
import json
import re
from time_formating import time_formating
from jenkinsapi.jenkins import Jenkins

client = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint="https://aipocinstance.openai.azure.com/",
    api_key=env.open_ai_key,
)

#setting jenkins credentials
if "talentedge" in sys.argv[1]:
    jenkins_username = env.talentedge_username
    jenkins_password = env.talentedge_password

if "upgrad" in sys.argv[1]:
    jenkins_username = env.upgrad_username
    jenkins_password = env.upgrad_password

def check_url(url):
    try:
        if not re.match(r".*/\d+/console/?$", url):
            raise ValueError
        else:
            return True
    except:
        print("Provide valid jenkins job url\nValid url eg:-  https://jenkins.talentedge.dev/job/aspire-frontend/15/console")
        return False

def get_job_param(url,param_name):
    match = re.search(r"https?://(?:[^./]+\.)?([^/]+)", url)
    account = match.group(1) if match else None
    jenkins = Jenkins(f"https://jenkins.{account}", username=jenkins_username, password=jenkins_password)
    url = url.split("/")
    job = jenkins.get_job(url[4])
    build = job.get_build(int(url[5]))
    parameters = build.get_actions()['parameters']
    for param in parameters:
        if param["name"] == param_name:
            return param["value"]
    else:
        return None

def elasticsearch_curl_command(url):
    try:
        data = get_jenkins_failed_stage(url)
        start_time_value = data.get("startTimeMillis")
        duration_value = data.get("durationMillis")
        times = time_formating(start_time_value, duration_value)
        formatted_start_time, formatted_end_time, formatted_date = times
        match = re.search(r"https?://(?:[^./]+\.)?([^/]+)", url)
        account = match.group(1) if match else None
        elasticsearch_url = f"https://elasticsearch.{account}/filebeat-{formatted_date}/_search?pretty=true"
        split_url = url.split("/")
        job_name = split_url[4]
        environment = get_job_param(url, "ENVIRONMENT")
        # Define the query payload
        payload = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"kubernetes.pod.name": f"{environment}-{job_name}"}},
                        {"range": {"@timestamp": {"gte": f"{formatted_start_time}", "lt": f"{formatted_end_time}"}}}
                    ]
                }
            },
            "_source": ["message", "kubernetes.container.name", "kubernetes.pod.name", "kubernetes.container.image"],
            "size": 100
        }
        headers = {"Content-Type": "application/json"}
        response = requests.get(elasticsearch_url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            data = response.json()
            with open("./curl_command_output.log", "w") as f:
                for hit in data.get("hits", {}).get("hits", []):
                    source = hit.get("_source", {})
                    message = source.get("message", "No message")
                    container_image = source.get("kubernetes", {}).get("container", {}).get("image", "No image")
                    
                    f.write(f"Message: {message}\n")
                    f.write(f"Container Image: {container_image}\n")
                    f.write("-" * 50 + "\n")  # Separator for readability
            print("Console output saved to curl_command_output.log")
        else:
            # print(f"Error: {response.status_code}, {response.text}")
            raise ValueError
    except:
        sys.exit("supports for only 15 Days older build")

def get_jenkins_failed_stage(url):
    url = url.rstrip("/console/") + "/wfapi/describe"  # Fix incorrect strip method
    response = requests.post(url, auth=(jenkins_username, jenkins_password))
    if response.status_code == 200:
        data = response.json()  # Directly parse JSON response
        first_failed_stage = next((stage for stage in data.get("stages", []) if stage.get("status") == "FAILED"), None)
        return first_failed_stage
        #return data
    else:
        return f"Failed to fetch console output. Status code: {response.status_code}"

def get_node_id (url):
    data = get_jenkins_failed_stage(url)
    return data.get("id")

def failed_stage_name(url):
    data = get_jenkins_failed_stage(url)
    return data.get("name")

def jenkins_console_output(url):
    print(get_node_id(url))
    try:
        url = url.strip("/console/") + f"/pipeline-console/log?nodeId={get_node_id(url)}"
        response = requests.post(url, auth=(jenkins_username, jenkins_password))
        if response.status_code == 200:
            with open('./jenkins_output.txt', 'w') as file:
                file.write(response.text)
            print("Console output saved to jenkins_output.txt")
        else:
            print(f"Failed to fetch console output. Status code: {response.status_code}")
            sys.exit("Provide valid job name and build id")
    except:
        sys.exit("Provide Valid build id")

def get_openai_response(prompt, post_message):
    prompt = prompt + post_message
    response = client.chat.completions.create(
        messages=[
            {
            "role": "system",
            "content": "You are designed to work as devops engineer"
            },
            {
                "role": "user",
                "content": "make sure to provide solution in single line only for easy understanding with most possible cause for the failure, no more troubleshooting step"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=4096,
        temperature=1.0,
        top_p=1.0,
        model="gpt-4o-mini"
    )
    # Extract and return the assistant's reply
    return response.choices[0].message.content


if __name__ == "__main__":
    gpt_post_message = "what is solution for above erorr from Jenkins console output"
    if check_url(sys.argv[1]):
        jenkins_console_output(sys.argv[1])
        with open("jenkins_output.txt", "r") as file:
            gpt_input = file.read()
        if failed_stage_name(sys.argv[1]) == "Service Deploy":
            elasticsearch_curl_command(sys.argv[1])
            university = get_job_param(sys.argv[1], "UNIVERSITY")
            environment = get_job_param(sys.argv[1], "ENVIRONMENT")
            with open("./curl_command_output.log", "r") as f:
                gpt_post_message = f"what is solution for above error from Jenkins failure and why its exceeded its progress deadline for this provided logs from elastic search, check for log messages only which has image tag {university}-{environment}"
                gpt_input = gpt_input + f.read()
        gpt_answer = get_openai_response(gpt_input, gpt_post_message)
        print(gpt_answer)