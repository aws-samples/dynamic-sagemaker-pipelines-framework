# Tensorflow Example Data Source

## Data Information
We use the Online Shoppers Purchasing Intention Dataset.

More info on the dataset:

This dataset was obtained from  UCI's Machine Learning Library. https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset


## Data Download
Download the data locally from [here](https://archive.ics.uci.edu/static/public/468/online+shoppers+purchasing+intention+dataset.zip). The data file is named **online_shoppers_intention.csv**
```

Then reference the preprocessing script(written for sagemaker processing jobs) to create train test splits.

## Upload to S3
```
aws s3 cp <LOCAL>/x_train.npy s3://<BUCKET>/lightGBM/train
aws s3 cp <LOCAL>/y_train.npy s3://<BUCKET>/lightGBM/train

aws s3 cp <LOCAL>/x_test.npy s3://<BUCKET>/lightGBM/test
aws s3 cp <LOCAL>/y_test.npy s3://<BUCKET>/lightGBM/test

```