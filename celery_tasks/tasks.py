from celery import Celery
from celery import group, chain

import shutil
import os
import subprocess
import zipfile

app = Celery('tasks', broker='amqp://celery_worker:celery@10.0.11.137:5673//', backend='redis://10.0.11.137:6379')
app.conf.task_prefetch_count = 1

@app.task
def add(x, y):
    return x + y 

@app.task(queue='merizo_queue')
def run_merizo(file_name):
    print("Running Merizo")
    # Get parent directory
    parent_dir = os.path.dirname(file_name)
    
    # Get file name without extension 
    file_name_base = os.path.splitext(os.path.basename(file_name))[0]

    # Create output directory
    output_dir = os.path.join(parent_dir, file_name_base)
    os.makedirs(output_dir, exist_ok=True)  
    # Run prediction
    command = f"/home/ec2-user/data/celery_venv/bin/python /home/ec2-user/data/Merizo/predict.py -d cpu -i {file_name} --iterate --save_domains"
    subprocess.run(command, shell=True, check=True)

    # Move files to the output directory
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

@app.task(queue='pdb_queue')
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

@app.task(queue='pdb_queue')
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


@app.task()
def process_results(merizo_results):
    domain_file_paths = merizo_results#[path for result in merizo_results]
    
    centermass_tasks = group(run_pdb_centremass.s(path) for path in domain_file_paths)
    watercontact_tasks = group(run_pdb_watercontact.s(path) for path in domain_file_paths)

    pdb_group = group(centermass_tasks, watercontact_tasks) 
    return pdb_group.apply_async(routing_key="pdb_queue")

@app.task()
def run_pipeline(directory_path):
    print("Running Pipeline")
    unzipped_folder_name = ""
    with zipfile.ZipFile(os.path.join(directory_path, 'data.zip'), 'r') as zip_ref:
        for info in zip_ref.infolist():
            if info.is_dir():  # Find the top-level directory
                unzipped_folder_name = info.filename
                break 
    
        zip_ref.extractall(directory_path)

    os.remove(os.path.join(directory_path, 'data.zip')) # Remove original archive

    directory_path = os.path.join(directory_path, unzipped_folder_name) # Update directory path to the unzipped folder

    pdb_files = [os.path.join(directory_path, file) for file in os.listdir(directory_path) if file.endswith('.pdb')]

    # Create a chain for each PDB file
    file_processing_chains = [
        chain(
            run_merizo.s(file_path).set(routing_key='merizo_queue') | 
            process_results.s()
        )
         for file_path in pdb_files
    ]

    grouped_chains = group(file_processing_chains)

    task_chain = chain(grouped_chains , clean_up.s(directory_path=directory_path))
    chain_result = task_chain.apply_async()
    return chain_result


@app.task()
def clean_up(results, directory_path):
    base_dir_name = os.path.basename(os.path.dirname(directory_path)).strip('/')
    print(base_dir_name)
    parent_dir = os.path.dirname(os.path.dirname(directory_path))
    new_zip_path = os.path.join(parent_dir, 'data.zip')

    shutil.make_archive(directory_path, 'zip', directory_path)
    original_zip = os.path.join(parent_dir, base_dir_name + '.zip')
    
    os.rename(original_zip, new_zip_path)

    shutil.rmtree(directory_path)  # Clean up the resutls directory





#start:
# celery -A tasks worker --loglevel=INFO --pidfile=celery.pid --logfile=celery.log -D
#stop:
# celery multi stop_verify worker --pidfile=celery.pid --logfile=celery.log