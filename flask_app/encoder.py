"""

    1. read csv
    2. determine dtype for each column
    3. encoder each column given encoding level

    lvl 0: no change
    lvl 1: only change column name
    lvl 2: replace string values with unique replacement, replace float numbers by scaling
    lvl >=3: replace string values with unique replacement, replace float numbers by scaling + Gaussian noise (while keeping column regression)

"""

import pandas as pd
import os
import numpy as np
from sklearn.linear_model import LinearRegression
from zipfile import ZipFile
import encryption
from io import StringIO
import utils


def generate_string_mapping_grouped_columns(tables, grouped_columns):
    """
        generate string mappings given certain columns are grouped
    """
    all_row_name_mappings = [{} for i in range(len(tables))]
    for group_index in range(len(grouped_columns)):
        group = grouped_columns[group_index]
        values = []
        for table_index in range(len(group)):
            values.extend(list(tables[table_index][group[table_index]].values.flatten()))

        unique_values = np.unique(values)
        row_name_mapping_dic = {}
        for i in range(len(unique_values)):
            row_name_mapping_dic[unique_values[i]] = 'group{}_{}'.format(group_index, i)

        for table_index in range(len(group)):
            for column_name in group[table_index]:
                all_row_name_mappings[table_index][column_name] = row_name_mapping_dic
    return all_row_name_mappings


def encode_string_column(column, column_index, row_name_mapping_dic):
    """
        encode a column with string entry
    """
    # decide encoded value to replace each unique entry
    
    if row_name_mapping_dic is None:
        unique_values = column.unique()
        row_name_mapping_dic = {}
        for i in range(len(unique_values)):
            row_name_mapping_dic[unique_values[i]] = 'cell{}_{}'.format(column_index, i)

    all_values = column.to_numpy()
    new_values = [row_name_mapping_dic[all_values[i]] for i in range(len(all_values))]
    return new_values, row_name_mapping_dic


def encode_float_column(column_values, Gaussian_noise=False):
    """
        encode a column with float entry
    """
    all_values = (column_values - np.mean(column_values)) / np.std(column_values)

    if Gaussian_noise:
        all_values += np.random.normal(size=len(all_values))
    
    return all_values


def encode_until_threshold(table_data, float_columns, encoding_lvl, threshold=0.1):
    # set a threshold, if surpass, Gaussian noise is stopped
    max_error = 0.0
    # keep adding Gaussian noise until prediction error surpass the threshold
    while max_error < threshold:
        # add 1 more Gaussian noise to data
        for column_name in float_columns:
            encoded_values = encode_float_column(table_data[column_name].to_numpy(), Gaussian_noise=True)
            table_data[column_name] = encoded_values

        # determine correlation still exists by checking linear regression performance
        max_error = 0
        for i in range(len(float_columns)):
            for j in range(i+1, len(float_columns)):
                X = table_data[float_columns[i]].fillna(0).to_numpy().reshape(-1, 1)
                Y = table_data[float_columns[j]].fillna(0).to_numpy().reshape(-1, 1)

                reg = LinearRegression().fit(X, Y)
                pred = reg.predict(X)
                error = np.mean((pred - Y)**2)
                max_error = max(max_error, error)


def collect_column_types(table_data):
    """
        collect column types
        0: date; 1: int; 2: float; 3: str

        fill in nan values
    """
    column_types = []

    for column_name in table_data.columns:
        if table_data[column_name].dtype == np.int64: # do nothing currently
            column_types.append(1)
        elif table_data[column_name].dtype == np.float64:
            table_data[column_name] = table_data[column_name].fillna(0)
            column_types.append(2)
        elif table_data[column_name].dtype == object:
            table_data[column_name] = table_data[column_name].fillna('')
            column_types.append(3)
    return column_types


