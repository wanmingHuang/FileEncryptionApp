import os
from flask import Flask, flash, request, redirect, url_for, render_template, session
from werkzeug.utils import secure_filename
from flask import send_from_directory, send_file
import utils
import encoder
import decoder
import text_decoder
import pandas as pd
import numpy as np
import json
import shutil
import secrets
import ops
import encryption

UPLOAD_FOLDER = 'uploaded_files/'
ENCODE_FOLDER = 'encoded_files/'
DECODE_FOLDER = 'decoded_files/'


# clear all previous files before running
def reset_folders():
    if os.path.exists(UPLOAD_FOLDER):
        shutil.rmtree(UPLOAD_FOLDER)
    if os.path.exists(ENCODE_FOLDER):
        shutil.rmtree(ENCODE_FOLDER)
    if os.path.exists(DECODE_FOLDER):
        shutil.rmtree(DECODE_FOLDER)

    os.mkdir(UPLOAD_FOLDER)
    os.mkdir(ENCODE_FOLDER)
    os.mkdir(DECODE_FOLDER)


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ENCODE_FOLDER'] = ENCODE_FOLDER
app.config['DECODE_FOLDER'] = DECODE_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # maxinum size of uploaded file
app.config['DEBUG'] = True

app.config['IF_ENCODE'] = True
app.config['key'] = None

app.secret_key = secrets.token_urlsafe(16)
app.config['SESSION_TYPE'] = 'filesystem'
# session.init_app(app)


def allowed_file(filename):
    if app.config['IF_ENCODE'] is True:
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in {'csv', '.txt'}
    else:
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in {'zip', 'txt', 'py'}


def collect_uploaded_files(uploaded_files):
    """
        collect flask uploaded files
    """
    file_paths = []
    sample_names = []
    for file in uploaded_files:
        if allowed_file(file.filename): # read each file
            filename = secure_filename(file.filename)
            sample_names.append(filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path) # save file to server
            file_paths.append(file_path)
    return file_paths, sample_names


def table2json(table_data):
    """
        a pandas data frame to json
    """
    table_data = table_data.dropna()
    # table_data = table_data.to_dict(orient='records')
    # table_data = json.dumps(table_data, indent=2)

    # subsample if the table is too big
    if table_data.shape[0] > 200:
        table_data = table_data.sample(n=200)

    table_data = table_data.reset_index(drop=True)

    return table_data.to_json(date_unit='ns')


@app.route('/set_mode', methods=['GET'])
def set_mode():
    """
        set the mode to be encode or decode
    """
    app.config['key'] = None
    reset_folders()
    app.config['IF_ENCODE'] = not app.config['IF_ENCODE']

    return redirect('/')


def process_uploaded_files():
    reset_folders()
    uploaded_files = request.files.getlist("file[]")

    if len(uploaded_files) == 0:
        flash('No selected file')
        return redirect(request.url)

    file_paths, sample_names = collect_uploaded_files(uploaded_files)
    if len(file_paths) == 0: # no correct format files are uploaded
        flash('Incorrect file format, please reupload')
        return redirect(request.url)

    app.config['FILE_PATH'] = file_paths
    app.config['NUM_TABLES'] = len(sample_names)
    return sample_names


@app.route('/encode_tables', methods=['GET', 'POST'])
def encode_tables():
    app.config['IF_ENCODE'] = True
    if request.method == 'GET':
        return render_template('table_encoder.html',
                            if_encode=app.config['IF_ENCODE'],
                            encode_step=1)
    else:
        sample_names = process_uploaded_files()

        samples = []
        all_column_types = []
        columns_to_group = [[] for i in range(len(sample_names))]

        table_index = 0
        for file_path in app.config['FILE_PATH']:
            raw_data, column_types = encoder.read_data(file_path, [])
            raw_column_names, raw_cell_values = encoder.extract_sample(raw_data)
            samples.append([raw_column_names, raw_cell_values])
            all_column_types.append(column_types)

            # all string columns are potential columns to be grouped
            for i in range(len(column_types)):
                if column_types[i] == 3:
                    columns_to_group[table_index].append(raw_column_names[i])

            table_index += 1

        app.config['columns_to_group'] = columns_to_group
        app.config['grouped_columns'] = []  # for each group [ for each table [] ] 

        print(columns_to_group)
        print("!"*80)

        encode_step = 2 if len(samples) > 1 else 2
        column_types = [] if len(samples) > 1 else all_column_types

        return render_template('table_encoder.html',
                            samples=samples,
                            sample_names=sample_names,
                            if_encode=app.config['IF_ENCODE'],
                            column_types=all_column_types,
                            encode_step=encode_step,
                            columns_to_group=columns_to_group)


