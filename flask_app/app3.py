"""
    This file should process and maintain file with session, without save tables on server
"""

import os
from flask import Flask, flash, request, redirect, url_for, render_template, session
from flask_session import Session
from werkzeug.utils import secure_filename
from flask import send_from_directory, send_file
import tempfile
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
from steps import explanations

UPLOAD_FOLDER = 'uploaded_files/'
ENCODE_FOLDER = 'encoded_files/'
DECODE_FOLDER = 'decoded_files/'


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # maxinum size of uploaded file
app.config['DEBUG'] = True

app.config['IF_ENCODE'] = True
app.config['key'] = None

app.secret_key = secrets.token_urlsafe(16)
# app.secret_key = "7vgXeTB8B6RWOECPZIdwng"
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False

server_session = Session(app)
server_session.permanent = False

def allowed_file(filename):
    if app.config['IF_ENCODE'] is True:
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in {'csv', '.txt'}
    else:
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in {'zip', 'txt', 'py'}


def filter_uploaded_files(uploaded_files):
    """
        Only keep files with allowed file extensions
    """
    files = []
    sample_names = []
    for file in uploaded_files:
        if allowed_file(file.filename): # read each file
            filename = secure_filename(file.filename)
            sample_names.append(filename)
            files.append(file)

    return files, sample_names


def process_uploaded_files():
    uploaded_files = request.files.getlist("file[]")

    if len(uploaded_files) == 0:
        flash('No selected file')
        return redirect(request.url)

    files, sample_names = filter_uploaded_files(uploaded_files)
    if len(sample_names) == 0: # no correct format files are uploaded
        flash('Incorrect file format, please reupload')
        return redirect(request.url)
    return files, sample_names


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
    session.permanent = False
    session['ROLE'] = None
    session['key'] = None

    if request.method == 'POST':
        session['ROLE'] = request.form['role']

    if 'ROLE' not in session.keys() or session['ROLE'] is None:
        return render_template('navigator.html')
    else:
        return render_template('navigator.html', role=session['ROLE'])


@app.route("/generate_new_key", methods=["GET", "POST"])
def generate_new_key():
    encoder.generate_new_key()
    # download the key file
    return send_file('key.key', as_attachment=True, cache_timeout=0)


################################################################
# Table encoder
################################################################

@app.route('/encode_tables', methods=['GET', 'POST'])
def encode_tables():
    session['IF_ENCODE'] = True
    if request.method == 'GET':
        return render_template('table_encoder2.html',
                            if_encode=session['IF_ENCODE'],
                            encode_step=1)
    else:
        files, sample_names = process_uploaded_files()
        session['NUM_TABLES'] = len(sample_names)
        session['sample_names'] = sample_names

        session['tables'] = []
        session['samples'] = []
        session['all_column_types'] = []
        columns_to_group = [[] for i in range(len(sample_names))]

        table_index = 0
        for file in files:
            raw_data, column_types = encoder.read_table(file, [])
            raw_column_names, raw_cell_values = encoder.extract_sample(raw_data)
            session['samples'].append([raw_column_names, raw_cell_values.tolist()])
            # convert data frame to json and save it
            session['tables'].append(utils.table2json(raw_data, False))
            session['all_column_types'].append(column_types)

            # all string columns are potential columns to be grouped
            for i in range(len(column_types)):
                if column_types[i] == 3:
                    columns_to_group[table_index].append(raw_column_names[i])

            table_index += 1

        session['columns_to_group'] = columns_to_group
        session['grouped_columns'] = []  # for each group [ for each table [] ]

        # for webpage purpose, records group index of each column, ungroup or nor String marks -1
        session['columns_grouped'] = [{column_name:0 for column_name in columns_to_group[i]} for i in range(len(sample_names))]
        session['group_cnt'] = 1 # record group index
        session['group_colors'] = ['transparent', 'red', 'blue', 'yellow', 'purple', 'orange']

        session['encode_step'] = 2
        column_types = [] if len(session['samples']) > 1 else session['all_column_types']
        
        return render_template('table_encoder2.html',
                            explanation=explanations[0],
                            samples=session['samples'],
                            sample_names=session['sample_names'],
                            if_encode=session['IF_ENCODE'],
                            column_types=session['all_column_types'],
                            encode_step=session['encode_step'],
                            columns_to_group=session['columns_to_group'])


