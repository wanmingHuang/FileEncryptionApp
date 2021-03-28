from zipfile import ZipFile


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