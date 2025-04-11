from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import boto3
from werkzeug.utils import secure_filename
from botocore.exceptions import ClientError
import tempfile
import json
import zipfile
import io
import time
import shutil
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'xlsx', 'docx', 'zip'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Available environments and their profiles
ENVIRONMENTS = {
    'dev': 'development',
    'uat': 'testing',
    'prod': 'production'
}


# Initialize S3 client with specified profile
def get_s3_client(profile_name=None):
    if profile_name:
        session = boto3.Session(profile_name=profile_name)
        return session.client('s3')
    return boto3.client('s3')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    selected_env = request.args.get('env', '')
    profile_name = ENVIRONMENTS.get(selected_env, None)

    try:
        s3 = get_s3_client(profile_name)
        buckets = s3.list_buckets()
        return render_template('index.html',
                               buckets=buckets['Buckets'],
                               environments=ENVIRONMENTS,
                               selected_env=selected_env)
    except Exception as e:
        flash(f"Error listing buckets: {str(e)}", 'danger')
        return render_template('index.html',
                               buckets=[],
                               environments=ENVIRONMENTS,
                               selected_env=selected_env)


@app.route('/bucket/<bucket_name>', defaults={'prefix': ''})
@app.route('/bucket/<bucket_name>/<path:prefix>')
def list_objects(bucket_name, prefix):
    selected_env = request.args.get('env', '')
    profile_name = ENVIRONMENTS.get(selected_env, None)

    try:
        s3 = get_s3_client(profile_name)

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
                               breadcrumbs=breadcrumbs,
                               selected_env=selected_env)

    except Exception as e:
        flash(f"Error listing objects: {str(e)}", 'danger')
        return redirect(url_for('index'))


@app.route('/upload/<bucket_name>', defaults={'prefix': ''}, methods=['POST'])
@app.route('/upload/<bucket_name>/<path:prefix>', methods=['POST'])
def upload_file(bucket_name, prefix):
    selected_env = request.args.get('env', '')
    profile_name = ENVIRONMENTS.get(selected_env, None)

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
                s3 = get_s3_client(profile_name)
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
    selected_env = request.args.get('env', '')
    profile_name = ENVIRONMENTS.get(selected_env, None)

    try:
        s3 = get_s3_client(profile_name)

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
    selected_env = request.args.get('env', '')
    profile_name = ENVIRONMENTS.get(selected_env, None)

    try:
        s3 = get_s3_client(profile_name)
        s3.delete_object(Bucket=bucket_name, Key=object_key)
        flash(f'Successfully deleted {object_key.split("/")[-1]}', 'success')
    except Exception as e:
        flash(f"Error deleting object: {str(e)}", 'danger')

    # Redirect back to the current directory
    prefix = '/'.join(object_key.split('/')[:-1])
    if prefix:
        prefix += '/'
    return redirect(url_for('list_objects', bucket_name=bucket_name, prefix=prefix, env=selected_env))


@app.route('/create_folder/<bucket_name>', defaults={'prefix': ''}, methods=['POST'])
@app.route('/create_folder/<bucket_name>/<path:prefix>', methods=['POST'])
def create_folder(bucket_name, prefix):
    selected_env = request.args.get('env', '')
    profile_name = ENVIRONMENTS.get(selected_env, None)
    folder_name = request.form.get('folder_name', '').strip()

    if not folder_name:
        flash('Folder name cannot be empty', 'danger')
        return redirect(request.referrer)

    # Create a proper S3 key for the folder
    folder_key = prefix + folder_name + '/' if prefix else folder_name + '/'

    try:
        s3 = get_s3_client(profile_name)
        # Create an empty object with a trailing slash to represent a folder
        s3.put_object(Bucket=bucket_name, Key=folder_key, Body='')
        flash(f'Successfully created folder: {folder_name}', 'success')
    except Exception as e:
        flash(f"Error creating folder: {str(e)}", 'danger')

    return redirect(url_for('list_objects', bucket_name=bucket_name, prefix=prefix))


@app.route('/copy/<bucket_name>/<path:object_key>', methods=['POST'])
def copy_object(bucket_name, object_key):
    selected_env = request.args.get('env', '')
    profile_name = ENVIRONMENTS.get(selected_env, None)
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
        s3 = get_s3_client(profile_name)
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


