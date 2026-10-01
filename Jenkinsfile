pipeline {
    agent any

    environment {
        PYTHON = 'C:\\Users\\Asus\\AppData\\Local\\Programs\\Python\\Python312\\python.exe'
        WDM_OFFLINE = 'true'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Setup Python') {
            steps {
                bat '"%PYTHON%" -m venv venv'
                bat 'venv\\Scripts\\python.exe -m pip install --upgrade pip'
                bat 'venv\\Scripts\\pip install -r requirements.txt'
            }
        }
        stage('Run Tests') {
            steps {
                bat 'venv\\Scripts\\pytest tests -v --junitxml=results.xml --html=report.html --self-contained-html'
            }
        }
    }
    post {
        always {
            junit 'results.xml'
            emailext(
                subject: "Jenkins Build #${env.BUILD_NUMBER} - ${currentBuild.currentResult} - ${env.JOB_NAME}",
                body: """<p>Build ${env.BUILD_NUMBER} finished with status: <b>${currentBuild.currentResult}</b></p>
                         <p>View in Jenkins: <a href="${env.BUILD_URL}">${env.BUILD_URL}</a></p>
                         <p>Full HTML test report is attached.</p>""",
                mimeType: 'text/html',
                to: 'shekhar@massistcrm.com',
                attachmentsPattern: 'report.html,results.xml'
            )
        }
    }
}
