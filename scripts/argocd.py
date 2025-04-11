import json
import subprocess
import os
import logging


logging.basicConfig(level="DEBUG")

def install_argocd():
    logging.debug(f"Installing argocd")
    installed = subprocess.getoutput('helm list -n argocd -o json')
    if not installed:
        error = 0
        logging.debug(f"No argocd found. Installing...")
        error += os.system('helm repo add argo https://argoproj.github.io/argo-helm')
        logging.debug(f'Adding repo, errors: {error}')
        error += os.system('helm install argocd argo/argo-cd -n argocd -f values/argocd-values.yaml --create-namespace --wait')
        logging.debug(f'Installing argo, errors: {error}')
    os.system('kubectl apply -f app-of-apps.yaml')

def main():
    install_argocd()

if __name__ == "__main__":
    main()

