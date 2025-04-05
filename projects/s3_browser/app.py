import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import boto3
from werkzeug.utils import secure_filename
from botocore.exceptions import ClientError
import tempfile

app = Flask(__name__)
app.secret_key = os.urandom(24)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'xlsx', 'docx', 'zip'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

aws_profile = 'myprofile'
def get_boto3_client(aws_profile, service='s3'):
    # os.environ['HTTPS_PROXY'] = 'proxy.com:10009'
    # os.environ['HTTP_PROXY'] = 'proxy.com:10009'
    #return boto3.client(service)
    #aws_access_key_id, aws_secret_access_key, aws_session_token, region = getAWSKeys()
    #os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    #os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    session = boto3.session.Session(profile_name=aws_profile)
    return session.client(service)

# Initialize S3 client
def get_s3_client(aws_profile):
    return get_boto3_client(aws_profile, service='s3')




def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    try:
        s3 = get_s3_client(aws_profile)
        buckets = s3.list_buckets()
        return render_template('index.html', buckets=buckets['Buckets'])
    except Exception as e:
        flash(f"Error listing buckets: {str(e)}", 'danger')
        return render_template('index.html', buckets=[])


@app.route('/bucket/<bucket_name>', defaults={'prefix': ''})
@app.route('/bucket/<bucket_name>/<path:prefix>')
def list_objects(bucket_name, prefix):
    try:
        s3 = get_s3_client()

        # Handle trailing slash for directories
        if prefix and not prefix.endswith('/'):
            prefix += '/'

        # List objects with the given prefix
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix, Delimiter='/')

        # Process common prefixes (folders)
        folders = []
        if 'CommonPrefixes' in response:
            for obj in response['CommonPrefixes']:
                folder_name = obj['Prefix'].rstrip('/').split('/')[-1]
                folders.append({
                    'name': folder_name,
                    'prefix': obj['Prefix']
                })

        # Process objects (files)
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                # Skip the directory itself
                if obj['Key'] == prefix:
                    continue

                # Extract the file name (last part after the last slash)
                file_name = obj['Key'].split('/')[-1]

                # Only include files directly in this directory
                if file_name and obj['Key'].startswith(prefix):
                    files.append({
                        'key': obj['Key'],
                        'name': file_name,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified']
                    })

        # Prepare breadcrumbs for navigation
        breadcrumbs = []
        if prefix:
            parts = prefix.rstrip('/').split('/')
            current_path = ''
            for i, part in enumerate(parts):
                current_path += part + '/'
                breadcrumbs.append({
                    'name': part,
                    'path': current_path
                })

        return render_template('bucket.html',
                               bucket_name=bucket_name,
                               folders=folders,
                               files=files,
                               current_prefix=prefix,
                               breadcrumbs=breadcrumbs)

    except Exception as e:
        flash(f"Error listing objects: {str(e)}", 'danger')
        return redirect(url_for('index'))


@app.route('/upload/<bucket_name>', defaults={'prefix': ''}, methods=['POST'])
@app.route('/upload/<bucket_name>/<path:prefix>', methods=['POST'])
def upload_file(bucket_name, prefix):
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(request.referrer)

    files = request.files.getlist('file')

    if not files or files[0].filename == '':
        flash('No selected file', 'danger')
        return redirect(request.referrer)

    upload_count = 0
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            try:
                s3 = get_s3_client()
                # Prepare the S3 key by combining the prefix and filename
                s3_key = prefix + filename if not prefix or prefix.endswith('/') else prefix + '/' + filename
                s3.upload_file(file_path, bucket_name, s3_key)
                upload_count += 1
                os.remove(file_path)  # Clean up temporary file
            except Exception as e:
                flash(f"Error uploading {filename}: {str(e)}", 'danger')

    if upload_count > 0:
        flash(f'Successfully uploaded {upload_count} file(s)', 'success')

    # Redirect back to the current directory
    return redirect(url_for('list_objects', bucket_name=bucket_name, prefix=prefix))


@app.route('/download/<bucket_name>/<path:object_key>')
def download_file(bucket_name, object_key):
    try:
        s3 = get_s3_client()

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        # Download the file
        s3.download_file(bucket_name, object_key, temp_path)

        # Get the filename from the object key
        filename = object_key.split('/')[-1]

        # Send the file to the user and delete it after sending
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=filename,
            on_close=lambda: os.remove(temp_path)  # Clean up the temp file
        )

    except Exception as e:
        flash(f"Error downloading file: {str(e)}", 'danger')
        # Redirect back to the bucket view
        prefix = '/'.join(object_key.split('/')[:-1])
        return redirect(url_for('list_objects', bucket_name=bucket_name, prefix=prefix))


@app.route('/delete/<bucket_name>/<path:object_key>', methods=['POST'])
def delete_object(bucket_name, object_key):
    try:
        s3 = get_s3_client()
        s3.delete_object(Bucket=bucket_name, Key=object_key)
        flash(f'Successfully deleted {object_key.split("/")[-1]}', 'success')
    except Exception as e:
        flash(f"Error deleting object: {str(e)}", 'danger')

    # Redirect back to the current directory
    prefix = '/'.join(object_key.split('/')[:-1])
    if prefix:
        prefix += '/'
    return redirect(url_for('list_objects', bucket_name=bucket_name, prefix=prefix))


@app.route('/create_folder/<bucket_name>', defaults={'prefix': ''}, methods=['POST'])
@app.route('/create_folder/<bucket_name>/<path:prefix>', methods=['POST'])
def create_folder(bucket_name, prefix):
    folder_name = request.form.get('folder_name', '').strip()

    if not folder_name:
        flash('Folder name cannot be empty', 'danger')
        return redirect(request.referrer)

    # Create a proper S3 key for the folder
    folder_key = prefix + folder_name + '/' if prefix else folder_name + '/'

    try:
        s3 = get_s3_client()
        # Create an empty object with a trailing slash to represent a folder
        s3.put_object(Bucket=bucket_name, Key=folder_key, Body='')
        flash(f'Successfully created folder: {folder_name}', 'success')
    except Exception as e:
        flash(f"Error creating folder: {str(e)}", 'danger')

    return redirect(url_for('list_objects', bucket_name=bucket_name, prefix=prefix))


@app.route('/copy/<bucket_name>/<path:object_key>', methods=['POST'])
def copy_object(bucket_name, object_key):
    destination_path = request.form.get('destination_path', '').strip()
    new_name = request.form.get('new_name', '').strip()

    if not new_name:
        flash('New name cannot be empty', 'danger')
        return redirect(request.referrer)

    # Prepare the destination key
    if destination_path and not destination_path.endswith('/'):
        destination_path += '/'

    destination_key = destination_path + new_name

    try:
        s3 = get_s3_client()
        copy_source = {'Bucket': bucket_name, 'Key': object_key}
        s3.copy_object(CopySource=copy_source, Bucket=bucket_name, Key=destination_key)
        flash(f'Successfully copied to {destination_key}', 'success')
    except Exception as e:
        flash(f"Error copying object: {str(e)}", 'danger')

    # Redirect back to the current directory
    prefix = '/'.join(object_key.split('/')[:-1])
    if prefix:
        prefix += '/'
    return redirect(url_for('list_objects', bucket_name=bucket_name, prefix=prefix))


if __name__ == '__main__':
    app.run(debug=True, port=7770)