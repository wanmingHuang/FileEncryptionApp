from zipfile import ZipFile



def unzip_file(zipfilename, target_dir):
    """
        extract a zip file to a target dir
    """
    with ZipFile(zipfilename, 'r') as f:
        f.extractall(target_dir)