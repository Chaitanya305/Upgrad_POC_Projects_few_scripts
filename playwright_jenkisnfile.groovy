pipeline {
  agent {
    label 'degrees-jenkins-automation-worker'
  }
  options {
    timestamps()
    disableConcurrentBuilds()
  }
  environment {
    BRANCH_NAME = "${BRANCH}"
    ENVIRONMENT = "${ENVIRONMENT}"
    APP_NAME = "${JOB_BASE_NAME}"
    UNIVERSITY = "${UNIVERSITY}"
    CONFIG_FILE = "${CONFIG_FILE}"
  }
  stages {
    stage('Authorisation Check') {
      when {
        expression {
          return env.ENVIRONMENT.startsWith('Prod');
        }
      }
      steps {
        script {
          wrap([$class: 'BuildUser']) {
            if (env.BUILD_USER_EMAIL != 'dipesh.garg@upgrad.com' && env.BUILD_USER_EMAIL != 'abhishek.aman@upgrad.com' && env.BUILD_USER_EMAIL != 'rajat1.paliwal@upgrad.com' && env.BUILD_USER_EMAIL != 'parag.gade@upgrad.com' && env.BUILD_USER_EMAIL != 'sharad.dutta@upgrad.com' && env.BUILD_USER_EMAIL != 'sharan.rao@upgrad.com' && env.BUILD_USER_EMAIL != 'atharva.rajurkar@upgrad.com' && env.BUILD_USER_EMAIL != 'chaitanya.golhar@upgrad.com' && env.BUILD_USER_EMAIL != 'adnan.azam@upgrad.com'  && env.BUILD_USER_EMAIL != 'priyanka.bhavsar@upgrad.com' && env.BUILD_USER_EMAIL != 'atharva.rajurkar@upgrad.com' && env.BUILD_USER_EMAIL != 'harish.govindarajulu@upgrad.com') {
                throw new RuntimeException("You are not Authorised to perform build on Production, Please connect with DevOps Team")
            }
          }
        }
      }
    }
    stage('Git Checkout') {
      steps {
        checkout([
          $class: 'GitSCM',
          branches: [[name: "*/${BRANCH_NAME}"]],
          userRemoteConfigs: [[
            url: 'git@bitbucket.org:upgrad_dev/lms_automation.git'
          ]]
        ])
      }
    }
    stage('Service Build') {
      steps {
        dir('/home/ubuntu/workspace/lms_automation/PlayWright') {
          sh '''
          npm install -playwright
          npm install csv-parse mysql2
          npx playwright install
          npx playwright install-deps
          ENV=${ENVIRONMENT} University=${UNIVERSITY} xvfb-run -a npx playwright test --config ${CONFIG_FILE}
          '''
        }
      }
    }
  }
  post {
    always {
      publishHTML(target: [
        reportDir: 'PlayWright/playwright-report',
        reportFiles: 'index.html',
        reportName: 'Playwright Test Report',
        keepAll: true,
        allowMissing: true
      ])
      echo "Cleaning up ${WORKSPACE}"
      // clean up our workspace 
      deleteDir()
      // clean up tmp directory 
      dir("${workspace}@tmp") {
        deleteDir()
      }
    }
    failure {
        script {
        wrap([$class: 'BuildUser']) {
          def startTime = new Date(currentBuild.startTimeInMillis)
          def durationMinutes = currentBuild.durationString.replace('and counting', '').trim()
          def emailBody = """
            <p>Hi Team,</p>
            <p>Lms Automation job deployment details:</p>
            <ul>
              <li><b>Application:</b> ${APP_NAME}</li>
              <li><b>Deployed By:</b> ${env.BUILD_USER_EMAIL}</li>
              <li><b>Branch:</b> ${BRANCH}</li>
              <li><b>Build Number:</b> ${BUILD_NUMBER}</li>
              <li><b>Build URL:</b> <a href="${BUILD_URL}">${BUILD_URL}</a></li>
              <li><b>Start Time:</b> ${startTime}</li>
              <li><b>Duration:</b> ${durationMinutes}</li>
              <li><b>Status:</b> ${currentBuild.currentResult}</li>
            </ul>
            <p>Regards,<br/>DevOps Team</p>
          """

          writeFile file: "ses_email.json", text: """{
            "Destination": {
              "ToAddresses": ["${env.BUILD_USER_EMAIL}"]
            },
            "Message": {
              "Body": {
                "Html": {
                  "Charset": "UTF-8",
                  "Data": "${emailBody.replace("\"","'").replace("\n","")}"
                }
              },
              "Subject": {
                "Charset": "UTF-8",
                "Data": "Info | Lms Automation Job Deployment Details: ${APP_NAME} (${BUILD_NUMBER})"
              }
            },
            "Source": "ZeroOps Team <devops@upgrad.com>"
          }"""

          sh '''
            CREDS=$(aws sts assume-role \
            --role-arn arn:aws:iam::575925617790:role/aws-security-reports \
            --role-session-name jenkins-ses-session)

            export AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r '.Credentials.AccessKeyId')
            export AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r '.Credentials.SecretAccessKey')
            export AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r '.Credentials.SessionToken')

            aws ses send-email --region ap-south-1 --cli-input-json file://ses_email.json
          '''
        }
        }
    }
  }
}




./configure --prefix=/opt/janus \
--enable-websockets \
--enable-data-channels \
--enable-rabbitmq \
--enable-mqtt \
--enable-post-processing \
--enable-docs