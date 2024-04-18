from celery import Celery
import shutil
import os
import subprocess

app = Celery('tasks', broker='amqp://celery_worker:celery@10.0.15.70:5673//', backend='redis://10.0.15.70:6379')  # Replace 'rabbitmq_host' with your RabbitMQ hostname or IP
app.conf.task_prefetch_count = 2

@app.task
def add(x, y):
    return x + y 

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
    command = f"/home/ec2-user/data/celery_venv/bin/python /home/ec2-user/data/Merizo/predict.py -d cpu -i {file_name} --iterate --save_domains"
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
    command = f"/home/ec2-user/data/celery_venv/bin/python /home/ec2-user/data/pdbtools/scripts/pdb_centermass {file_name} > {output_dir}/centermass.txt"

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
    command = f"/home/ec2-user/data/celery_venv/bin/python /home/ec2-user/data/pdbtools/scripts/pdb_watercontact {file_name} > {output_dir}/watercontact.txt"

    subprocess.run(command, shell=True, check=True)

@app.task
def run_pipeline(directory_path):
    pdb_files = [os.path.join(args.directory_path, file) for file in os.listdir(args.directory_path) if file.endswith('.pdb')]

    merizo_job = group(run_merizo.s(file_path) for file_path in pdb_files)
    merizo_results = merizo_job.apply_async()
    paths = merizo_results.get()

    domain_file_paths = [path for result in paths for path in result] 

    centermass_tasks = [run_pdb_centremass.s(path) for path in domain_file_paths]
    watercontact_tasks = [run_pdb_watercontact.s(path) for path in domain_file_paths]

    pdb_job = group(centermass_tasks, watercontact_tasks)
    pdb_results = pdb_job.apply_async()
    pdb_results.get()