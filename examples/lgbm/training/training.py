import argparse
import glob
import lightgbm as lgb
import numpy as np
import os


if __name__=='__main__':
    
    # extract training data S3 location and hyperparameter values
    parser = argparse.ArgumentParser()
    parser.add_argument('--train', type=str, default=os.environ['SM_CHANNEL_TRAIN'])
    parser.add_argument('--validation', type=str, default=os.environ['SM_CHANNEL_TEST'])
    parser.add_argument('--num_leaves', type=int, default=28)
    parser.add_argument('--max_depth', type=int, default=5)
    parser.add_argument('--learning_rate', type=float, default=0.1)
    args = parser.parse_args()
    
    print('Loading training data from {}\n'.format(args.train))
    input_files = glob.glob('{}/*.npy'.format(args.train))
    print('\nTRAINING INPUT FILE LIST: \n{}\n'.format(input_files)) 
    for file in input_files:
        if 'x_' in file:
            x_train = np.load(file)
        else:
            y_train = np.load(file)      
    print('\nx_train shape: \n{}\n'.format(x_train.shape))
    print('\ny_train shape: \n{}\n'.format(y_train.shape))
    train_data = lgb.Dataset(x_train, label=y_train)
    
    print('Loading validation data from {}\n'.format(args.validation))
    eval_input_files = glob.glob('{}/*.npy'.format(args.validation))
    print('\nVALIDATION INPUT FILE LIST: \n{}\n'.format(eval_input_files)) 
    for file in eval_input_files:
        if 'x_' in file:
            x_val = np.load(file)
        else:
            y_val = np.load(file)      
    print('\nx_val shape: \n{}\n'.format(x_val.shape))
    print('\ny_val shape: \n{}\n'.format(y_val.shape))
    eval_data = lgb.Dataset(x_val, label=y_val)
    
    print('Training model with hyperparameters:\n\t num_leaves: {}\n\t max_depth: {}\n\t learning_rate: {}\n'
          .format(args.num_leaves, args.max_depth, args.learning_rate))
    parameters = {
        'objective': 'binary',
        'metric': 'binary_logloss',
        'is_unbalance': 'true',
        'boosting': 'gbdt',
        'num_leaves': args.num_leaves,
        'max_depth': args.max_depth,
        'learning_rate': args.learning_rate,
        'verbose': 1
    }
    num_round = 10
    bst = lgb.train(parameters, train_data, num_round, eval_data)
    
    print('Saving model . . . .')
    bst.save_model('/opt/ml/model/online_shoppers_model.txt')