import json
import subprocess
import os
import logging


logging.basicConfig(level="DEBUG")

def install_yc():
    user = os.getenv("USER")
    if os.path.exists(f"/home/{user}/yandex-cloud/bin/yc"):
        return True
    returned = os.system('curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash')
    if not returned:
        return True
    return False

def yc_login():
    user = os.getenv("USER")
    profiles = subprocess.getoutput(f'/home/{user}/yandex-cloud/bin/yc config profile list')
    logging.debug(f"Profiles: {profiles}")
    if not profiles or not 'otus' in profiles:
        error = 0
        error += os.system(f'/home/{user}/yandex-cloud/bin/yc config profile create otus')
        logging.debug(f"Creating profile errors: {error}")
        if not error:
            secret = os.getenv('SECRET')
            secret.replace('\n', '\\n')
            with open('temp_key.json', 'w') as file:
                file.write(secret)
            logging.debug(f"Adding file errors: {error}")
            error += os.system(f'/home/{user}/yandex-cloud/bin/yc config set service-account-key temp_key.json')
            logging.debug(f"Adding key errors: {error}")
            error += os.system('rm temp_key.json')
            logging.debug(f"Removing file errors: {error}")
            if not error:
                error += os.system(f'/home/{user}/yandex-cloud/bin/yc config set cloud-id $CLOUD')
                logging.debug(f"Adding cloud errors: {error}")
                error += os.system(f'/home/{user}/yandex-cloud/bin/yc config set folder-id $FOLDER')
                logging.debug(f"Adding folder errors: {error}")
        if error:
            raise Exception 
        
def create_cluster(cluster_name: str, nodes: int):
    user = os.getenv("USER")
    clusters = json.loads(subprocess.getoutput(f'/home/{user}/yandex-cloud/bin/yc managed-kubernetes cluster list --format json'))
    logging.debug(f'{clusters}')
    cluster_exists = 0
    if clusters:
        for cluster in clusters:
            if cluster['name'] == cluster_name:
                cluster_exists = 1
                if cluster['status'] == "STOPPED":

                    os.system(f'/home/{user}/yandex-cloud/bin/yc managed-kubernetes cluster start --name {cluster_name}')
                    logging.debug(f"Starting cluster")
    if not cluster_exists:
        logging.info(f'There is no cluster with name {cluster_name}, creating...')
        creation = subprocess.getoutput(f'/home/{user}/yandex-cloud/bin/yc managed-kubernetes cluster create \
                                    --name {cluster_name} --network-name otus \
                                    --service-account-name k8s --node-service-account-name k8s --subnet-name otus \
                                    --zone ru-central1-a --cluster-ipv4-range "172.17.0.0/16" --service-ipv4-range \
                                    "172.18.0.0/16" --public-ip --version 1.31 --format json')
        logging.debug(f"Creation cluster: \n {creation}")
        start_of_json = creation.find("{")
        json_creation = json.loads(creation[start_of_json:])
        logging.debug(f"Creation json {json_creation}")
    nodes_exist = json.loads(subprocess.getoutput(f'/home/{user}/yandex-cloud/bin/yc managed-kubernetes node-group list --format json'))
    if not nodes_exist:
        logging.info(f'There is no nodes in cluster with name {cluster_name}, creating...')
        creation = subprocess.getoutput(f'/home/{user}/yandex-cloud/bin/yc managed-kubernetes node-group create \
                                        --cluster-name {cluster_name} --cores 4 --disk-size 40GB --disk-type network-nvme \
                                        --fixed-size {nodes} --location zone=ru-central1-a,subnet-name=otus --memory 8GB \
                                        --name {cluster_name} --network-acceleration-type standard \
                                        --container-runtime containerd --node-name {cluster_name}-node-' + '{instance.index}')
        logging.debug(f"Creation \n{creation}")
        start_of_json = creation.find("{")
        json_creation = json.loads(creation[start_of_json:])
        json_creation = json.loads(creation)
        logging.debug(f"Creation json {json_creation}")

def main():
    if not install_yc():
        logging.error(f"Can't install Yandex cli. Exiting")
        exit(1)
    if not os.path.exists("cluster.json"):
        logging.error(f"No cluster.json file in repo. Exiting")
        exit(1)
    with open("cluster.json", "r") as file:
        config = json.loads(file.read())
    if not "name" in config:
        logging.error(f"No name in config. Exiting")
        exit(1)
    if not "nodes" in config:
        logging.error(f"No nodes in config. Exiting")
        exit(1)
    try:
        yc_login()
        create_cluster(config["name"], int(config["nodes"]))
    except Exception as e:
        print(f'Error while running script: {e}')
    finally:
        finalizer()
        

def finalizer():
    os.system('/usr/bin/yc config unset cloud-id')
    os.system('/usr/bin/yc config unset service-account-key')
    os.system('/usr/bin/yc config unset folder-id')
    

if __name__ == "__main__":
    main()

