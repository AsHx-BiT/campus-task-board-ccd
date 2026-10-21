pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    def imageRepo = env.IMAGE_REPO?.trim()
                    if (!imageRepo ||
                        !imageRepo.startsWith('docker.io/') ||
                        imageRepo.contains(':') ||
                        imageRepo.contains('your-dockerhub-username')) {
                        error('Set IMAGE_REPO to docker.io/<your-dockerhub-username>/campus-task-board (without a tag or port).')
                    }

                    env.IMAGE_REPO = imageRepo
                    env.IMAGE_TAG = sh(
                        script: 'git rev-parse HEAD',
                        returnStdout: true
                    ).trim()
                    env.K8S_NAMESPACE = env.K8S_NAMESPACE?.trim() ?: 'default'
                    env.MINIKUBE_PROFILE = env.MINIKUBE_PROFILE?.trim() ?: 'minikube'

                    echo "Building commit ${env.IMAGE_TAG} for ${env.IMAGE_REPO}"
                }
            }
        }

        stage('Build and Test') {
            steps {
                sh 'python3 --version'
                sh 'python3 -m compileall -q app.py test_app.py'
                sh 'python3 -m unittest -v'
            }
        }

        stage('Docker Build') {
            steps {
                sh 'docker version'
                sh 'docker build --pull --tag "$IMAGE_REPO:$IMAGE_TAG" .'
            }
        }

        stage('Docker Push') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-credentials',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_TOKEN'
                    )
                ]) {
                    sh '''
                        set +x
                        trap 'docker logout >/dev/null 2>&1 || true' EXIT
                        printf '%s' "$DOCKER_TOKEN" |
                            docker login --username "$DOCKER_USER" --password-stdin >/dev/null
                        docker push "$IMAGE_REPO:$IMAGE_TAG"
                    '''
                }
            }
        }

        stage('Minikube Deployment') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'minikube-kubeconfig',
                        variable: 'KUBECONFIG'
                    )
                ]) {
                    sh '''
                        set -eu

                        command -v minikube >/dev/null
                        command -v kubectl >/dev/null

                        minikube status --profile "$MINIKUBE_PROFILE"

                        current_context=$(kubectl config current-context)
                        if [ "$current_context" != "$MINIKUBE_PROFILE" ]; then
                            echo "KUBECONFIG context '$current_context' does not match Minikube profile '$MINIKUBE_PROFILE'." >&2
                            exit 1
                        fi

                        echo "Using Minikube context: $current_context"
                        kubectl get nodes

                        render_dir=$(mktemp -d)
                        cp k8s/deployment.yaml k8s/service.yaml k8s/kustomization.yaml "$render_dir/"
                        trap 'rm -rf "$render_dir"' EXIT

                        python3 - "$render_dir/kustomization.yaml" <<'PY'
import os
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

text, repo_count = re.subn(
    r"(?m)^(\\s*newName:\\s*).+$",
    lambda match: match.group(1) + os.environ["IMAGE_REPO"],
    text,
    count=1,
)

text, tag_count = re.subn(
    r"(?m)^(\\s*newTag:\\s*).+$",
    lambda match: match.group(1) + '"' + os.environ["IMAGE_TAG"] + '"',
    text,
    count=1,
)

deployment_path = path.parent / "deployment.yaml"
deployment_text = deployment_path.read_text(encoding="utf-8")

deployment_text, version_count = re.subn(
    r"(?m)^(\\s*value:\\s*).+$",
    lambda match: match.group(1) + '"' + os.environ["IMAGE_TAG"] + '"',
    deployment_text,
    count=1,
)

if repo_count != 1 or tag_count != 1 or version_count != 1:
    raise SystemExit(
        "Expected one newName/newTag in Kustomization and "
        "one APP_VERSION value in Deployment"
    )

path.write_text(text, encoding="utf-8")
deployment_path.write_text(deployment_text, encoding="utf-8")
PY

                        kubectl apply -n "$K8S_NAMESPACE" -k "$render_dir"
                        kubectl rollout status -n "$K8S_NAMESPACE" \
                            deployment/campus-task-board --timeout=180s
                    '''
                }
            }
        }

        stage('Verification') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'minikube-kubeconfig',
                        variable: 'KUBECONFIG'
                    )
                ]) {
                    sh '''
                        set -eu

                        kubectl wait -n "$K8S_NAMESPACE" \
                            --for=condition=Available \
                            deployment/campus-task-board \
                            --timeout=180s

                        kubectl wait -n "$K8S_NAMESPACE" \
                            --for=condition=Ready \
                            pods -l app=campus-task-board \
                            --timeout=180s

                        kubectl get deployment campus-task-board -n "$K8S_NAMESPACE"
                        kubectl get pods,service,endpoints \
                            -n "$K8S_NAMESPACE" \
                            -l app=campus-task-board

                        deployed_image=$(kubectl get deployment campus-task-board \
                            -n "$K8S_NAMESPACE" \
                            -o jsonpath='{.spec.template.spec.containers[?(@.name=="web")].image}')

                        expected_image="$IMAGE_REPO:$IMAGE_TAG"
                        if [ "$deployed_image" != "$expected_image" ]; then
                            echo "Expected image $expected_image, found $deployed_image" >&2
                            exit 1
                        fi

                        port_forward_log=$(mktemp)
                        kubectl port-forward -n "$K8S_NAMESPACE" \
                            service/campus-task-board 18080:8080 \
                            >"$port_forward_log" 2>&1 &
                        port_forward_pid=$!

                        cleanup() {
                            kill "$port_forward_pid" >/dev/null 2>&1 || true
                            rm -f "$port_forward_log"
                        }
                        trap cleanup EXIT

                        attempt=0
                        until curl --fail --silent \
                            http://127.0.0.1:18080/health >/dev/null; do
                            attempt=$((attempt + 1))
                            if [ "$attempt" -ge 30 ] ||
                               ! kill -0 "$port_forward_pid" 2>/dev/null; then
                                cat "$port_forward_log" >&2
                                echo 'Application health endpoint did not become ready.' >&2
                                exit 1
                            fi
                            sleep 2
                        done

                        curl --fail --silent --show-error \
                            http://127.0.0.1:18080/health

                        curl --fail --silent --show-error \
                            http://127.0.0.1:18080/api/tasks |
                            python3 -c 'import json, os, sys; data=json.load(sys.stdin); assert data["version"] == os.environ["IMAGE_TAG"], data; assert data["tasks"], data'
                    '''
                }
            }
        }
    }

    post {
        always {
            script {
                if (env.IMAGE_REPO?.trim() && env.IMAGE_TAG?.trim()) {
                    sh 'docker image rm "$IMAGE_REPO:$IMAGE_TAG" >/dev/null 2>&1 || true'
                }
            }
        }
    }
}
