pipeline {
    agent any

    environment {
        IMAGE_NAME = "smart-lab-color-predictor"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Install & Test') {
            steps {
                sh 'python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt && python -m pytest -v'
            }
        }
        stage('Build Docker Image') {
            steps {
                sh "docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} ."
            }
        }
    }
}