@app.route('/set_column_data_type', methods=['POST'])
def set_column_data_type():
    """
        set column data type given user input
    """
    # all column types: date, int, float, string
    session['date_columns'] = [[] for i in range(session['NUM_TABLES'])]
    session['int_columns'] = [[] for i in range(session['NUM_TABLES'])]
    session['float_columns'] = [[] for i in range(session['NUM_TABLES'])]
    session['string_columns'] = [[] for i in range(session['NUM_TABLES'])]

    for key in request.form.keys():
        if "column_types" in key:
            table_index = int(key.replace("column_types-", "").split(":")[0])
            column_name = key.split(':')[-1]
            session['all_column_types'][table_index].append(int(request.form[key]))

            if int(request.form[key]) == 0:
                session['date_columns'][table_index].append(column_name)
            if int(request.form[key]) == 1:
                session['int_columns'][table_index].append(column_name)
            if int(request.form[key]) == 2:
                session['float_columns'][table_index].append(column_name)
            if int(request.form[key]) == 3:
                session['string_columns'][table_index].append(column_name)

    session['encode_step'] = 3

    return render_template('table_encoder2.html',
                            explanation=explanations[session['encode_step'] - 2],
                            if_encode=session['IF_ENCODE'],
                            samples=session['samples'],
                            sample_names=session['sample_names'],
                            column_types=session['all_column_types'],
                            encode_step=session['encode_step'],
                            columns_to_group=session['columns_to_group'],
                            columns_grouped=session['columns_grouped'],
                            group_colors=session['group_colors'],
                            error_message="")


@app.route("/group_columns", methods=["POST"])
def group_columns():
    """
        Group columns for string conversion across columns, and possibly tables
    """

    group_columns = [[] for i in range(session['NUM_TABLES'])]

    column_cnt = 0
    for key in request.form.keys():
        if "group_columns" in key:
            key = key.replace("group_columns-", "")
            table_index, column_name = key.split("-")
            table_index = int(table_index)
            group_columns[table_index - 1].append(column_name)
            session['columns_to_group'][table_index - 1].remove(column_name)
            session['columns_grouped'][table_index - 1][column_name] = session['group_cnt']

            column_cnt += 1
    
    if column_cnt > 1:
        session['grouped_columns'].append(group_columns)
        session['encode_step'] = 3
        session['group_cnt'] += 1
    else:
        session['encode_step'] = 4
    
    return render_template('table_encoder2.html',
                            explanation=explanations[session['encode_step'] - 2],
                            if_encode=session['IF_ENCODE'],
                            samples=session['samples'],
                            sample_names=session['sample_names'],
                            column_types=session['all_column_types'],
                            encode_step=session['encode_step'],
                            columns_to_group=session['columns_to_group'],
                            columns_grouped=session['columns_grouped'],
                            group_colors=session['group_colors'],
                            error_message="")


@app.route("/adjust_encoding_level", methods=["POST"])
def adjust_encoding_level():
    """
        adjust encoding level with slider

        encode table with the updated slider
    """

    encoding_levels = []
    plot_column_indexes = [[] for i in range(session['NUM_TABLES'])]

    for key in request.form.keys():
        if "encoding_level" in key:
            encoding_levels.append(int(request.form[key]))

        if 'plot_legends' in key:
            plot_column_indexes.append(int(key.replace('plot_legends-', '')))

    session['encoded_tables'] = []
    session['encoded_samples'] = []
    session['row_mapping'] = []
    session['column_mapping'] = []
    all_plot_column_flags = []
    data = []

    # if some columns are grouped, generate string mapping
    all_row_name_mappings = encoder.generate_string_mapping_grouped_columns(session['tables'], session['grouped_columns'])

    for i in range(session['NUM_TABLES']):
        # encode with the current encoding level
        raw_data, encoded_data, row_mapping_records, column_mapping_records = encoder.read_and_encode_data(
            session['sample_names'][i], session['tables'][i], session['date_columns'][i],
            session['float_columns'][i], session['string_columns'][i], encoding_levels[i], all_row_name_mappings[i])

        session['encoded_tables'].append(utils.table2json(encoded_data, False))

        # extract sample from table to show on the webpage
        encoded_column_names, encoded_cell_values = encoder.extract_sample(encoded_data)
        session['encoded_samples'].append([encoded_column_names, encoded_cell_values])
        session['row_mapping'].append(row_mapping_records)
        session['column_mapping'].append(column_mapping_records)

        # if no columns are specified, all float columns are plotted
        # if len(plot_column_indexes[i]) == 0:
        #     plot_column_indexes[i] = [raw_column_names.index(column_name) for column_name in float_columns[i]]
        
        # plot_column_flags = np.zeros(len(raw_column_names))
        # for j in range(len(raw_column_names)):
        #     if j in plot_column_indexes[i]:
        #         plot_column_flags[j] = 1
        # all_plot_column_flags.append(list(plot_column_flags.astype(np.int32)))

        data.append([utils.table2json(raw_data, True), utils.table2json(encoded_data, True)])
    
    # show tables and show plot
    return render_template('table_encoder2.html',
                            if_encode=app.config['IF_ENCODE'],
                            samples=session['samples'],
                            sample_names=session['sample_names'],
                            column_types=session['all_column_types'],
                            # plot_column_flags=all_plot_column_flags,
                            encoded_samples=session['encoded_samples'],
                            encoding_levels=encoding_levels,
                            encode_step=4,
                            data=data
    )


@app.after_request
def remove_files(response):
    if (request.endpoint == "download"):
        shutil.rmtree(session['TEMP_DIR'])
    return response


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
        zipfilepath, tmpdirname = encoder.encrypt_zip(session['encoded_tables'], session['sample_names'], session['row_mapping'], session['column_mapping'], key)
        session['TEMP_DIR'] = tmpdirname
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
    app.run(host='0.0.0.0', port=8000)
