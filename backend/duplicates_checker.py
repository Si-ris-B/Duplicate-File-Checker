import os
import hashlib
from datetime import datetime
import math
from collections import defaultdict
import platform

def get_hash(filename, first_chunk_only=False, hash_algorithm=hashlib.sha1):
    # Create an instance of the specified hash algorithm
    hash_obj = hash_algorithm()

    # Open the file in binary mode
    with open(filename, 'rb') as file_object:
        if first_chunk_only:
            # Read only the first 2048 bytes of the file
            data = file_object.read(2048)
            hash_obj.update(data)
        else:
            # Iterate over the file in small chunks using a helper function called chunk_reader
            for chunk in chunk_reader(file_object):
                hash_obj.update(chunk)

    # Calculate the digest (hash) of the file
    hashed = hash_obj.digest()

    return hashed

def chunk_reader(file, chunk_size=51200):
    """
    A helper generator function to read file in chunks.
    It yields data in chunks of the specified size.
    """
    while True:
        chunk = file.read(chunk_size)
        if not chunk:
            break
        yield chunk

def convert_size(size_bytes):
    """function to convert bytes to readable format"""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])

def creation_date(path_to_file):
    
    if platform.system() == 'Windows':
        return os.path.getctime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime

def get_files_by_size(path):
    """
    Recursively scans the directories specified in 'path' and returns a dictionary that groups files by their size.

    Args:
        path (str):Directory path to scan.

    Returns:
        dict: Dictionary containing file paths grouped by their respective sizes.
        int: Total files count
    """

    # Initialize counters and data structures
    file_count = 0
    files_by_size = defaultdict(list)

    # Walk through the directory tree rooted at 'path'
    for dirpath, dirnames, filenames in os.walk(path):
        # Iterate over each filename in the current directory
        for filename in filenames:
            file_count += 1

            # Generate the full path to the current file
            file_path = os.path.join(dirpath, filename)

            try:
                # Get the real (canonical) path of the file
                real_file_path = os.path.realpath(file_path)

                # Get the size of the file in bytes
                file_size = os.path.getsize(real_file_path)

                # Ignore files smaller than 1024 bytes
                if file_size < 1024:
                    continue

                # Add the file path to the dictionary using the file size as the key
                if file_size not in files_by_size:
                    # Initialize an empty list for the file size if it doesn't exist
                    files_by_size[file_size] = []

                # Append the file path to the list associated with the file size
                files_by_size[file_size].append(real_file_path)

            except OSError:
                # If the file is not accessible due to permissions or other reasons,
                # continue to the next file
                continue

    return files_by_size, file_count

def get_duplicate_files_hashes_and_count(files_by_size):
    """
    This function calculates the count of duplicate files based on their sizes.

    Args:
        files_by_size (dict): A dictionary containing file sizes as keys and a list of corresponding file names as values.

    Returns:
        Dict: Dictionary to store file hashes and associated filenames
        int: The count of duplicate file hashes.
    """

    # Calculate the total count of files with length greater than or equal to 2 in each category

    # Initialize a variable to store the count of qualifying files
    qualifying_file_count = sum([len(files) for category, files in files_by_size.items() if len(files) >= 2])

    hashes_on_1k = defaultdict(list)  # Dictionary to store file hashes and associated filenames
    hashes_on_1k_num = 0  # Count of duplicate file hashes

    for size, files in files_by_size.items():
        if len(files) < 2:
            # Skip file sizes that have less than 2 files since they are unique
            continue

        for filename in files:
            try:
                small_hash = get_hash(filename, first_chunk_only=True)  # Calculate the hash of the first chunk of the file

                # Add the filename to the list of filenames associated with the existing hash                
                hashes_on_1k[small_hash].append(filename)

                # Increment the count of unique file hashes
                hashes_on_1k_num += 1

            except OSError:
                # Ignore file access errors and continue to the next file
                continue

    return hashes_on_1k, hashes_on_1k_num

def find_duplicate_files(hashes_on_1k):
    """
    Finds duplicate files based on hash values. For all files with the hash on the 1st 1024 bytes, get their hash on the full file - collisions will be duplicates

    Args:
        hashes_on_1k (dict): A dictionary containing file hashes as keys and a list of corresponding filenames as values.

    Returns:
        tuple: A tuple containing the data of the duplicate file and a dictionary containing unique file hashes 
               as keys and a list of corresponding filenames as values.
    """
    duplicate_files_count = 0  # Counter for duplicate file occurrences
    
    total_files = sum([len(files) for hashes, files in hashes_on_1k.items() if len(files) >= 2])
    unique_file_hashes = defaultdict(list)  # Dictionary to store unique file hashes and their corresponding filenames
    total_file_size = 0  # Total size of all duplicate files
    duplicate_files_list = []

    try:
        for hash_1k, files in hashes_on_1k.items():
            if len(files) < 2:
                continue  # Skip files that don't have duplicates

            for filename in files:
                try:
                    full_hash = get_hash(filename, first_chunk_only=False)  # Calculate the file's hash
                except OSError:
                    # The file access might have changed until this point, so continue to the next file
                    continue

                duplicate_files_count += 1
                size = os.path.getsize(filename)
                filesize = convert_size(size)
                creation = datetime.fromtimestamp(os.path.getctime(filename))
                modification = datetime.fromtimestamp(os.path.getctime(filename))

                # Store data of the duplicate file
                data = {
                    'Hash': full_hash,
                    'FileName': filename,
                    'Size': filesize,
                    'Size In Bytes': size,
                    'Hash on 1k': hash_1k,
                    'Modified Date': modification,
                    'Creation Date': creation
                }

                unique_file_hashes[str(full_hash)].append(filename)
                total_file_size += size
                duplicate_files_list.append(data)


        return duplicate_files_list, unique_file_hashes  # Return the duplicate file data and unique file hashes

    except OSError:
        print("An error occurred while accessing files. Please try again.")

def search_duplicate_files(path):

    files_by_size, file_count = get_files_by_size(path)
    hashes_on_1k, hashes_on_1k_num = get_duplicate_files_hashes_and_count(files_by_size)
    duplicate_files, unique_file_hashes = find_duplicate_files(hashes_on_1k)
    return duplicate_files