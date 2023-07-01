import pandas as pd
import math

class PandasManager():

    def __init__(self, list_of_dicts):
        
        self._dataframe = pd.DataFrame.from_dict(list_of_dicts)
        self._dataframe['Total Hashes'] = self._dataframe['Hash'].map(self._dataframe['Hash'].value_counts())
        self._dataframe['Total 1k Hashes'] = self._dataframe['Hash on 1k'].map(self._dataframe['Hash on 1k'].value_counts())
        
        self.column_group_full_hash, self.median_group_by_full_hash = self.group_dataframe_by_column('Hash')
        self.column_group_1k, self.median_group_by_1k_hash = self.group_dataframe_by_column('Hash on 1k')

    def group_dataframe_by_column(self, column_name):
        grouped_by_column = self._dataframe.groupby(column_name)
        median_grouped_by_hash = grouped_by_column.median()
        return grouped_by_column, median_grouped_by_hash

    def get_dataframe_copy(self):
        """Returns a copy of the DataFrame."""
        return self._dataframe.copy()

    def get_total_files_count(self):
        self.total_files_count = len(self._dataframe.index)
        return self.total_files_count
 
    def get_modified_group_dataframe(self, idx):
        """
        Returns a modified group DataFrame based on the given index.
        """
        if idx == 0:
            group_df = self.median_group_by_full_hash
        elif idx == 1:
            group_df = self.median_group_by_1k_hash

        modified_df = group_df.reset_index()
        modified_df['Size'] = modified_df['Size In Bytes'].apply(self.get_readable_size)

        return modified_df

    def get_total_duplicates_size(self, idex):

        return self.get_total_filesize() - self.get_unique_filesize(idex)

    def get_unique_filesize(self, idex):
        if idex == 0:
            selected_group = self.median_group_by_full_hash
        elif idex == 1:
            selected_group = self.median_group_by_1k_hash
        return selected_group['Size In Bytes'].sum()

    def get_total_filesize(self):
        """
        return: Total size of all files with duplicates
        """
        return self._dataframe['Size In Bytes'].sum()

    def get_readable_size(self, size_bytes):
        """
        Convert bytes to a human-readable format.
        
        Args:
            size_bytes (int): Size in bytes.

        Returns:
            str: Human-readable size.

        Examples:
            >>> get_readable_size(2048)
            '2 KB'
        """

        # Check if size is zero
        if size_bytes == 0:
            return "0 B"

        # Define size units and their abbreviations
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']

        # Calculate the appropriate suffix index based on logarithmic calculation
        exponent = int(math.floor(math.log(size_bytes, 1024)))

        # Calculate the divisor based on the suffix index
        divisor = math.pow(1024, exponent)

        # Calculate the size in the appropriate unit
        size = round(size_bytes / divisor, 2)

        # Format the result as a string with the size and unit
        result = f"{size} {suffixes[exponent]}"

        return result

    def get_unique_file_count(self, index):
        """
        Returns the total number of unique files based on the given index.

        Args:
            index: The index representing the group type.
                0 corresponds to median_group_by_full_hash.
                1 corresponds to median_group_by_1k_hash.

        Returns:
            The total number of unique files.
        """
        # Select the appropriate group based on the index
        if index == 0:
            selected_group = self.median_group_by_full_hash
        elif index == 1:
            selected_group = self.median_group_by_1k_hash

        # Get the length of the group DataFrame to determine the number of unique files
        unique_file_count = len(selected_group.index)

        return unique_file_count

    def get_group_by_value(self, value, index):
        """
        Returns the group associated with the given value based on the provided index.

        Args:
            value: The value to search for in the group.
            index: The index representing the group type.
                0 corresponds to column_group_full_hash.
                1 corresponds to column_group_1k.

        Returns:
            The group associated with the given value.
        """
        # Select the appropriate group based on the index
        if index == 0:
            selected_group = self.column_group_full_hash
        elif index == 1:
            selected_group = self.column_group_1k

        # Return the group associated with the given value
        return selected_group.get_group(value)

    def get_group_summary(self, value, index):
        """
        Calculates the total size, count, and duplicate size of a group associated with the given value.

        Args:
            value: The value used to identify the group.
            index: The index representing the group type.
                0 corresponds to column_group_full_hash.
                1 corresponds to column_group_1k.

        Returns:
            A tuple containing the total size, count, and duplicate size of the group.
        """
        # Select the appropriate group based on the index
        if index == 0:
            selected_group = self.column_group_full_hash
        elif index == 1:
            selected_group = self.column_group_1k

        # Retrieve the group associated with the given value
        group_df = selected_group.get_group(value)

        # Calculate the sum of sizes
        total_size = group_df['Size In Bytes'].sum()

        # Calculate the number of records in the group
        record_count = len(group_df.index)

        # Calculate the duplicate size
        median_size = group_df['Size In Bytes'].median()
        duplicate_size = total_size - median_size

        return total_size, record_count, duplicate_size