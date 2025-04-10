import json
import subprocess
import os
import logging


logging.basicConfig(level="DEBUG")

def install_argocd():
    installed = subprocess.getoutput('helm list -A -o json')
    os.system('helm repo add argo https://argoproj.github.io/argo-helm')
    os.system('helm install argocd argo/argo-cd -n argocd -f values/argocd-values.yaml --create-namespace')


def main():
    install_argocd()

if __name__ == "__main__":
    main()

