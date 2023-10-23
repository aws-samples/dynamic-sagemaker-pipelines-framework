import glob
import os
import tarfile

import numpy as np
import pandas as pd
from joblib import load
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

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

    x_train_, x_test_, y_train, y_test = train_test_split(X, Y, test_size=0.33)
    pca_model_tarfile_location = os.path.join(INPUT_DIR, "calhousing-pca-Training-input-train/model.tar.gz")
    print(os.listdir(os.path.join(INPUT_DIR, "calhousing-pca-Training-input-train")))
    with tarfile.open(pca_model_tarfile_location) as tar:
        tar.extractall()
    print(os.listdir())
    pca = load("pca_model.joblib")
    x_train = pca.transform(x_train_)
    x_test = pca.transform(x_test_)

    split_data_dir = os.path.join(BASE_DIR, "split_data")
    if not os.path.exists(split_data_dir):
        os.mkdir(split_data_dir)
    np.save(os.path.join(split_data_dir, "x_train.npy"), x_train)
    np.save(os.path.join(split_data_dir, "x_test.npy"), x_test)
    np.save(os.path.join(split_data_dir, "y_train.npy"), y_train)
    np.save(os.path.join(split_data_dir, "y_test.npy"), y_test)

    input_files = glob.glob("{}/*.npy".format(split_data_dir))
    print("\nINPUT FILE LIST: \n{}\n".format(input_files))
    scaler = StandardScaler()
    x_train = np.load(os.path.join(split_data_dir, "x_train.npy"))
    scaler.fit(x_train)

    train_data_output_dir = os.path.join(OUTPUT_DIR, "train/train")
    if not os.path.exists(train_data_output_dir):
        os.mkdir(train_data_output_dir)
    test_data_output_dir = os.path.join(OUTPUT_DIR, "train/test")
    if not os.path.exists(test_data_output_dir):
        os.mkdir(test_data_output_dir)
    for file in input_files:
        raw = np.load(file)
        # only transform feature columns
        if "y_" not in file:
            transformed = scaler.transform(raw)
        if "train" in file:
            if "y_" in file:
                output_path = os.path.join(train_data_output_dir, "y_train.npy")
                np.save(output_path, raw)
                print("SAVED LABEL TRAINING DATA FILE\n")
            else:
                output_path = os.path.join(train_data_output_dir, "x_train.npy")
                np.save(output_path, transformed)
                print("SAVED TRANSFORMED TRAINING DATA FILE\n")
        else:
            if "y_" in file:
                output_path = os.path.join(test_data_output_dir, "y_test.npy")
                np.save(output_path, raw)
                output_path = os.path.join(test_data_output_dir, "y_test.csv")
                np.savetxt(output_path, raw, delimiter=",")
                print("SAVED LABEL TEST DATA FILE\n")
            else:
                output_path = os.path.join(test_data_output_dir, "x_test.npy")
                np.save(output_path, transformed)
                output_path = os.path.join(test_data_output_dir, "x_test.csv")
                np.savetxt(output_path, transformed, delimiter=",")
                print("SAVED TRANSFORMED TEST DATA FILE\n")
