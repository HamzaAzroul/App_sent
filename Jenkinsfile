pipeline {
    agent any

    environment {
        // Image Docker sans le double tag ":app:latest", on garde une seule référence de tag
        DOCKER_IMAGE = "hamzaazroul/app_sent2"
        IMAGE_TAG = "latest"  // Tu peux remplacer par un SHA de commit si besoin
    }

    stages {
        stage('Build') {
            steps {
                sh "docker build -t ${DOCKER_IMAGE}:${IMAGE_TAG} ./backend"
            }
        }

        stage('Test') {
            steps {
                sh "docker run --rm ${DOCKER_IMAGE}:${IMAGE_TAG} tests/"
            }
        }

        stage('Push') {
            steps {
                withCredentials([string(credentialsId: 'docker-hub-token', variable: 'DOCKER_TOKEN')]) {
                    sh "echo $DOCKER_TOKEN | docker login -u hamzaazroul --password-stdin"
                }
                sh "docker push ${DOCKER_IMAGE}:${IMAGE_TAG}"
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                sh "kubectl apply -f ."
                sh "kubectl apply -f ./k8s/"
            }
        }

        stage('Monitor') {
            steps {
                sh "kubectl apply -f ."
                sh "kubectl apply -f ./k8s/"
            }
        }
    }
}