def encode(raw_data, float_columns, string_columns, encoding_lvl, row_mapping_dict_grouped):
    """
        decode data type of each column

        table_data: pandas data frame
    """
    table_data = raw_data.copy()
    raw_column_names = list(table_data.columns)
    row_mapping_dicts = {} # a dict for each string column, column index as the key

    if encoding_lvl > 0: # 1. encode column name
        encoded_column_names = ["VAR{}".format(i) for i in range(len(raw_column_names))]
        table_data.columns = encoded_column_names
    else:
        encoded_column_names = table_data.columns

    # encode the string, float column names passed in
    string_columns = [encoded_column_names[raw_column_names.index(column_name)] for column_name in string_columns]
    float_columns = [encoded_column_names[raw_column_names.index(column_name)] for column_name in float_columns]

    if encoding_lvl > 1: # 2: encode string values
        # _, string_columns = collect_column_types(table_data)
        # string columns
        for i in range(len(string_columns)):
            column_name = string_columns[i]
            original_column_name = raw_column_names[encoded_column_names.index(column_name)]
            if original_column_name in row_mapping_dict_grouped.keys():
                # print(column_name)
                # print(table_data[column_name])
                # print(row_mapping_dict_grouped[column_name])
                
                encoded_values, row_mapping_dict = encode_string_column(table_data[column_name], i, row_mapping_dict_grouped[original_column_name])
            else:
                encoded_values, row_mapping_dict = encode_string_column(table_data[column_name], i, None)
            table_data[column_name] = encoded_values
            row_mapping_dicts[column_name] = row_mapping_dict

    if encoding_lvl > 2: # 3: rescale float values
        # float columns
        for column_name in float_columns:
            encoded_values = encode_float_column(table_data[column_name].to_numpy())
            table_data[column_name] = encoded_values
            
    if encoding_lvl > 3: # start at 4: add Gaussian noise
        # inserting Gaussian noise based on provided encoding level
        for _ in range(encoding_lvl - 3):
            for column_name in float_columns:
                encoded_values = encode_float_column(table_data[column_name].to_numpy(), Gaussian_noise=True)
                table_data[column_name] = encoded_values

    return table_data, [raw_column_names, encoded_column_names, row_mapping_dicts]


def write_mapping(mapping_data, target_dir, file_name):
    """
        write string mapping to file
    """
    raw_column_names, encoded_column_names, row_mapping_dicts = mapping_data
    file_name = file_name.replace('.csv', '')

    mapping_file_list = []

    # write to file
    if row_mapping_dicts is not None:
        for column_name, row_mapping_dict in row_mapping_dicts.items():
            row_mapping_file = os.path.join(target_dir, "{}-{}-row.txt".format(file_name,column_name))
            with open(row_mapping_file, 'w') as f:
                for key, value in row_mapping_dict.items():
                    f.write('"{}","{}"\n'.format(key, value))
            mapping_file_list.append(row_mapping_file)

    column_mapping_file = os.path.join(target_dir, "{}-column.txt".format(file_name))
    with open(column_mapping_file, 'w') as f:
        for i in range(len(raw_column_names)):
            f.write('"{}","{}"\n'.format(raw_column_names[i], encoded_column_names[i]))
        mapping_file_list.append(column_mapping_file)
    
    return mapping_file_list


def plot_columns(table_data, target_dir, fig_name):
    fig = plt.figure()
    for column_name in table_data.columns:
        if table_data[column_name].dtype == np.float64:
            plt.plot(table_data[column_name])
    plt.savefig(os.path.join(target_dir, fig_name+'.png'))


def read_tables(root_dir):
    """
        read and return tables without joining them
    """
    file_paths = [os.path.join(root_dir, file_name) for file_name in os.listdir(root_dir) if '.csv' in file_name]

    all_table_data = []
    all_column_types = []
    samples = []
    sample_names = []
    for file_name in os.listdir(root_dir):
        if '.csv' in file_name:
            sample_names.append(file_name)
            file_path = os.path.join(root_dir, file_name)
            table_data = pd.read_csv(file_path)
            column_types = collect_column_types(table_data)

            all_table_data.append(table_data)
            all_column_types.append(column_types)
            raw_column_names, raw_cell_values = extract_sample(table_data)
            samples.append([raw_column_names, raw_cell_values])


    return all_table_data, all_column_types, samples, sample_names, file_paths


