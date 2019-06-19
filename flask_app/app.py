import os
import urllib.request
from flask import Flask, flash, request, redirect, render_template, jsonify, url_for, send_file
from werkzeug.utils import secure_filename

# import swear removal model
import sys
sys.path.append('../model')
from SwearRemovalModel import main as SWR_model

UPLOAD_FOLDER = 'static/temp_folder'

app = Flask(__name__)
app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


# For now, only allow .wav files
ALLOWED_EXTENSIONS = set(['wav'])

# path to the uploads folder
# When refactoring, this will be unecessary as it is already done in the app.config
PATH = os.path.join("static", "temp_folder")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_path():
    file_name = os.listdir(PATH)[0]
    return os.path.join(PATH, file_name)


@app.route('/')
def upload_form():
    return render_template('index.html')


@app.route('/', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No file selected for uploading')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash('File successfully uploaded')

            # Create the Graph and Save the png file
            file_path = get_file_path()

            SWR_model(filename, app.config['UPLOAD_FOLDER'])

            os.remove(file_path)

            file_name = filename.split(".")[0] + "_edited.wav"

            # Download the file
            return send_file(os.path.join(PATH, file_name), as_attachment=True)
        else:
            flash('Allowed file type .wav')

    return redirect(request.url)


if __name__ == "__main__":
    app.run()