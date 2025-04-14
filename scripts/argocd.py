import json
import subprocess
import os
import logging


logging.basicConfig(level="INFO")

def main():
    logging.debug(f"Installing argocd")
    installed = json.loads(subprocess.getoutput('/usr/local/bin/helm list -n argocd -o json'))
    logging.debug(f'Helm list: {installed}')
    if not installed:
        error = 0
        logging.info(f"No argocd found. Installing...")
        error += os.system('/usr/local/bin/helm repo add argo https://argoproj.github.io/argo-helm')
        logging.debug(f'Adding repo, errors: {error}')
        error += os.system('/usr/local/bin/helm install argocd argo/argo-cd -n argocd -f values/argocd-values.yaml --create-namespace --wait')
        logging.debug(f'Installing argo, errors: {error}')
    logging.info(f'Adding app of apps.')
    os.system('/usr/local/bin/kubectl apply -f app-of-apps.yaml')


if __name__ == "__main__":
    main()
