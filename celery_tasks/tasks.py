from celery import Celery
import shutil
import os
import subprocess

app = Celery('tasks', broker='amqp://celery_worker:celery@10.0.15.70:5673//', backend='redis://10.0.15.70:6379')  # Replace 'rabbitmq_host' with your RabbitMQ hostname or IP

@app.task
def add(x, y):
    return x + y 

# @app.task
# def run_prediction(file_name):
#     import subprocess
#     command = f"python /home/ec2-user/data/Merizo/predict.py -d cpu -i {file_name} --iterate --save_domains"
#     subprocess.run(command, shell=True, check=True)

@app.task
def run_merizo(file_name):
    
    # Get parent directory
    parent_dir = os.path.dirname(file_name)
    
    # Get file name without extension 
    file_name_base = os.path.splitext(os.path.basename(file_name))[0]

    # Create output directory
    output_dir = os.path.join(parent_dir, file_name_base)
    os.makedirs(output_dir, exist_ok=True)  
    print("output_dir: ", output_dir)
    print("parent_dir: ", parent_dir)
    # Run prediction
    command = f"python /home/ec2-user/data/Merizo/predict.py -d cpu -i {file_name} --iterate --save_domains"
    subprocess.run(command, shell=True, check=True)

    # Move files to the output directory
    print(f"os.listdir(parent_dir):  {os.listdir(parent_dir)}")
    for filename in os.listdir(parent_dir):
        if filename.startswith(file_name_base):
            print(f"GOT: {filename}")
            source = os.path.join(parent_dir, filename)
            destination = os.path.join(output_dir, filename)
            if os.path.exists(destination):  # Check if exists and remove if so
                os.remove(destination)
            shutil.move(source, output_dir)

    domain_files = []
    # Prepare domain files for pdb_tools (doesn't work with .dom_pdb extension)
    for filename in os.listdir(output_dir):
        if filename.endswith('.dom_pdb'):
            new_filename = filename[:-8] + '.pdb' 
            os.rename(os.path.join(output_dir, filename), 
                      os.path.join(output_dir, new_filename))
            domain_files.append(os.path.join(output_dir, new_filename))
    
    return domain_files

@app.task
def run_pdb_centremass(file_name):
    print("Running Centremass")
    # Get parent directory
    parent_dir = os.path.dirname(file_name)
     # Get file name without extension 
    file_name_base = os.path.splitext(os.path.basename(file_name))[0]

    # Create output directory
    output_dir = os.path.join(parent_dir, file_name_base)
    os.makedirs(output_dir, exist_ok=True)  

    # Run prediction
    command = f"/home/ec2-user/data/pdbtools/scripts/pdb_centermass {file_name} > {output_dir}/centermass.txt"

    subprocess.run(command, shell=True, check=True)

@app.task
def run_pdb_watercontact(file_name):
    # Get parent directory
    print("Running Watercontact")
    print(file_name)
    parent_dir = os.path.dirname(file_name)
     # Get file name without extension 
    file_name_base = os.path.splitext(os.path.basename(file_name))[0]

    # Create output directory
    output_dir = os.path.join(parent_dir, file_name_base)
    os.makedirs(output_dir, exist_ok=True)  

    # Run prediction
    command = f"/home/ec2-user/data/pdbtools/scripts/pdb_watercontact {file_name} > {output_dir}/watercontact.txt"

    subprocess.run(command, shell=True, check=True)
    # for filename in os.listdir(output_dir):
    #     print(filename)
    #     if filename.startswith(file_name_base):
    #         destination = os.path.join(output_dir, filename)
    #         print(f"Destination: {destination}")
    #         if os.path.exists(destination):  # Check if exists and remove if so
    #             os.remove(destination)
    #         shutil.move(filename, output_dir)

    
# @app.task
# def run_pdb_watercontact(file_name):
#/home/ec2-user/data/pdbtools/pdb_watercontact.py


#start:
# celery -A tasks worker --loglevel=INFO --pidfile=celery.pid --logfile=celery.log -D
#stop:
# celery multi stop_verify worker --pidfile=celery.pid --logfile=celery.log