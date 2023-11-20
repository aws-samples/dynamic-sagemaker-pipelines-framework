import glob
import numpy as np
import os
import pandas as pd
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
    X = cal_housing_df[
        [
            "longitude",
            "latitude",
            "housingMedianAge",
            "totalRooms",
            "totalBedrooms",
            "population",
            "households",
            "medianIncome",
        ]
    ]
    # Y = cal_housing_df[["medianHouseValue"]] / 100000
   
    data_dir = os.path.join(BASE_DIR, "unprocessed")
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)
    np.save(os.path.join(data_dir, "x_inference.npy"), X)
    input_files = glob.glob("{}/*.npy".format(data_dir))
    print("\nINPUT FILE LIST: \n{}\n".format(input_files))
    
    scaler = StandardScaler()
    x_inference = np.load(os.path.join(data_dir, "x_inference.npy"))
    scaler.fit(x_inference)
    
    data_output_dir = os.path.join(OUTPUT_DIR, "inference")
    if not os.path.exists(data_output_dir):
        os.mkdir(data_output_dir)
        
    for file in input_files:
        raw = np.load(file)
        # only transform feature columns
        transformed = scaler.transform(raw)
        output_path = os.path.join(data_output_dir, "inference.csv")
        np.savetxt(output_path, transformed, delimiter=",")
        print(f"SAVED TRANSFORMED Inference DATA FILE.{output_path}\n")