@app.route('/encrypt_data', methods=['GET', 'POST'])
def encrypt_data():
    """
        This is a standalone function that encrypts data
    """
    app.config['PAGE'] = 'encrypt_data'
    if request.method == 'GET':
        return render_template('encryption.html')
    else:
        app.config['IF_ENCODE'] = False
        # assume only 1 file is uploaded
        process_uploaded_files()
        if app.config['key'] is None:
            flash('Pleae upload a key to encrypt')
            return render_template('encryption.html')
        else:
            encryption.encrypt_file(app.config['FILE_PATH'][0], key=app.config['key'])
            app.config['DOWNLOAD_FILE_PATH'] = app.config['FILE_PATH'][0]
            return render_template('encryption.html', downloadable=True)


@app.route('/decrypt_data', methods=['GET', 'POST'])
def decrypt_data():
    """
        This is a standalone function that encrypts data
    """
    app.config['PAGE'] = 'decrypt_data'
    if request.method == 'GET':
        return render_template('decryption.html')
    else:
        app.config['IF_ENCODE'] = False
        # assume only 1 file is uploaded
        process_uploaded_files()
        if app.config['key'] is None:
            flash('Pleae upload a key to decrypt')
            return render_template('decryption.html')
        else:
            encryption.decrypt_file(app.config['FILE_PATH'][0], key=app.config['key'])
            app.config['DOWNLOAD_FILE_PATH'] = app.config['FILE_PATH'][0]
            return render_template('decryption.html', downloadable=True)


@app.route('/decode_tables', methods=['GET','POST'])
def decode_tables():
    app.config['PAGE'] = 'decode_tables'
    app.config['IF_ENCODE'] = False
    if 'key' not in app.config.keys():
        app.config['key'] = None
    if request.method == 'GET':
        return render_template('table_decoder.html',
                                if_encode=app.config['IF_ENCODE'],
                                encode_step=1)
    else:
        sample_names = process_uploaded_files()
        try:
            decoded_tables, decode_file_paths, download_file_path = decoder.decode_file(
                app.config['FILE_PATH'][0], app.config['DECODE_FOLDER'], app.config['key'])
        except Exception as e:
            flash('Error: ' + str(e))
            return render_template('table_decoder.html',
                                if_encode=app.config['IF_ENCODE'],
                                encode_step=1)

        app.config['DOWNLOAD_FILE_PATH'] = download_file_path

        if decoded_tables is not None: # i.e. a decoded csv
            # extract sample from table to show on the webpage
            samples = []
            sample_names = [file_path.split('/')[-1] for file_path in decode_file_paths]
            for decoded_data in decoded_tables:
                raw_column_names, raw_cell_values = encoder.extract_sample(decoded_data)
                samples.append([raw_column_names, raw_cell_values])

            # convert raw data and encoded data to json to be plotted
            # data = {'raw_data': table2json(decoded_data)}

            return render_template('table_decoder.html',
                                    if_encode=app.config['IF_ENCODE'],
                                    column_types=[],
                                    samples=samples,
                                    sample_names=sample_names,
                                    encode_step = 3)


@app.route('/decode_reports', methods=['GET','POST'])
def decode_reports():
    app.config['PAGE'] = 'decode_reports'
    app.config['IF_ENCODE'] = False
    if 'key' not in app.config.keys():
        app.config['key'] = None
    if request.method == 'GET':
        return render_template('report_decoder.html',
                                report="")
    else:
        sample_names = process_uploaded_files()
        try:
            decoded_report, decoded_file_path = text_decoder.decode_file(
                app.config['FILE_PATH'][0], app.config['DECODE_FOLDER'], app.config['key'])
        except Exception as e:
            flash('Error: ' + str(e))
            return render_template('report_decoder.html', report="")
        app.config['DOWNLOAD_FILE_PATH'] = decoded_file_path

        return render_template('report_decoder.html',
                                report = decoded_report,
                                downloadable = True)


