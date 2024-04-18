from flask import Flask, render_template, request, redirect, url_for
import zipfile
import uuid
import os
import sys
sys.path.append('../shared')
from tasks import add, run_pipeline

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = '/home/ec2-user/data/shared/submissions'  # Set upload destination

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['zipfile']
        if file:  # Check if file was provided
            filename = file.filename
            if not filename.lower().endswith('.zip'):
                print("Problem")
                return render_template('index.html', error="Please only upload .zip files.")

            job_hash = str(uuid.uuid4()) # Generate unique hash
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], job_hash)
            os.makedirs(upload_path, exist_ok=True)

            file.save(os.path.join(upload_path, 'data.zip'))

            result = add.delay(10, 2)
            print(result.get())

            return redirect(url_for('upload_success', job_hash=job_hash))
    else:
        return render_template('index.html')

@app.route('/upload_success/<job_hash>')
def upload_success(job_hash):
    return render_template('success.html', job_hash=job_hash)

if __name__ == '__main__':
    app.run(debug=True) 