pipeline {
    agent any
    options {
        timeout(time: 30, unit: 'MINUTES')
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Install & Lint') {
            steps {
                dir('backend') {
                    sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install -r requirements.txt flake8 bandit pip-audit
                    flake8 app tests --max-line-length=100
                    '''
                }
            }
        }
        stage('Unit Tests + Coverage') {
            steps {
                dir('backend') {
                    sh '''
                    . .venv/bin/activate
                    pytest --cov=app --cov-branch \
                           --cov-report=xml --cov-report=html \
                           --cov-fail-under=75 \
                           --junitxml=test-results.xml
                    '''
                }
            }
            post {
                always {
                    junit 'backend/test-results.xml'
                    archiveArtifacts artifacts: 'backend/htmlcov/**', allowEmptyArchive: true
                }
            }
        }
        stage('SonarQube Analysis') {
            steps {
                script {
                    def scannerHome = tool 'sonar-scanner'
                    withSonarQubeEnv('sonarqube') {
                        sh "${scannerHome}/bin/sonar-scanner"
                    }
                }
            }
        }
        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }
        stage('Security Scans') {
            steps {
                dir('backend') {
                    sh '''
                    . .venv/bin/activate
                    bandit -r app -ll
                    pip-audit -r requirements.txt
                    '''
                }
            }
        }
        stage('Build Image') {
            steps {
                sh 'docker build -t capstone-backend:${BUILD_NUMBER} backend'
            }
        }
        stage('Deploy') {
            when { branch 'main' }
            steps {
                sh 'docker compose up -d --build db backend'
            }
        }
        stage('Smoke Test') {
            when { branch 'main' }
            steps {
                sh '''
                sleep 10
                docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
                '''
            }
        }
    }
    post {
        failure {
            echo 'Build failed; check the stage logs above.'
        }
    }
}