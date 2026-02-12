import requests

def shark_request_remote_trigger(job_name):
    failed_job_name = "https://jenkins.talentedge.dev/job/aspire-frontend/15/console"
    failed_stage = "Service Deploy"

    jenkins_url = 'https://jenkins.upgrad.dev/job/DevOps/job/' + job_name + '/buildWithParameters?token=sharkbot'
    print(jenkins_url)
    auth = ('devops@upgrad.com', '1183e38e4319b7d4fbd090c5dfa76b63a7')
    params = {
        'Priority': 'P2',
        'Category': 'Issue  - CI/CD Jenkins/ Spinnaker',
        'Subject': f'Job is failing at {failed_stage} stage',
        'Description': f'Please check below failed job\n {failed_job_name}'
    }
    try:
        response = requests.post(jenkins_url, auth=auth, params=params)
        if response.status_code == 201:
            print('Jenkins job triggered successfully.')
        else:
            print('Failed to trigger Jenkins job . Status code: {}'.format(response.status_code))
    
    except requests.RequestException as e:
        print('Error triggering Jenkins job : {}'.format(e))

shark_request_remote_trigger('raise-devops-request')