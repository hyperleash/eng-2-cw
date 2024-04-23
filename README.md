# eng-2-cw
# Setup Guide

This guide outlines the steps required to set up a distributed analysis system for proteome analysis using Ansible. 
The setup process involves preparing the control node, preparing the necessary SSH keys, cloning the repository, and running the analysis pipeline.

## Step 1: Connect to the Control Node

Make sure you have the lecturer key used during the cluster creating. Then use the following command:
```bash
ssh -i path/to/key ec2-user@<instance_address>
```

## Step 2: Copy the private lecturer key to the control node
This is required so that the control node can access the workers

```bash
scp path/to/comp0239_key ec2-user@<instance_address>:~/.ssh/comp0239_key
```

## Step 3: Install the required packages onto the control node
This installs python, pip, git, and ansible onto the control node

```bash
sudo yum update -y

sudo yum install -y python3 git

sudo yum install -y python3-pip

sudo pip3 install ansible
```


## Step 4: Clone the coursework github repository
To clone the repository and put all of the required code on the control node run this command:
```bash
git clone https://github.com/hyperleash/eng-2-cw.git
```

## Step 5: Add the lecturer key to your ssh-agent
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/comp0239_key

```
## Step 6: Create and distribute a new key pair (modify the inventory file with the according IPs)

```bash
cd eng-2-cw
ansible-playbook distribute_keys.yaml -i inventory.yaml -e 'ansible_ssh_private_key_file=~/.ssh/comp0239_key'
```

## STEP 7: Add the correct internal client IP where required (if a new cluster was created)
- In the NFS fstab task in master_playbook.yaml
- In eng-2-cw/celery_tasks/tasks.py in Celery app creation (line 9)
- In eng-2-cw/web_app/app.py for Redis backend IP
  
## Step 8: Run the master playbook to configure the cluster
```bash
cd eng-2-cw
ansible-playbook master_playbook.yaml -i inventory.yaml
```

# Running the web app

The easiest way to do this seems to be through VSCode
## Step 1: Add the following ssh config
```bash
Host CLIENT
   HostName 3.9.175.144
   User ec2-user
   IdentityFile ~/.ssh/comp0239_key
```
## Step 2: Connect to CLIENT through VSCode and start the flask app:
```bash
source /home/ec2-user/data/celery_venv/bin/activate
cd /home/ec2-user/data/web_app/
flask run
```

## Step 3: VSCode should offer to open the page in the browser

## Step 4: Use small_test.zip and big_test.zip example input archives to test the app
