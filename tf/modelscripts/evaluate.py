import os
import json
import subprocess
import sys
import numpy as np
import pandas 
import pathlib
import tarfile
from sklearn.metrics import mean_squared_error 


if __name__ == "__main__":
    
    pred_path = "/opt/ml/processing/input/calhousing-Transform-train/"
    print(os.listdir(pred_path))
    with open(os.path.join(pred_path, "x_test.csv.out")) as f:
        file_string = f.read()
    y_test_pred = json.loads(file_string)["predictions"]
    
    test_path = "/opt/ml/processing/input/calhousing-Preprocessing-train/"
    print(os.listdir(test_path))
    y_test_true = np.loadtxt(os.path.join(test_path, "test/y_test.csv"))
    scores = mean_squared_error(y_test_true, y_test_pred)
    print("\nTest MSE :", scores)

    # Available metrics to add to model: https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor-model-quality-metrics.html
    report_dict = {
        "regression_metrics": {
            "mse": {"value": scores, "standard_deviation": "NaN"},
        },
    }

    output_dir = "/opt/ml/processing/output"
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)

    evaluation_path = f"{output_dir}/model_evaluation_metrics.json"
    with open(evaluation_path, "w") as f:
        f.write(json.dumps(report_dict))