@app.route('/bulk_download/<bucket_name>', methods=['POST'])
def bulk_download(bucket_name):
    selected_env = request.args.get('env', '')
    profile_name = ENVIRONMENTS.get(selected_env, None)

    keys_json = request.form.get('keys', '[]')
    try:
        selected_items = json.loads(keys_json)
        s3 = get_s3_client(profile_name)

        # Collect all file keys to download
        keys_to_download = []
        folder_count = 0

        # Process files directly selected
        file_items = [item for item in selected_items if item['type'] == 'file']
        for item in file_items:
            keys_to_download.append({
                'key': item['key'],
                'original_path': item['key'],
                'name': item.get('name', item['key'].split('/')[-1])
            })

        # Process folders - list all objects within each folder recursively
        folder_items = [item for item in selected_items if item['type'] == 'folder']
        for folder in folder_items:
            folder_count += 1
            folder_prefix = folder['path']

            # Get all objects with this prefix using pagination for large folders
            paginator = s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket_name, Prefix=folder_prefix)

            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        if obj['Key'] != folder_prefix:  # Skip the folder object itself
                            keys_to_download.append({
                                'key': obj['Key'],
                                'original_path': obj['Key'],
                                'name': obj['Key'].split('/')[-1]
                            })

        if not keys_to_download:
            flash('No files selected for download', 'warning')
            return redirect(request.referrer)

        # If only one file and no folders were selected, use the standard download endpoint
        if len(keys_to_download) == 1 and folder_count == 0:
            return redirect(url_for('download_file',
                                    bucket_name=bucket_name,
                                    object_key=keys_to_download[0]['key'],
                                    env=selected_env))

        # Create a temporary directory to store downloaded files
        temp_dir = tempfile.mkdtemp()

        try:
            # Create a ZIP file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Name the zip file based on selection
            if folder_count == 1 and len(file_items) == 0:
                # If only one folder is selected, use its name
                folder_name = folder_items[0].get('name', 'folder')
                zip_filename = f"{bucket_name}_{folder_name}_{timestamp}.zip"
            elif folder_count > 1 and len(file_items) == 0:
                # If multiple folders are selected
                zip_filename = f"{bucket_name}_folders_{timestamp}.zip"
            elif folder_count == 0:
                # Only files selected
                zip_filename = f"{bucket_name}_files_{timestamp}.zip"
            else:
                # Mix of folders and files
                zip_filename = f"{bucket_name}_download_{timestamp}.zip"

            zip_path = os.path.join(temp_dir, zip_filename)

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Track progress for large downloads
                total_files = len(keys_to_download)
                processed_files = 0

                for item in keys_to_download:
                    key = item['key']
                    original_path = item['original_path']

                    # For preserving folder structure in the ZIP:
                    # If the user selected a folder, remove the folder prefix to create a clean structure
                    arcname = original_path
                    for folder in folder_items:
                        folder_path = folder['path']
                        if original_path.startswith(folder_path):
                            # If this file is from a selected folder, preserve structure relative to that folder
                            folder_name = folder.get('name', folder_path.rstrip('/').split('/')[-1])
                            relative_path = original_path[len(folder_path):]
                            arcname = os.path.join(folder_name, relative_path)
                            break

                    # Create necessary directories in the ZIP
                    if '/' in arcname:
                        dir_path = os.path.dirname(arcname)
                        # This doesn't actually create a directory in the ZIP,
                        # but is a workaround to create empty directories if needed
                        if dir_path and not any(e.startswith(dir_path + '/') for e in zipf.namelist()):
                            zipf.writestr(dir_path + '/', '')

                    # Download the file to a temporary file
                    temp_file = os.path.join(temp_dir, os.path.basename(key))
                    try:
                        s3.download_file(bucket_name, key, temp_file)

                        # Add file to the ZIP with its path structure
                        zipf.write(temp_file, arcname=arcname)

                        # Remove the temporary file
                        os.remove(temp_file)

                        processed_files += 1
                    except Exception as e:
                        app.logger.error(f"Error downloading {key}: {str(e)}")

            # Send the ZIP file
            return send_file(
                zip_path,
                as_attachment=True,
                download_name=zip_filename,
                # Clean up the temp directory after sending
                on_close=lambda: shutil.rmtree(temp_dir, ignore_errors=True)
            )

        except Exception as e:
            # Clean up temp directory in case of error
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e

    except Exception as e:
        flash(f"Error during bulk download: {str(e)}", 'danger')
        return redirect(request.referrer) @ app.route('/bulk_delete/<bucket_name>', defaults={'prefix': ''},
                                                      methods=['POST'])


@app.route('/bulk_delete/<bucket_name>/<path:prefix>', methods=['POST'])
def bulk_delete(bucket_name, prefix):
    selected_env = request.args.get('env', '')
    profile_name = ENVIRONMENTS.get(selected_env, None)

    keys_json = request.form.get('keys', '[]')
    try:
        selected_items = json.loads(keys_json)
        s3 = get_s3_client(profile_name)

        deleted_count = 0
        error_count = 0
        folder_count = 0

        for item in selected_items:
            try:
                if item['type'] == 'file':
                    # Delete individual file
                    s3.delete_object(Bucket=bucket_name, Key=item['key'])
                    deleted_count += 1
                elif item['type'] == 'folder':
                    # Recursive delete for folder
                    folder_count += 1
                    folder_prefix = item['path']

                    # Use paginator to handle large folders
                    paginator = s3.get_paginator('list_objects_v2')
                    pages = paginator.paginate(Bucket=bucket_name, Prefix=folder_prefix)

                    object_deletion_count = 0

                    for page in pages:
                        if 'Contents' in page:
                            # Create a list of objects to delete
                            objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]

                            if objects_to_delete:
                                # Delete objects in batches of 1000 (S3 limit)
                                for i in range(0, len(objects_to_delete), 1000):
                                    batch = objects_to_delete[i:i + 1000]
                                    s3.delete_objects(
                                        Bucket=bucket_name,
                                        Delete={
                                            'Objects': batch,
                                            'Quiet': True
                                        }
                                    )
                                    object_deletion_count += len(batch)

                    deleted_count += object_deletion_count
            except Exception as e:
                error_count += 1
                app.logger.error(f"Error deleting {item}: {str(e)}")

        if error_count == 0:
            if folder_count > 0:
                flash(f'Successfully deleted {folder_count} folder(s) containing {deleted_count} object(s)', 'success')
            else:
                flash(f'Successfully deleted {deleted_count} file(s)', 'success')
        else:
            flash(f'Deleted {deleted_count} item(s), but encountered {error_count} error(s)', 'warning')

    except Exception as e:
        flash(f"Error during bulk delete: {str(e)}", 'danger')

    return redirect(url_for('list_objects', bucket_name=bucket_name, prefix=prefix, env=selected_env))
    import os

if __name__ == '__main__':
    app.run(port=8001, host='0.0.0.0')