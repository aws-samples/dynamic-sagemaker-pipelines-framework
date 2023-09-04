import glob
import numpy as np
import os
import pandas as pd
from sklearn.model_selection import train_test_split


if __name__=='__main__':
    
    
    input_file = glob.glob('{}/*.csv'.format('/opt/ml/processing/input'))
    print('\nINPUT FILE: \n{}\n'.format(input_file))   
    df = pd.read_csv(input_file[0])
    
    # minor preprocessing (drop some uninformative columns etc.)
    print('Preprocessing the dataset . . . .')   
    df_clean = df.drop(['Month','Browser','OperatingSystems','Region','TrafficType','Weekend'], axis=1)
    visitor_encoded = pd.get_dummies(df_clean['VisitorType'], prefix='Visitor_Type', drop_first = True)
    df_clean_merged = pd.concat([df_clean, visitor_encoded], axis=1).drop(['VisitorType'], axis=1)
    X = df_clean_merged.drop('Revenue', axis=1)
    y = df_clean_merged['Revenue']
    
    # split the preprocessed data with stratified sampling for class imbalance
    X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=2, test_size=.2)

    # save to container directory for uploading to S3
    print('Saving the preprocessed dataset . . . .')   
    train_data_output_path = os.path.join('/opt/ml/processing/train', 'x_train.npy')
    np.save(train_data_output_path, X_train.to_numpy())
    train_labels_output_path = os.path.join('/opt/ml/processing/train', 'y_train.npy')
    np.save(train_labels_output_path, y_train.to_numpy())    
    test_data_output_path = os.path.join('/opt/ml/processing/test', 'x_test.npy')
    np.save(test_data_output_path, X_test.to_numpy())
    test_labels_output_path = os.path.join('/opt/ml/processing/test', 'y_test.npy')
    np.save(test_labels_output_path, y_test.to_numpy())   