@app.route('/', methods=['GET','POST'])
def root():
    reset_folders()
    app.config['key'] = None

    if request.method == 'POST':
        app.config['ROLE'] = request.form['role']

    if 'ROLE' not in app.config.keys() or app.config['ROLE'] is None:
        return render_template('navigator.html')
    else:
        return render_template('navigator.html', role=app.config['ROLE'])


@app.route("/generate_new_key", methods=["GET", "POST"])
def generate_new_key():
    encoder.generate_new_key()
    # download the key file
    return send_file('key.key', as_attachment=True, cache_timeout=0)


@app.route("/join_table", methods=["POST"])
def join_table():
    join_columns = []

    for key in request.form.keys():
        if "join_columns" in key:
            join_columns.append(request.form[key])

    if len(join_columns) > 1: # join columns, and proceed to choose data types
        try:
            raw_data, file_path, column_types = encoder.read_join_tables(app.config['UPLOAD_FOLDER'], join_columns)
            app.config['NUM_TABLES'] = 1
            app.config['FILE_PATH'] = [file_path]
            raw_column_names, raw_cell_values = encoder.extract_sample(raw_data)
            encode_step = 3
            samples=[[raw_column_names, raw_cell_values]]
            sample_names=[file_path.split('/')[-1]]
            error_message=""
        except Exception as e: # catch exception if key supplied is wrong
            samples = []
            sample_names = []
            for file_path in app.config['FILE_PATH']:
                raw_data, column_types = encoder.read_data(file_path, [])
                raw_column_names, raw_cell_values = encoder.extract_sample(raw_data)
                samples.append([raw_column_names, raw_cell_values])
                sample_names.append(file_path.split("/")[-1])
            encode_step = 2
            error_message = str(e)
            flash(error_message)
        column_types=[column_types]

    else: # do not join columns, for each table, choose data types
        all_table_data, column_types, samples, sample_names, file_paths = encoder.read_tables(app.config['UPLOAD_FOLDER'])
        app.config['FILE_PATH'] = file_paths
        encode_step = 3
    
    return render_template('table_encoder.html',
                            if_encode=app.config['IF_ENCODE'],
                            samples=samples,
                            sample_names=sample_names,
                            column_types=column_types,
                            encode_step=encode_step,
                            error_message="")


@app.route("/group_columns", methods=["POST"])
def group_columns():
    """
        Group columns for string conversion across columns, and possibly tables
    """
    # print(list(request.form.keys()))
    # print("="*80)

    group_columns = [[] for i in range(app.config['NUM_TABLES'])]

    column_cnt = 0
    for key in request.form.keys():
        if "group_columns" in key:
            key = key.replace("group_columns-", "")
            table_index, column_name = key.split("-")
            table_index = int(table_index)
            group_columns[table_index - 1].append(column_name)
            app.config['columns_to_group'][table_index - 1].remove(column_name)
            column_cnt += 1
    
    if column_cnt > 1:
        app.config['grouped_columns'].append(group_columns)
        encode_step = 2
    else:
        encode_step = 3

    all_table_data, column_types, samples, sample_names, file_paths = encoder.read_tables(app.config['UPLOAD_FOLDER'])
    app.config['FILE_PATH'] = file_paths
    
    return render_template('table_encoder.html',
                            if_encode=app.config['IF_ENCODE'],
                            samples=samples,
                            sample_names=sample_names,
                            column_types=column_types,
                            encode_step=encode_step,
                            columns_to_group=app.config['columns_to_group'],
                            error_message="")


