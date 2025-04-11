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
        
def create_netowrk():
    user = os.getenv("USER")
    nets = json.loads(subprocess.getoutput(f'/home/{user}/yandex-cloud/bin/yc vpc network list --format json'))
    net_exists, error, subnet_exists = 0, 0, 0
    if nets:
        for net in nets:
            if net['name'] == "otus":
                net_exists = 1
    if not net_exists:
        logging.info(f'Network otus not found. Creating')
        error += os.system(f'/home/{user}/yandex-cloud/bin/yc vpc network create otus')
        logging.debug(f"Adding network errors: {error}")
        if error:
            logging.error(f'Error while creating netwonk. Do you have limit? Exiting')
            exit(1)
    subnets = json.loads(subprocess.getoutput(f'/home/{user}/yandex-cloud/bin/yc vpc network list-subnets --name otus --format json'))
    if subnets:
        for subnet in subnets:
            if subnet['name'] == "otus":
                subnet_exists = 1
    if not subnet_exists:
        logging.info(f'Subnetwork otus not found. Creating')
        error += os.system(f'/home/{user}/yandex-cloud/bin/yc vpc subnet create --network-name otus --name otus \
                           --zone ru-central1-a --range 172.16.172.0/24')
        logging.debug(f"Adding subnet errors: {error}")
        if error:
            logging.error(f'Error while creating subnetwonk. Exiting')
            exit(1)
    
        
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
                    logging.info(f'Cluster stopped. Starting...')
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
    security_groups = json.loads(subprocess.getoutput(f'/home/{user}/yandex-cloud/bin/ycyc vpc network list-security-groups \
                                                      --name otus --format json'))
    for security in security_groups:
        if security['name'].startswith("default"):
            secutity_group = security['id']
    if not nodes_exist:
        logging.info(f'There is no nodes in cluster with name {cluster_name}, creating...')
        creation = subprocess.getoutput(f'/home/{user}/yandex-cloud/bin/yc managed-kubernetes node-group create \
                                        --cluster-name {cluster_name} --cores 4 --disk-size 40GB --disk-type network-nvme \
                                        --fixed-size {nodes} --memory 8GB --name {cluster_name}\
                                        --network-interface security-group-ids={secutity_group},subnets=otus,ipv4-address=nat \
                                        --network-acceleration-type standard --container-runtime containerd  \
                                        --node-name {cluster_name}-node-' + '{instance.index} --format json')
        logging.debug(f"Creation \n{creation}")
        start_of_json = creation.find("{")
        json_creation = json.loads(creation[start_of_json:])
        json_creation = json.loads(creation)
        logging.debug(f"Creation json {json_creation}")


def install_kubectl():
    if not os.path.exists('/usr/local/bin/kubectl'):
        logging.info(f'No kubectl installed. Installing...')
        error = 0
        error += os.system('curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"')
        logging.debug(f"Download kubectl errors: {error}")
        error += os.system('sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl')
        logging.debug(f"Installed kubectl errors: {error}")
        os.system('rm kubectl')
        if error:
            return False
    return True
    
def install_helm():
    if not os.path.exists('/usr/local/bin/helm'):
        logging.info(f'No helm installed. Installing...')
        error = 0
        error += os.system('curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3')
        logging.debug(f"Download helm errors: {error}")
        os.system('chmod 700 get_helm.sh')
        error += os.system('./get_helm.sh')
        logging.debug(f"Installed helm errors: {error}")
        os.system('rm get_helm.sh')     
        if error:
            return False
    return True

def main():
    user = os.getenv("USER")
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
        create_netowrk()
        create_cluster(config["name"], int(config["nodes"]))
    except Exception as e:
        print(f'Error while creating cluster: {e}')
    if not install_kubectl():
        logging.error("Error while installing kubectl. Exiting")
        exit(1)
    if not install_helm():
        logging.error("Error while installing helm. Exiting")
        exit(1)
    error = os.system(f'/home/{user}/yandex-cloud/bin/yc managed-kubernetes cluster get-credentials --external --name {config["name"]} --force')
    if error:
        logging.error("Error taking config from yc. Exiting")
        exit(1)
    


if __name__ == "__main__":
    main()

