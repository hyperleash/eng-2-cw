from flask import Flask, render_template, request, redirect, url_for
import zipfile
import uuid
import os
import sys
sys.path.append('../shared')
from tasks import add, run_pipeline
from tasks import app as celery_app
from flask import send_from_directory
from celery.result import AsyncResult
import redis
import shutil

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = '/home/ec2-user/data/shared/submissions'  # Set upload destination

redis_client = redis.Redis(host='10.0.11.137', port=6379) 

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['zipfile']
        if file:  # Check the provided file 
            filename = file.filename
            if not filename.lower().endswith('.zip'):
                print("Non-archive uppload: ignoring")
                return render_template('index.html', error="Please only upload .zip files.")

            job_hash = str(uuid.uuid4()) # Generate unique hash
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], job_hash)
            os.makedirs(upload_path, exist_ok=True)

            file.save(os.path.join(upload_path, 'data.zip'))
            
            result = run_pipeline.delay(upload_path)

            task_id = result.id
            redis_client.set(job_hash, task_id)

            return redirect(url_for('upload_success', job_hash=job_hash))
    else:
        return render_template('index.html')

@app.route('/upload_success/<job_hash>')
def upload_success(job_hash):
    return render_template('success.html', job_hash=job_hash)

@app.route('/download-results/<job_hash>')
def download_results(job_hash):
    result_archive_path = os.path.join(app.config['UPLOAD_FOLDER'], job_hash, 'data.zip')

    if not os.path.exists(result_archive_path):
        return render_template('error.html', error_message='Result archive not found')

    return send_from_directory(os.path.dirname(result_archive_path), os.path.basename(result_archive_path), as_attachment=True)
# Status route
@app.route('/task-status/<job_hash>')
def get_task_status(job_hash):
    task_id = redis_client.get(job_hash).decode('utf-8')
    if task_id:
        chain_result = AsyncResult(task_id, app=celery_app)
        child_task_statuses = []
        print(chain_result.children)
        for group_result in chain_result.children:  # Iterate over GroupResult objects
            for child_result in group_result.children:  # Iterate over AsyncResult objects
                child_task_statuses.append(child_result.status) # Get status
        
        if all(status == 'SUCCESS' for status in child_task_statuses): #if all succeed
            overall_status = 'READY'
        elif any(status == 'FAILURE' for status in child_task_statuses): #if any fail
            overall_status = 'FAILED'
        else:
            overall_status = 'IN PROGRESS'
    
        if overall_status == 'READY':
            return render_template('status.html', job_hash=job_hash, job_status=overall_status, download_ready=True)  
        else:
            return render_template('status.html', job_hash=job_hash, job_status=overall_status, download_ready=False)
    else:
        return render_template('error.html', error_message='Hash not found') 

if __name__ == '__main__':
    app.run(debug=True) 