@app.route("/adjust_encoding_level", methods=["POST"])
def adjust_encoding_level():
    """
        adjust encoding level with slider

        encode table with the updated slider
    """

    encoding_levels = []

    # all column types: date, int, float, string
    date_columns = [[] for i in range(app.config['NUM_TABLES'])]
    int_columns = [[] for i in range(app.config['NUM_TABLES'])]
    float_columns = [[] for i in range(app.config['NUM_TABLES'])]
    string_columns = [[] for i in range(app.config['NUM_TABLES'])]

    column_types = [[] for i in range(app.config['NUM_TABLES'])]
    plot_column_indexes = [[] for i in range(app.config['NUM_TABLES'])]

    for key in request.form.keys():
        if "column_types" in key:
            table_index = int(key.replace("column_types-", "").split(":")[0])
            column_name = key.split(':')[-1]
            column_types[table_index].append(int(request.form[key]))

            if int(request.form[key]) == 0:
                date_columns[table_index].append(column_name)
            if int(request.form[key]) == 1:
                int_columns[table_index].append(column_name)
            if int(request.form[key]) == 2:
                float_columns[table_index].append(column_name)
            if int(request.form[key]) == 3:
                string_columns[table_index].append(column_name)

        if "encoding_level" in key:
            encoding_levels.append(int(request.form[key]))

        if 'plot_legends' in key:
            plot_column_indexes.append(int(key.replace('plot_legends-', '')))

    samples = []
    encoded_samples = []
    sample_names = []
    all_plot_column_flags = []
    app.config['DOWNLOAD_FILE_PATHS'] = []
    app.config['MAPPING_FILES'] = []
    data = []

    for i in range(app.config['NUM_TABLES']):
        all_table_data, _, _, _, _ = encoder.read_tables(app.config['UPLOAD_FOLDER'])

    # if some columns are grouped, generate string mapping
    all_row_name_mappings = encoder.generate_string_mapping_grouped_columns(all_table_data, app.config['grouped_columns'])

    for i in range(app.config['NUM_TABLES']):
        sample_names.append(app.config['FILE_PATH'][i].split("/")[-1])
        # encode with the current encoding level
        raw_data, encoded_data, encoded_file_name, mapping_file_list = encoder.read_and_encode_data(
            app.config['FILE_PATH'][i], app.config['ENCODE_FOLDER'], date_columns[i], float_columns[i], string_columns[i], encoding_levels[i], all_row_name_mappings[i])

        app.config['DOWNLOAD_FILE_PATHS'].append(encoded_file_name)
        app.config['MAPPING_FILES'].extend(mapping_file_list)

        # extract sample from table to show on the webpage
        raw_column_names, raw_cell_values = encoder.extract_sample(raw_data)
        encoded_column_names, encoded_cell_values = encoder.extract_sample(encoded_data)
        samples.append([raw_column_names, raw_cell_values])
        encoded_samples.append([encoded_column_names, encoded_cell_values])

        # if no columns are specified, all float columns are plotted
        if len(plot_column_indexes[i]) == 0:
            plot_column_indexes[i] = [raw_column_names.index(column_name) for column_name in float_columns[i]]
        
        plot_column_flags = np.zeros(len(raw_column_names))
        for j in range(len(raw_column_names)):
            if j in plot_column_indexes[i]:
                plot_column_flags[j] = 1
        all_plot_column_flags.append(list(plot_column_flags.astype(np.int32)))

        data.append([table2json(raw_data.iloc[:, plot_column_indexes[i]]), table2json(encoded_data.iloc[:, plot_column_indexes[i]])])
    
    # show tables and show plot
    return render_template('table_encoder.html',
                            if_encode=app.config['IF_ENCODE'],
                            samples=samples,
                            sample_names=sample_names,
                            column_types=column_types,
                            plot_column_flags=all_plot_column_flags,
                            encoded_samples=encoded_samples,
                            encoding_levels=encoding_levels,
                            encode_step=4,
                            data=data
    )


@app.route("/download", methods=["POST"])
def download():
    if app.config['IF_ENCODE'] is True: # download encoded files
        if request.form.get('submit_button') == 'Download without encryption': # no encryption
            key = None
        else: # encrypt and download
            if request.files['file'].filename == '':
                flash('No key file uploaded, key is unused')
                key = None
            else:
                key = request.files['file'].read()
        zipfilepath = encoder.encrypt_zip(app.config['ENCODE_FOLDER'], app.config['DOWNLOAD_FILE_PATHS'], app.config['MAPPING_FILES'], key)
    else: # download decoded files
        zipfilepath = app.config['DOWNLOAD_FILE_PATH']

    return send_file(zipfilepath, as_attachment=True, cache_timeout=0)


@app.route("/upload_key", methods=["POST"])
def upload_key():
    if request.files['file'].filename == '':
        flash('No key file uploaded, key is unused')
        key = None
    else:
        key = request.files['file'].read()
        app.config['key'] = key
        flash("key is uploaded")
    return redirect(app.config['PAGE'])


if __name__ == "__main__":
    app.run()
