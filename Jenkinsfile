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
                bat 'venv\\Scripts\\pytest tests -v -n 3 --junitxml=results.xml --html=report.html --self-contained-html --alluredir=allure-results'
            }
        }
    }
    post {
        always {
            junit 'results.xml'
            allure includeProperties: false, jdk: '', results: [[path: 'allure-results']]

            script {
                def testResultAction = currentBuild.testResultAction
                def total = testResultAction ? testResultAction.totalCount : 0
                def failed = testResultAction ? testResultAction.failCount : 0
                def skipped = testResultAction ? testResultAction.skipCount : 0
                def passed = total - failed - skipped
                def passRate = total > 0 ? String.format("%.1f", (passed / (float) total) * 100) : "N/A"
                def statusColor = currentBuild.currentResult == 'SUCCESS' ? '#2e7d32' : '#c62828'

                emailext(
                    subject: "Jenkins Build #${env.BUILD_NUMBER} - ${currentBuild.currentResult} - ${env.JOB_NAME}",
                    body: """
                        <div style="font-family: Arial, sans-serif; max-width: 600px;">
                            <h2 style="color: ${statusColor}; margin-bottom: 4px;">Build ${env.BUILD_NUMBER}: ${currentBuild.currentResult}</h2>
                            <p style="color: #555; margin-top:0;">DMS Selenium Test Suite &mdash; ${env.JOB_NAME}</p>
                            <table style="border-collapse: collapse; width: 100%; margin: 16px 0;">
                                <tr style="background:#f5f5f5;"><td style="padding:8px; font-weight:bold;">Total Tests</td><td style="padding:8px;">${total}</td></tr>
                                <tr><td style="padding:8px; font-weight:bold; color:#2e7d32;">Passed</td><td style="padding:8px;">${passed}</td></tr>
                                <tr style="background:#f5f5f5;"><td style="padding:8px; font-weight:bold; color:#c62828;">Failed</td><td style="padding:8px;">${failed}</td></tr>
                                <tr><td style="padding:8px; font-weight:bold; color:#f9a825;">Skipped</td><td style="padding:8px;">${skipped}</td></tr>
                                <tr style="background:#f5f5f5;"><td style="padding:8px; font-weight:bold;">Pass Rate</td><td style="padding:8px;">${passRate}%</td></tr>
                            </table>
                            <p>
                                <a href="${env.BUILD_URL}" style="color:#1565c0;">View Build in Jenkins</a><br/>
                                <a href="${env.BUILD_URL}allure" style="color:#1565c0;">View Full Allure Dashboard</a>
                            </p>
                            <p style="color:#777; font-size:13px;">Full HTML report and JUnit results are attached for detailed review.</p>
                        </div>
                    """,
                    mimeType: 'text/html',
                    to: 'shekhar@massistcrm.com',
                    attachmentsPattern: 'report.html,results.xml'
                )
            }
        }
    }
}
