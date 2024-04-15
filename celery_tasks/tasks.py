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
def run_prediction(file_name):
    # Get file name without extension 
    # Get parent directory
    parent_dir = os.path.dirname(file_name)
    
    file_name_base = os.path.splitext(os.path.basename(file_name))[0]

    # Create output directory
    output_dir = os.path.join(parent_dir, file_name_base)
    os.makedirs(output_dir, exist_ok=True)  # Create if it doesn't exist 

    # Run prediction
    command = f"python /home/ec2-user/data/Merizo/predict.py -d cpu -i {file_name} --iterate --save_domains"
    subprocess.run(command, shell=True, check=True)

    # Move files to the output directory
    for filename in os.listdir():
        if filename.startswith(file_name_base):
            destination = os.path.join(output_dir, filename)
            if os.path.exists(destination):  # Check if destination exists
                os.remove(destination)
            shutil.move(filename, output_dir)

    domain_files = []
    # Prepare domain files for pdb_tools (doesn't work with .dom_pdb extension)
    for filename in os.listdir(output_dir):
        if filename.endswith('.dom_pdb'):
            new_filename = filename[:-8] + '.pdb' 
            os.rename(os.path.join(output_dir, filename), 
                      os.path.join(output_dir, new_filename))
            domain_files.append(os.path.join(output_dir, new_filename))
    
    return domain_files
#start:
# celery -A tasks worker --loglevel=INFO --pidfile=celery.pid --logfile=celery.log -D
#stop:
# celery multi stop_verify worker --pidfile=celery.pid --logfile=celery.log