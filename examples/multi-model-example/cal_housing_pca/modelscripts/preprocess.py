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
    Y = cal_housing_df[["medianHouseValue"]] / 100000

    X.to_csv(os.path.join(OUTPUT_DIR, "train/X.csv"), index=False, header=True)