// CD Pipeline: Build Image → Push ECR → Deploy EKS
//
// 前提條件（一次性設定）：
//   1. ECR repo 建立：aws ecr create-repository --repository-name app-login-service --region ap-northeast-1
//   2. jenkins-agent IRSA 需要 ECR push 權限（見 infra/k8s/jenkins-agent-irsa.tf）
//   3. K8s Secret 建立：
//      kubectl create secret generic app-login-service-secret \
//        --from-literal=SECRET_KEY=$(openssl rand -hex 32) \
//        --from-literal=DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/logindb \
//        --from-literal=ENVIRONMENT=production

pipeline {
    agent {
        kubernetes {
            namespace 'jenkins-agents'
            yaml """
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: jenkins-agent
  containers:
  - name: jnlp
    image: jenkins/inbound-agent:latest
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
  - name: aws-tools
    image: 677856867919.dkr.ecr.ap-northeast-1.amazonaws.com/jenkins:latest
    imagePullPolicy: Always
    command: ["sleep", "infinity"]
    resources:
      requests:
        cpu: 200m
        memory: 512Mi
  - name: kaniko
    image: gcr.io/kaniko-project/executor:debug
    command: ["sleep", "infinity"]
    resources:
      requests:
        cpu: 500m
        memory: 1Gi
"""
        }
    }

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
                container('aws-tools') {
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
        }

        stage('Build & Push ECR') {
            steps {
                container('kaniko') {
                    sh """
                        /kaniko/executor \
                            --context=dir:///home/jenkins/agent/workspace/${env.JOB_NAME} \
                            --dockerfile=Dockerfile \
                            --destination=${env.IMAGE_FULL} \
                            --destination=${env.ECR_REGISTRY}/${IMAGE_NAME}:latest \
                            --cache=true
                    """
                }
            }
        }

        stage('Configure kubectl') {
            steps {
                container('aws-tools') {
                    sh "aws eks update-kubeconfig --name ${CLUSTER_NAME} --region ${AWS_REGION} --kubeconfig /tmp/kubeconfig"
                }
            }
        }

        stage('Read SSM Parameters') {
            steps {
                container('aws-tools') {
                    script {
                        env.WILDCARD_CERT_ARN = sh(
                            script: "aws ssm get-parameter --name ${SSM_CERT_PATH} --region ${AWS_REGION} --query Parameter.Value --output text",
                            returnStdout: true
                        ).trim()
                    }
                }
            }
        }

        stage('Deploy') {
            steps {
                container('aws-tools') {
                    sh """
                        export KUBECONFIG=/tmp/kubeconfig
                        IMAGE_FULL=${env.IMAGE_FULL} \
                        envsubst < k8s/deployment.yaml | kubectl apply -f -

                        WILDCARD_CERT_ARN=${env.WILDCARD_CERT_ARN} \
                        envsubst < k8s/ingress.yaml | kubectl apply -f -
                    """
                    sh """
                        export KUBECONFIG=/tmp/kubeconfig
                        kubectl rollout status deployment/${IMAGE_NAME} \
                            -n ${K8S_NAMESPACE} --timeout=120s
                    """
                }
            }
        }

        stage('Verify') {
            steps {
                container('aws-tools') {
                    sh """
                        export KUBECONFIG=/tmp/kubeconfig
                        kubectl get pods -l app=${IMAGE_NAME} -n ${K8S_NAMESPACE}
                        kubectl get svc ${IMAGE_NAME} -n ${K8S_NAMESPACE}
                        kubectl get ingress ${IMAGE_NAME} -n ${K8S_NAMESPACE}
                    """
                }
            }
        }
    }

    post {
        failure {
            container('aws-tools') {
                sh "export KUBECONFIG=/tmp/kubeconfig && kubectl rollout undo deployment/${IMAGE_NAME} -n ${K8S_NAMESPACE} || true"
            }
        }
    }
}
