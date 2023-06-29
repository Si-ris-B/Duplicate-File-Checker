import sys
import os
import hashlib
from datetime import datetime
import logging
import math
from collections import defaultdict

import hashlib

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

def get_files_by_size(paths):
    """
    Recursively scans the directories specified in 'paths' and returns a dictionary that groups files by their size.

    Args:
        paths (list): List of directory paths to scan.

    Returns:
        dict: Dictionary containing file paths grouped by their respective sizes.
        int: Total files count
    """

    # Initialize counters and data structures
    file_count = 0
    files_by_size = defaultdict(list)

    # Iterate over each path in the list of paths
    for path in paths:
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
        int: The count of unique file hashes.
    """

    # Calculate the total count of files with length greater than or equal to 2 in each category

    # Initialize a variable to store the count of qualifying files
    qualifying_file_count = sum([len(files) for category, files in files_by_size.items() if len(files) >= 2])

    # Create an empty list to store file lengths
    file_lengths = []

    duplicate_file_count = 0  # Initialize count of duplicate files
    hashes_on_1k = {}  # Dictionary to store file hashes and associated filenames
    hashes_on_1k_num = 0  # Count of unique file hashes

    for size, files in files_by_size.items():
        if len(files) < 2:
            # Skip file sizes that have less than 2 files since they are unique
            continue

        for filename in files:
            file_lengths.append(filename)  # Append filename to the list of all files

            try:
                small_hash = get_hash(filename, first_chunk_only=True)  # Calculate the hash of the first chunk of the file

                if small_hash in hashes_on_1k:
                    # Add the filename to the list of filenames associated with the existing hash
                    hashes_on_1k[small_hash].append(filename)
                else:
                    # Create a new hash entry with the filename as the first element in the list of filenames
                    hashes_on_1k[small_hash] = [filename]

                # Increment the count of unique file hashes
                hashes_on_1k_num += 1

            except OSError:
                # Ignore file access errors and continue to the next file
                continue

    return hashes_on_1k, hashes_on_1k_num
