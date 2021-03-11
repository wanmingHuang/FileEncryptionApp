import pandas as pd
import numpy as np
import os
import pickle
import encryption
from zipfile import ZipFile
import time


def process_mapping_file(row_mapping_files, column_mapping_file):
    mapping = {}
    mapping['rows'] = {}
    mapping['columns'] = {}

    for row_mapping_file in row_mapping_files:
        encoded_column_name = row_mapping_file.split('/')[-1].replace('-row.txt','').split("-")[-1]
        mapping['rows'][encoded_column_name] = {}
        with open(row_mapping_file, 'r') as f:
            lines = f.readlines()
            for line in lines:
                line = line.replace('\n', '')
                raw_entry, encoded_entry = line.split('","')
                raw_entry = raw_entry.replace('"', '')
                encoded_entry = encoded_entry.replace('"', '')
                mapping['rows'][encoded_column_name][encoded_entry] = raw_entry

    with open(column_mapping_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.replace('\n', '')
            raw_entry, encoded_entry = line.split('","')
            raw_entry = raw_entry.replace('"', '')
            encoded_entry = encoded_entry.replace('"', '')
            mapping['columns'][encoded_entry] = raw_entry
    return mapping


def decode_table(file_path, mapping):
    table_data = pd.read_csv(file_path)
    column_names = list(table_data.columns)

    # decode_row_values
    for column_name, column_dict in mapping['rows'].items():
        encoded_column_values = table_data[column_name].values
        table_data[column_name] = [mapping['rows'][column_name][el] for el in encoded_column_values]

    # decode column names
    table_data.columns = [mapping['columns'][name] for name in column_names]

    # return the decoded table
    return table_data


def unzip_file(zipfilename, target_dir):
    """
        extract a zip file to a target dir
    """
    with ZipFile(zipfilename, 'r') as f:
        f.extractall(target_dir)
    

def unzip_decrypt(zipfilename, target_dir, key):
    """
        comes before decode
        decrypt before unzip
    """

    # read key from file
    # with open('key.key', 'rb') as f:
    #     key = f.read()

    if key is not None:
        with open(zipfilename, 'rb') as f:
            zipObj = f.read()  # Read the bytes of the input file
        decrypted = encryption.decrypt(zipObj, key)
        with open(zipfilename, 'wb') as f:
            f.write(decrypted)

    # target_dir = os.path.join(target_dir, zipfilename.split('/')[-1].replace('.zip', ''))
    unzip_file(zipfilename, target_dir)


def read_mapping(filenames, target_dir):
    """
        read mapping as dict from target_dir
    """
    row_mapping_files = []
    for filename in filenames:
        if "row" in filename:
            row_mapping_files.append(os.path.join(target_dir, filename))
        if "column" in filename:
            column_mapping_file = os.path.join(target_dir, filename)
    mapping = process_mapping_file(row_mapping_files, column_mapping_file)
    return mapping


def decode_file(zipfilename, target_dir, key):
    # unzip the directory for 1. zipped csc; 2. mapping files
    unzip_file(zipfilename, target_dir)
    target_dir = os.path.join(target_dir, zipfilename.split('/')[-1].replace('.zip', ''))

    # assume 1 zip file for csvs
    mapping_files = {}
    for file_name in os.listdir(target_dir):
        if 'zip' in file_name: # tables
            zipfilename = file_name
        if '.txt' in file_name: # mapping_files
            sample_name = file_name.split("-")[0]
            if sample_name not in mapping_files.keys():
                mapping_files[sample_name] = []
            mapping_files[sample_name].append(file_name)
        if '.key' in file_name: # key
            with open(os.path.join(target_dir, file_name), 'rb') as f:
                key = f.read()

    # unzip the zip for tables
    unzip_decrypt(os.path.join(target_dir, zipfilename), target_dir, key)

    table_dir = [name for name in os.listdir(target_dir) if os.path.isdir(name)][0]
    target_dir = os.path.join(target_dir, table_dir)

    decoded_tables = []
    file_paths = []
    for sample_name in mapping_files.keys():
        mapping = read_mapping(mapping_files[sample_name], os.path.join(target_dir, "../"))

        encoded_file_name = os.path.join(target_dir, 'encoded_'+sample_name+'.csv')
        table_data = decode_table(encoded_file_name, mapping)
        # save decoded table to directory
        table_data.to_csv(os.path.join(target_dir, "../", "decoded_{}.csv".format(sample_name)), index=None)
        # return table_data, os.path.join(target_dir, "../", "decoded_{}.csv".format(sample_name))

        decoded_tables.append(table_data)
        file_paths.append(os.path.join(target_dir, "../", "decoded_{}.csv".format(sample_name)))

    # zip all decoded tables
    zipObj = ZipFile(os.path.join(target_dir, '../', 'decoded_tables.zip'), 'w')
    for file_path in file_paths:
        zipObj.write(file_path)
    zipObj.close()
    
    return decoded_tables, file_paths, os.path.join(target_dir, '../', 'decoded_tables.zip')


if __name__ == "__main__":
    # zipfilename = "encoded_files.zip"
    # decode_file(os.path.join(target_dir, zipfilename), target_dir)

    target_dir = "/Users/apple/Downloads/encoded_files2/"
    mapping = read_mapping(target_dir)
    # mapping = None
    decode_pickle(os.path.join(target_dir, 'student1_4.pkl'), mapping)

