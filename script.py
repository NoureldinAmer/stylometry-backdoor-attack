import os
import csv


def count_valid_java_files(folder_path, line_threshold=50):
    """
    Counts .java files in the given folder and its subfolders that meet the minimum line threshold
    based on folder names (e.g., 50-60, 100-200). Also collects the file paths.
    """
    count = 0
    valid_files = []
    for subfolder in os.listdir(folder_path):
        subfolder_path = os.path.join(folder_path, subfolder)
        if os.path.isdir(subfolder_path):
            try:
                # Extract the range from the folder name
                parts = subfolder.split('-')
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    lower_bound = int(parts[0])
                    if lower_bound >= line_threshold:
                        # Add .java files from this folder
                        java_files = [
                            os.path.join(subfolder_path, file)
                            for file in os.listdir(subfolder_path) if file.endswith('.java')
                        ]
                        valid_files.extend(java_files)
                        count += len(java_files)
            except Exception as e:
                print(f"Error processing folder {subfolder_path}: {e}")
    return count, valid_files


def escape_java_code(code):
    """
    Escapes special characters in Java code to fit within a CSV field.
    """
    escape_mappings = {
        '\\': '\\\\',
        '\'': '\\\'',
        '\"': '\\\"',
        '\n': '\\n',
        '\r': '\\r',
        '\t': '\\t'
    }
    escaped_code = ''.join(escape_mappings.get(c, c) for c in code)
    return escaped_code  # Enclose in single quotes


def process_author_files(author, valid_files, csv_writer, min_files):
    if len(valid_files) < min_files:
        print(f"Author {author} does not have enough files ({
              len(valid_files)}/{min_files}). Skipping.")
        return  # Skip if the author doesn't meet the minimum file count

    # Temporary storage for rows related to the current author
    temp_rows = []

    try:
        for file_path in valid_files:
            try:
                # Step 1: Read the Java file content
                with open(file_path, 'r', encoding='utf-8') as file:
                    code = file.read()

                # Step 2: Escape special characters and format the code
                formatted_code = escape_java_code(code)

                # Prepare the CSV row
                csv_row = [author, file_path, code]
                temp_rows.append(csv_row)

            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                print(f"Removing all entries for author {
                      author} and breaking loop.")
                # Break the loop and remove all rows for this author
                return  # Exits the function early

        # Add rows to the CSV only if all files were processed successfully
        for row in temp_rows:
            csv_writer.writerow(row)
        print(f"Successfully processed all files for author {author}.")

    except Exception as e:
        print(f"Unexpected error processing author {author}: {e}")


def find_authors_and_generate_csv(base_folder, csv_file, min_files=9, line_threshold=50):
    """
    Finds authors with at least `min_files` .java files meeting the line threshold.
    Writes the qualifying files to a CSV file.
    """
    authors = []
    with open(csv_file, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        # Write the header for the CSV
        csv_writer.writerow(['user_id', 'file_path', 'data'])

        for author in os.listdir(base_folder):
            author_path = os.path.join(base_folder, author)
            if os.path.isdir(author_path):
                java_file_count, valid_files = count_valid_java_files(
                    author_path, line_threshold)
                if java_file_count >= 9:
                    authors.append(author)
                process_author_files(author, valid_files,
                                     csv_writer, min_files)
            if len(authors) >= 10000:
                break

    return authors


# Example usage:
if __name__ == "__main__":
    base_folder = "../../dataset3_valid/."
    output_csv = "github.csv"  # CSV file to store the results
    authors = find_authors_and_generate_csv(
        base_folder, output_csv, min_files=9, line_threshold=50)
    print(f"Authors with at least 9 Java files having at least 50 lines of code are saved in {
          output_csv}:")
    for author in authors:
        print(author)
