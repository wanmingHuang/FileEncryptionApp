from zipfile import ZipFile
import uuid
import pandas as pd


def zip_file(zipfilename, file_list):
    zipObj = ZipFile(zipfilename, 'w')
    for file_path in file_list:
        zipObj.write(file_path)
    zipObj.close()


def unzip_file(zipfilename, target_dir):
    """
        extract a zip file to a target dir
    """
    with ZipFile(zipfilename, 'r') as f:
        f.extractall(target_dir)

def random_string():
    string = str(uuid.uuid4())
    return string


def table2json(table_data, if_subsample):
    """
        a pandas data frame to json
    """

    if if_subsample:
        table_data = table_data.dropna()

        # subsample if the table is too big
        if table_data.shape[0] > 200:
            table_data = table_data.sample(n=200)

        table_data = table_data.reset_index(drop=True)

    return table_data.to_json(date_unit='ns')

def json2table(json_table):
    """
        json to pandas data frame
    """
    table_data = pd.read_json(json_table)
    return table_data
