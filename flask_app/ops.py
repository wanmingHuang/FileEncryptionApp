"""
    functions that can be used to encoding or decodings
"""
import os


#############################################
# processing mapping files
#############################################

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