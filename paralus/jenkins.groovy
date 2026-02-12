pipeline {
    agent any
    environment {
      ENVIRONMENT = "${ENVIRONMENT}"
    }
    stages {
        stage('env value is ') {
            steps {
                sh "echo env. value: ${env.ENVIRONMENT}"
                sh "echo value is : ${ENVIRONMENT}"
            }
        }
        stage('check for env') {
            when {
                expression {
                    return env.ENVIRONMENT == 'venus'
                }
            }
            steps{
                script {
                    sh 'echo setting value for venus env'
                    ENVIRONMENT = "dev"
                }
            }
        }
        stage('check env') {
            steps {
                sh "echo env. value: eks-kubectl-${env.ENVIRONMENT}.conf"
                sh "echo value is : eks-kubectl-${ENVIRONMENT}.conf"
            }
        }
    }
}
