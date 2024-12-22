from features import *
from sklearn.feature_selection import mutual_info_regression
import sqlite3

db_path = 'solutions.sqlar'

# Connect to the SQLAR file
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT data , name  FROM sqlar WHERE name LIKE '%.java'")

# Fetch all matching files
java_files = cursor.fetchall()
code_snippets = [(row[1], row[0].decode('utf-8')) for row in java_files]
samples = calculate_features_for_files(
    [(row[1], row[0].decode('utf-8')) for row in java_files])
