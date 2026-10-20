stage('Minikube Deployment') {
    steps {
        withCredentials([file(credentialsId: 'minikube-kubeconfig', variable: 'KUBECONFIG')]) {
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
    raise SystemExit("Expected one newName/newTag in Kustomization and one APP_VERSION value in Deployment")

path.write_text(text, encoding="utf-8")
deployment_path.write_text(deployment_text, encoding="utf-8")
PY

                kubectl apply -n "$K8S_NAMESPACE" -k "$render_dir"
                kubectl rollout status -n "$K8S_NAMESPACE" deployment/campus-task-board --timeout=180s
            '''
        }
    }
}
