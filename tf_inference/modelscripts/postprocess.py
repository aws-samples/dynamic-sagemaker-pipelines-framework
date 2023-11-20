import glob
import numpy as np
import os
import pandas as pd
import json
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

BASE_DIR = "/opt/ml/processing"
CODE_DIR = os.path.join(BASE_DIR, "code")
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

print(os.listdir(INPUT_DIR))

if __name__ == "__main__":
    columns = [
        "longitude",
        "latitude",
        "housingMedianAge",
        "totalRooms",
        "totalBedrooms",
        "population",
        "households",
        "medianIncome",
        "medianHouseValue",
    ]
    cal_housing_df = pd.read_csv(
        os.path.join(INPUT_DIR, "raw_data/cal_housing.data"), 
        names=columns, 
        header=None
    )
    
    with open("/opt/ml/processing/input/inference/inference.csv.out") as file:
        content = json.load(file)
       
    flattened_predictions = [item * 100000 for sublist in content["predictions"] for item in sublist]
    pred_df = pd.DataFrame({"predictions": flattened_predictions})
    cal_housing_df["predictions"] = pred_df["predictions"]
    grouped = cal_housing_df.groupby("housingMedianAge")["predictions"].mean().reset_index()
   
    data_output_dir = os.path.join(OUTPUT_DIR, "inference")
    if not os.path.exists(data_output_dir):
        os.mkdir(data_output_dir)
    grouped.to_csv(os.path.join(data_output_dir, "MedianHouseValue_Agg_By_Age.csv"),index=False)

    print(f"SAVED TRANSFORMED Inference DATA FILE.{data_output_dir}\n")