def read_join_tables(root_dir, join_columns):
    file_paths = [os.path.join(root_dir, file_name) for file_name in os.listdir(root_dir) if '.csv' in file_name]

    table_data = pd.read_csv(file_paths[0])

    for i in range(1, len(file_paths)):
        file_path = file_paths[i]
        add_table = pd.read_csv(file_path)

        table_data = pd.merge(table_data, add_table, left_on=join_columns[0], right_on=join_columns[i])
    table_data.to_csv(os.path.join(root_dir, 'join_data.csv'), index=None)

    # speculate column types
    column_types = collect_column_types(table_data)

    return table_data, os.path.join(root_dir, 'join_data.csv'), column_types


def read_file(storage_file):
    """
        read data frame directly from file storage
    """
    table_data = pd.read_csv(StringIO(storage_file.read()))
    return table_data


def read_data(file_path, date_columns):
    table_data = pd.read_csv(file_path, parse_dates=date_columns)
    column_types = collect_column_types(table_data)
    return table_data, column_types


def generate_new_key():
    key = encryption.generate_key()

    # save key to file
    with open('key.key', 'wb') as f:
        f.write(key)


def encrypt_zip(target_dir, file_list, mapping_files, key=None):
    """
        comes after encode

        zip everything
        generate a key
        encrypt the zip file
    """

    # create a zip file with the encoded data and mapping files
    zipfilename = os.path.join(target_dir, 'encoded_tables.zip')
    utils.zip_file(zipfilename, file_list)

    # encrypt the zipped file
    if key is not None:
        encryption.encrypt_file(zipfilename, key)

    # also zip the mapping file
    new_zipfilename = os.path.join(target_dir, 'encoded_files.zip')
    utils.zip_file(new_zipfilename, mapping_files + [zipfilename])
    
    return new_zipfilename


def read_and_encode_data(file_path, target_dir, date_columns, float_columns, string_columns, encoding_lvl, row_mapping_dict_grouped):
    """
        main function for data encoding
        read raw data
        encode data
        save encoded results to file
    """
    table_data, _ = read_data(file_path, date_columns)
    file_name = file_path.split("/")[-1]

    encoded_data, mapping_data = encode(table_data, float_columns, string_columns, encoding_lvl, row_mapping_dict_grouped)

    # write mapping data to file
    mapping_file_list = write_mapping(mapping_data, target_dir, file_name)

    # write encoded data to file
    
    encoded_file_name = os.path.join(target_dir, 'encoded_{}'.format(file_name))
    encoded_data.to_csv(encoded_file_name, index=None)

    return table_data, encoded_data, encoded_file_name, mapping_file_list


def extract_sample(table_data):
    """
        extract sample from table data for showing in webpage
        the format is list of strings (each row)
    """
    sample = table_data.head(3)
    column_names = sample.columns.to_list()
    cell_values = sample.values
    return column_names, cell_values


def plotly_plot():
    gapminder = px.data.gapminder()
    fig = px.scatter(gapminder.query("year==2007"), x="gdpPercap", y="lifeExp", size="pop", color="continent",
            hover_name="country", log_x=True, size_max=60)
    fig.show()


if __name__ == "__main__":
    # table_data = pd.read_csv('../table_data.csv')
    # print(table_data.head())
    # print("="*80)
    # encoding_lvl = 4
    # table_data, mapping = encode(table_data, encoding_lvl)
    # print(table_data.head())

    # plotly_plot()


    root_dir = "/home/nlp/dev/Project/GP_0227/encoded_data"
    date_columns = []
    raw_data = read_join_tables(root_dir, date_columns)
    print(raw_data.head())

