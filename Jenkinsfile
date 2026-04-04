// CD Pipeline: Build Image → Push ECR → Deploy EKS
//
// 前提條件（一次性設定）：
//   1. ECR repo 建立：aws ecr create-repository --repository-name app-login-service --region ap-northeast-1
//   2. Jenkins EC2 IAM role 需要 ECR push 權限：
//      將 AmazonEC2ContainerRegistryReadOnly 改為 AmazonEC2ContainerRegistryPowerUser
//   3. Jenkins 節點需安裝 Docker（EC2 上執行：sudo yum install -y docker && sudo systemctl start docker）
//   4. K8s Secret 建立：
//      kubectl create secret generic app-login-service-secret \
//        --from-literal=SECRET_KEY=$(openssl rand -hex 32) \
//        --from-literal=DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/logindb \
//        --from-literal=ENVIRONMENT=production

pipeline {
    agent any

    environment {
        AWS_REGION    = "ap-northeast-1"
        CLUSTER_NAME  = "main-eks"
        IMAGE_NAME    = "app-login-service"
        K8S_NAMESPACE = "default"
        SSM_CERT_PATH = "/shared/wildcard-cert-arn"
    }

    stages {
        stage('Setup') {
            steps {
                script {
                    env.GIT_COMMIT_SHORT = sh(
                        script: "git rev-parse --short HEAD",
                        returnStdout: true
                    ).trim()
                    env.IMAGE_TAG = env.GIT_COMMIT_SHORT
                    env.AWS_ACCOUNT_ID = sh(
                        script: "aws sts get-caller-identity --query Account --output text",
                        returnStdout: true
                    ).trim()
                    env.ECR_REGISTRY = "${env.AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                    env.IMAGE_FULL    = "${env.ECR_REGISTRY}/${IMAGE_NAME}:${env.IMAGE_TAG}"
                    echo "Building image: ${env.IMAGE_FULL}"
                }
            }
        }

        stage('Build & Push ECR') {
            steps {
                sh """
                    aws ecr get-login-password --region ${AWS_REGION} | \
                        docker login --username AWS --password-stdin ${env.ECR_REGISTRY}

                    docker buildx build \
                        --platform linux/amd64 \
                        -t ${env.IMAGE_FULL} \
                        -t ${env.ECR_REGISTRY}/${IMAGE_NAME}:latest \
                        --push .
                """
            }
        }

        stage('Configure kubectl') {
            steps {
                sh "aws eks update-kubeconfig --name ${CLUSTER_NAME} --region ${AWS_REGION}"
            }
        }

        stage('Read SSM Parameters') {
            steps {
                script {
                    env.WILDCARD_CERT_ARN = sh(
                        script: "aws ssm get-parameter --name ${SSM_CERT_PATH} --region ${AWS_REGION} --query Parameter.Value --output text",
                        returnStdout: true
                    ).trim()
                }
            }
        }

        stage('Deploy') {
            steps {
                sh """
                    IMAGE_FULL=${env.IMAGE_FULL} \
                    envsubst < k8s/deployment.yaml | kubectl apply -f -

                    WILDCARD_CERT_ARN=${env.WILDCARD_CERT_ARN} \
                    envsubst < k8s/ingress.yaml | kubectl apply -f -
                """
                sh """
                    kubectl rollout status deployment/${IMAGE_NAME} \
                        -n ${K8S_NAMESPACE} --timeout=120s
                """
            }
        }

        stage('Verify') {
            steps {
                sh "kubectl get pods -l app=${IMAGE_NAME} -n ${K8S_NAMESPACE}"
                sh "kubectl get svc ${IMAGE_NAME} -n ${K8S_NAMESPACE}"
                sh "kubectl get ingress ${IMAGE_NAME} -n ${K8S_NAMESPACE}"
            }
        }
    }

    post {
        failure {
            echo "Deployment failed — rolling back"
            sh "kubectl rollout undo deployment/${IMAGE_NAME} -n ${K8S_NAMESPACE} || true"
        }
        always {
            sh "docker rmi ${env.IMAGE_FULL} || true"
        }
    }
}
