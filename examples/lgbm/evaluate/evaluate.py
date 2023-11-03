import glob
import lightgbm as lgb
import numpy as np
from sklearn.metrics import accuracy_score, roc_auc_score
import pathlib, json



if __name__=='__main__':
    
    print('Loading data . . . .')
    y_test= np.load(glob.glob('{}/*.npy'.format('/opt/ml/processing/input/online_shoppers_intention_ytest'))[0]) 
    # y_pred= glob.glob('{}/*.out'.format('/opt/ml/processing/input'))[0]
    text_file= open(glob.glob('{}/*.out'.format('/opt/ml/processing/input/lgbm-Transform-test'))[0], "r")
    y_pred= np.array([float(i) for i in text_file.read()[1:-1].split(',')])

    print('\ny_pred shape: \n{}\n'.format(y_pred.shape))
    print('\ny_test shape: \n{}\n'.format(y_test.shape))
 

    print('Evaluating model . . . .\n')    
    acc = accuracy_score(y_test.astype(int), y_pred.astype(int))
    auc = roc_auc_score(y_test, y_pred)
    print('Accuracy:  {:.2f}'.format(acc))
    print('AUC Score: {:.2f}'.format(auc))
    
    output_dir = "/opt/ml/processing/output"
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)

    report_dict = {
        "evaluation": {
            "metrics": {
                "Accuracy": '{:.2f}'.format(acc), "AUC_Score": '{:.2f}'.format(auc)
            }
        }
    }

    evaluation_path = f"{output_dir}/model_evaluation_metrics.json"
    with open(evaluation_path, "w") as f:
        f.write(json.dumps(report_dict))

