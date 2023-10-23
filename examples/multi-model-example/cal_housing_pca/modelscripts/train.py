import argparse
import numpy as np
import os
import pandas as pd
from sklearn.decomposition import PCA
from joblib import dump, load



if __name__ == "__main__":

    # data directories
    channel_path = "/opt/ml/input/data/calhousing-pca-Preprocessing-train"
    print(f'Training data location: {os.listdir(channel_path)}')
    train_data_path = os.path.join(channel_path, "X.csv")
    X = pd.read_csv(train_data_path)
    print(X.head(5))
    pca = PCA(n_components=6)
    pca.fit(X)
    print(pca.explained_variance_ratio_)
    print(pca.singular_values_)

    # save model
    dump(pca, os.path.join(os.environ.get("SM_MODEL_DIR") , "pca_model.joblib"))
    print(os.listdir("/opt/ml/model/"))