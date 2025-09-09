import os
import pandas as pd


input_folder = "../ActsinQuestions"
output_file = "../ActsinQuestions/allQuestions.csv"


csv_files = [f for f in os.listdir(input_folder) if f.endswith(".csv")]


df_list = []
for file in csv_files:
    file_path = os.path.join(input_folder, file)
    df = pd.read_csv(file_path)
    df_list.append(df)


all_questions = pd.concat(df_list, ignore_index=True)


all_questions = all_questions.drop_duplicates()

all_questions.to_csv(output_file, index=False, encoding="utf-8")

print(f"Combined {len(csv_files)} CSV files into {output_file} with {len(all_questions)} rows.")
