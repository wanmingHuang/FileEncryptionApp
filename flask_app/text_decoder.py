"""
    text decoder
    process report or code
"""

import numpy as np
import os
import re
import ops
import utils
import encryption


def decode_text_file(file_name, mapping):
    """
        read the file as text file
        search for special token, and replace them with decoded values
    """
    with open(file_name, 'r') as f:
        content = f.read()

    # search for special tokens that might need to be decoded
    tokens = re.findall("\<(.*?)\>", content)

    for token in tokens:
        value_to_replace = token.split(":")[-1]
        sample_name = token.split(":")[0].split("-")[0]
        if "column" in token:
            decoded_value = mapping[sample_name]['columns'][value_to_replace]
        if "row" in token:
            column_name = token.split(":")[0].split("-")[-1]
            decoded_value = mapping[sample_name]['rows'][column_name][value_to_replace]
        content = content.replace("<" + token + ">", decoded_value)
    
    return content


def decode_file(zipfilename, target_dir, key):
    """
        main file for text file decoding
    """
    # unzip the directory for 1. zipped csv; 2. mapping files
    utils.unzip_file(zipfilename, target_dir)

    unzipped_dir = [name for name in os.listdir(target_dir) if os.path.isdir(os.path.join(target_dir, name)) and "__" not in name][0]
    target_dir = os.path.join(target_dir, unzipped_dir)

    mapping_files = {}
    for file_name in os.listdir(target_dir):
        if ('column' in file_name) or ('row' in file_name): # mapping_files
            sample_name = file_name.split("-")[0]
            if sample_name not in mapping_files.keys():
                mapping_files[sample_name] = []
            mapping_files[sample_name].append(file_name)
        if "report" in file_name or ".py" in file_name: # report or code
            file_name_to_decode = file_name
        if '.key' in file_name: # key
            with open(os.path.join(target_dir, file_name), 'rb') as f:
                key = f.read()
    
    if key is not None:
        encryption.decrypt_file(os.path.join(target_dir, file_name_to_decode), key)

    all_mappings = {}
    for sample_name in mapping_files.keys():
        all_mappings[sample_name] = ops.read_mapping(mapping_files[sample_name], target_dir)

    decoded_content = decode_text_file(os.path.join(target_dir, file_name_to_decode), all_mappings)
    print(decoded_content)

    # save the decoded text to a file
    decoded_file_path = os.path.join(target_dir, '../', file_name_to_decode)
    with open(decoded_file_path, 'w') as f:
        f.write(decoded_content)

    
    # zip all decoded tables
    # zipObj = ZipFile(os.path.join(target_dir, '../', 'decoded_tables.zip'), 'w')
    # for file_path in file_paths:
    #     zipObj.write(file_path)
    # zipObj.close()
    
    # return decoded_tables, file_paths, os.path.join(target_dir, '../', 'decoded_tables.zip')

    return decoded_content, decoded_file_path

