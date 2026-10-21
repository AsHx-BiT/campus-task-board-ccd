# Campus Task Board - CCA 2 CI/CD project

A small, dependency-free student task board used to demonstrate the required Jenkins, Docker Hub, and Minikube pipeline. It serves a web page where you can add a task and choose its status, a JSON tasks endpoint, and a health endpoint. Added tasks remain in memory until the app process restarts. The container runs as a non-root user.

> **Assignment requirement:** the guide says to use an existing academic project. This workspace did not contain one, so this is a ready-to-run demonstration project, not evidence of a project you built earlier. To meet that requirement, use this pipeline structure with your own earlier academic project's source code, or confirm that your instructor accepts a new demo project.

## Repository contents

- `app.py`, `test_app.py` - application and standard-library unit tests
- `Dockerfile`, `.dockerignore` - container image
- `Jenkinsfile` - declarative checkout, test, build, registry push, and deploy pipeline
- `k8s/` - Kubernetes Deployment and NodePort Service

## Run locally

Requires Python 3.10+ and Docker.

```sh
python3 -m unittest -v
python3 app.py
```

Open `http://localhost:8080`, enter a task name, choose `To do`, `In progress`, or `Done`, and select **Add task**. The board and status counts update immediately. The API is at `/api/tasks`; send a JSON `POST` to add a task, and `/health` returns `ok`.
The server binds to `0.0.0.0` for container access. Set `PORT` to choose its listening port and `APP_VERSION` to change the version shown by the API and page. The app has no database or secret configuration.

Build and run the container:

```sh
docker build -t campus-task-board:local .
docker run --rm -p 8080:8080 campus-task-board:local
```

## Jenkins pipeline setup

The root `Jenkinsfile` builds and pushes Docker Hub images tagged with the full Git commit SHA, then deploys and verifies that exact image on Minikube.

1. Push this repository to GitHub.
2. Use a Linux Jenkins agent with Python 3, Docker CLI and a running Docker daemon, `kubectl`, `minikube`, and `curl` on `PATH`. The agent account must be able to access the Docker daemon. Run Minikube under the same OS account as the Jenkins agent (or make its profile/config accessible to that account). Confirm `minikube status --profile minikube` and `kubectl get nodes` work as that account. The kubeconfig credential must point to this same reachable Minikube cluster.
3. Install the Jenkins **Pipeline**, **Git**, and **Credentials Binding** plugins. Install the GitHub plugin only if using GitHub webhooks; SCM polling does not require that plugin.
4. Add these credentials in **Manage Jenkins → Credentials**:
   - `dockerhub-credentials`: Username with password, where the password is a Docker Hub access token.
   - `minikube-kubeconfig`: Secret file containing a kubeconfig for the target Minikube cluster, including certificates/credentials rather than workstation-only file paths. Its current context name must match `MINIKUBE_PROFILE`.
   - To prepare the kubeconfig on the Jenkins agent as the Jenkins OS account, select the Minikube context and flatten its credentials to a file outside the repository, then upload that file as the secret-file credential:
     ```sh
     kubectl config use-context minikube
     kubectl config view --raw --minify --flatten > "$HOME/minikube-kubeconfig"
     ```
5. Set Jenkins job or agent environment variables:
   - `IMAGE_REPO` (required), for example `docker.io/my-dockerhub-user/campus-task-board`; omit the tag because Jenkins appends the commit SHA.
   - `K8S_NAMESPACE` (optional; defaults to `default`).
   - `MINIKUBE_PROFILE` (optional; defaults to `minikube`).
   If using a namespace other than `default`, create it in Minikube before the first run.
6. For a public Docker Hub repository, no Kubernetes pull secret is needed. For a private repository, create a `kubernetes.io/dockerconfigjson` Secret in the selected namespace and uncomment `imagePullSecrets` in `k8s/deployment.yaml`. Jenkins' push credential does not give Minikube pull access. Keep all tokens and kubeconfig files out of Git.
7. Create a Jenkins **Pipeline** job using **Pipeline script from SCM**, your GitHub URL, and script path `Jenkinsfile`. Configure a GitHub webhook at `http://<jenkins-host>:8080/github-webhook/` or enable SCM polling.

The pipeline checks Docker daemon access during the image build and runs `minikube status`, `kubectl config current-context`, and `kubectl get nodes` before deployment. If these checks fail, correct the Jenkins agent's access or kubeconfig; the pipeline intentionally stops instead of deploying to an unreachable cluster. Restrict access to Jenkins and the Docker daemon to the required users.

## Configure the image and deploy to Minikube

The app has no database or persistent files, so it needs no database credentials or PersistentVolumeClaim. The Deployment uses the public Docker Hub image by default; configure `k8s/kustomization.yaml` before deploying:

```yaml
images:
  - name: campus-task-board
    newName: docker.io/YOUR_DOCKERHUB_USERNAME/campus-task-board
    newTag: "1.0.0"
```

Use a unique image tag for each release (the Jenkins pipeline uses the full Git commit SHA). For manual ECR deployment, set `newName` to `ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/campus-task-board`. Public Docker Hub images need no pull secret. For private Docker Hub or ECR images, create a `kubernetes.io/dockerconfigjson` Secret in the same namespace, then uncomment `imagePullSecrets` in the pod template in `k8s/deployment.yaml`. Keep registry credentials outside Git. ECR authorization tokens expire, so refresh the Secret before its token expires. The provided Jenkins push stage is configured for Docker Hub; ECR publishing requires changing that stage to authenticate with AWS ECR.

Start Minikube and make sure kubectl is using its context. Apply the Kustomize resources:

```sh
minikube start
kubectl config current-context
kubectl apply -k k8s/
kubectl rollout status deployment/campus-task-board --timeout=180s
```

## Verify on Minikube

Run on a machine with access to the same cluster:

```sh
kubectl get deployment campus-task-board
kubectl get pods -l app=campus-task-board
kubectl get service campus-task-board
kubectl get endpoints campus-task-board
minikube service campus-task-board --url
```

Open the printed URL and verify that the Campus Task Board page loads. You can also check the health endpoint at `<printed-url>/health`. Capture screenshots of the successful Jenkins stages, running pod/service, and app page. If the Jenkins host is remote, run the commands with that host's Minikube context or securely forward the app URL for the live demo.

## Demonstrate the second run

Change a visible string in `app.py` (for example, the introductory sentence in `PAGE`), commit and push to GitHub, then let the Jenkins job run again. The Git commit SHA creates the new image tag and is also set as `APP_VERSION` on the deployment, so the footer displays the deployed commit. Save screenshots of the code change/commit and the second successful rollout.

## Submission checklist

- GitHub repository URL
- `Jenkinsfile`, `Dockerfile`, and `k8s/` manifests
- screenshots from both successful pipeline runs and live app verification
- a short report with your project choice, AWS/Jenkins setup, pipeline stages, registry push, Minikube deployment, access method, and second-run source change

Screenshots and a real deployment report are intentionally left for capture from your own AWS/Jenkins/Minikube environment; none are fabricated here.
