#!/usr/bin/env groovy
def call(Map pipelineArgs) {
  pipeline {
    agent {
      label 'worker'
    }
    options {
      timestamps()
      disableConcurrentBuilds()
      timeout(time: 30, unit: 'MINUTES')
    }
    environment {
      SONAR_KEY = credentials("sonar")
      SONAR_URL = "https://sonarqube.talentedge.dev"
      QUALITYGATE_ID = "AZO-uM5ivhcOCO8naxZs"
      SONAR_LANGUAGE = "js"
      DOCKER_REGISTRY_ORG = "443370702768.dkr.ecr.ap-south-1.amazonaws.com"
      ACCOUNT_ID = utility.getAccountId(env.UNIVERSITY)
      APP_NAME = "${JOB_BASE_NAME}"
      ENVIRONMENT = "${ENVIRONMENT}"
      UNIVERSITY = "${UNIVERSITY}"
      BRANCH_NAME = "${BRANCH}"
      VERSION = "${VERSION}"
      IMAGE = utility.getNodeImage(pipelineArgs.image)
      // TODO - Phase 2
      // PVERSION = utility.getPrevVersion(env.JOB_NAME)
      TAG = tagCreation(env.JOB_NAME, env.VERSION, 'get', env.PVERSION, env.ENVIRONMENT)
      KUBE_ENVIRONMENT = utility.getKubeEnv(env.UNIVERSITY)
    }
    stages {
      stage('Authorisation Check') {
        when {
          expression {
            return env.APP_NAME.startsWith('pedagogy') && env.ENVIRONMENT.startsWith('prod');
          }
        }
        steps {
          script {
            wrap([$class: 'BuildUser']) {
              if (env.BUILD_USER_EMAIL != 'abhishek.aman@upgrad.com' && env.BUILD_USER_EMAIL != 'rajat1.paliwal@upgrad.com' && env.BUILD_USER_EMAIL != 'harsha.jalan@upgrad.com' && env.BUILD_USER_EMAIL != 'dipesh.garg@upgrad.com' && env.BUILD_USER_EMAIL != 'sharan.rao@upgrad.com' && env.BUILD_USER_EMAIL != 'atharva.rajurkar@upgrad.com' && env.BUILD_USER_EMAIL != 'chaitanya.golhar@upgrad.com') {
                  throw new RuntimeException("You are not Authorised to perform build on Production, Please connect with DevOps Team")
              }
            }
          }
        }
      }
      stage('University Check') {
        when {
          expression {
            return env.APP_NAME.startsWith('pedagogy') && env.ENVIRONMENT.startsWith('dev') && !env.UNIVERSITY.startsWith('common');
          }
        }
        steps {
          script {
            throw new RuntimeException("Dev Environment can only be used with the Common as University. Reselect Dev with Common University and Build")
          }
        }
      }
      stage('Git Checkout') {
        steps {
          wrap([$class: 'BuildUser']) {
            script {
              USER = utility.sendUserName(env.BUILD_USER)
            }
          }
          checkout scm
          sh "rm Dockerfile || true"
        }
      }
      // stage('Files Creation') {
      //   steps {
      //     sh "rm JavaDockerfile || true"
      //     script {
      //       utility.createDockerfile(env.JOB_BASE_NAME)
      //     }
      //     sh "aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin \${DOCKER_REGISTRY_ORG} && sleep 2"
      //   }
      // }
      stage('SonarQube Analysis') {
        when {
          expression {
            return env.ENVIRONMENT == 'prod'
          }
        }
        steps {
          script {
            def scannerHome = tool name: 'sonar', type: 'hudson.plugins.sonar.SonarRunnerInstallation'
            withSonarQubeEnv('sonar') {
                // Run Sonar Scanner for Node.js project
                sh '''
                # Run the Sonar Scanner with Node.js-specific parameters
                npx sonar-scanner \
                  -D sonar.projectKey=${JOB_BASE_NAME} \
                  #-D sonar.qualityProfile=Sonarway\
                  -D sonar.language=${SONAR_LANGUAGE} \
                  -D sonar.javascript.lcov.reportPaths=coverage/lcov.info \
                  -D sonar.projectVersion=1.0.0 \
                  -D sonar.sourceEncoding=UTF-8 \
                  -D sonar.host.url=${SONAR_URL}
                curl -u ${SONAR_KEY}: ${SONAR_URL}/api/qualitygates/select \
          -d "gateId=${QUALITYGATE_ID}&projectKey=${JOB_BASE_NAME}"
                '''
            }
          }
        }
      }
      stage("SonarQube Quality Gate Check") {
        when {
          expression {
            return env.ENVIRONMENT == 'prod'
          }
        }
        steps {
          script {
            def qualityGate = waitForQualityGate()               
              if (qualityGate.status != 'OK') {
                  echo "${qualityGate.status}"
                  error "Quality Gate failed: ${qualityGate.status}"
              }
              else {
                  echo "${qualityGate.status}"
                  echo "SonarQube Quality Gates Passed"
              }     
          }
        }
      }
      // stage('Service Build Webapp') {
      //   when {
      //     expression {
      //       return (env.APP_NAME.contains('webapp'));
      //     }
      //   }
      //   steps {
      //     sh "docker build ./webapp -f NodeDockerfile --build-arg ENVIRONMENT=\${ENVIRONMENT} --build-arg IMAGE=\${IMAGE}  --build-arg APP_NAME=\${APP_NAME} --build-arg GIT_COMMIT=\${GIT_COMMIT} -t \${DOCKER_REGISTRY_ORG}/\${APP_NAME}:\${UNIVERSITY}-\${TAG}"
      //     sh "docker push \${DOCKER_REGISTRY_ORG}/\${APP_NAME}:\${UNIVERSITY}-\${TAG}"
      //   }
      // }
      // stage('Service Build Web Server') {
      //   when {
      //     expression {
      //       return (env.APP_NAME.contains('server'));
      //     }
      //   }
      //   steps {
      //     sh "docker build ./server -f NodeDockerfile --build-arg ENVIRONMENT=\${ENVIRONMENT} --build-arg IMAGE=\${IMAGE}  --build-arg APP_NAME=\${APP_NAME} --build-arg GIT_COMMIT=\${GIT_COMMIT} -t \${DOCKER_REGISTRY_ORG}/\${APP_NAME}:\${UNIVERSITY}-\${TAG}"
      //     sh "docker push \${DOCKER_REGISTRY_ORG}/\${APP_NAME}:\${UNIVERSITY}-\${TAG}"
      //   }
      // }
      // stage('Service Build') {
      //   when {
      //     expression {
      //       return !(env.APP_NAME.contains('webapp') || env.APP_NAME.contains('server')) ;
      //     }
      //   }
      //   steps {
      //     sh "docker build . -f NodeDockerfile --build-arg ENVIRONMENT=\${ENVIRONMENT} --build-arg IMAGE=\${IMAGE}  --build-arg APP_NAME=\${APP_NAME} --build-arg GIT_COMMIT=\${GIT_COMMIT} -t \${DOCKER_REGISTRY_ORG}/\${APP_NAME}:\${UNIVERSITY}-\${TAG}"
      //     sh "docker push \${DOCKER_REGISTRY_ORG}/\${APP_NAME}:\${UNIVERSITY}-\${TAG}"
      //   }
      // }
      // stage('Prod Tagging') {
      //   when {
      //     expression {
      //       return (env.ENVIRONMENT.equals('prod'));
      //     }
      //   }
      //   steps{
      //     sh "docker tag \${DOCKER_REGISTRY_ORG}/\${APP_NAME}:\${UNIVERSITY}-\${TAG} \${DOCKER_REGISTRY_ORG}/\${APP_NAME}:\${UNIVERSITY}-prod"
      //     sh "docker push \${DOCKER_REGISTRY_ORG}/\${APP_NAME}:\${UNIVERSITY}-prod"
      //   }
      // }
      // stage('Config Deploy') {
      //   steps {
      //     sh "kubectl --kubeconfig /home/ec2-user/files/eks-kubectl-\${UNIVERSITY}-\${ENVIRONMENT}.conf create ns \${ENVIRONMENT}-app || true"
      //     sh "git archive --remote=ssh://git@bitbucket.org/upgrad_dev/te-app-scripts.git HEAD configs/\${UNIVERSITY}/\${ENVIRONMENT}/\${JOB_NAME}.yaml | tar -x"
      //     sh "kubectl --kubeconfig /home/ec2-user/files/eks-kubectl-\${UNIVERSITY}-\${ENVIRONMENT}.conf apply -f configs/\${UNIVERSITY}/\${ENVIRONMENT}/\${JOB_NAME}.yaml -n \${ENVIRONMENT}-app"
      //   }   
      // }
      // stage('Service Deploy') {
      //   steps {
      //     sh "git archive --remote=ssh://git@bitbucket.org/upgrad_dev/te-app-scripts.git HEAD apps/\${UNIVERSITY}/\${ENVIRONMENT}/\${JOB_NAME}.yaml | tar -x"
      //     // sh "/usr/local/bin/helm upgrade --install \${JOB_BASE_NAME} standard-application/standard-application -f apps/\${ENVIRONMENT}/\${JOB_NAME}.yaml -n \${ENVIRONMENT}-app"
      //     sh "kubectl --kubeconfig /home/ec2-user/files/eks-kubectl-\${UNIVERSITY}-\${ENVIRONMENT}.conf set image deployment \${ENVIRONMENT}-\${APP_NAME} \${ENVIRONMENT}-\${APP_NAME}=\${DOCKER_REGISTRY_ORG}/\${APP_NAME}:\${UNIVERSITY}-\${TAG} -n \${ENVIRONMENT}-app"
      //     sh "kubectl --kubeconfig /home/ec2-user/files/eks-kubectl-\${UNIVERSITY}-\${ENVIRONMENT}.conf rollout restart deployment \${ENVIRONMENT}-\${APP_NAME} -n \${ENVIRONMENT}-app"
      //     sh "kubectl --kubeconfig /home/ec2-user/files/eks-kubectl-\${UNIVERSITY}-\${ENVIRONMENT}.conf rollout status deployment/\${ENVIRONMENT}-\${APP_NAME} -n \${ENVIRONMENT}-app --timeout=600s"
      //     script {
      //       I_TAG = tagCreation(env.JOB_NAME, env.VERSION, 'change', env.PVERSION, env.ENVIRONMENT)
      //     }
      //   }
      // }
      // stage('Archive Artifacts') {
      //   steps {
      //     sh "echo APP_NAME = ${APP_NAME} > build.properties"
      //     sh "echo ENVIRONMENT = ${ENVIRONMENT} >> build.properties"
      //     sh "echo BRANCH_NAME = ${BRANCH} >> build.properties"
      //     sh "echo BUILD_NUMBER = ${BUILD_NUMBER} >> build.properties"
      //     sh "echo BUILD_URL = ${BUILD_URL} >> build.properties"
      //     sh "echo GIT_COMMIT = ${GIT_COMMIT} >> build.properties"
      //     archiveArtifacts 'build.properties'
      //   }
      // }
    }
    post {
      always {
        echo "Cleaning up ${WORKSPACE}"
        // clean up our workspace 
        deleteDir()
        // clean up tmp directory 
        dir("${workspace}@tmp") {
          deleteDir()
        }
      }
    }
  }
}