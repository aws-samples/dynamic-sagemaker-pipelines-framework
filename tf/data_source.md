# Tensorflow Example Data Source

## Data Information
We use the California housing dataset.

More info on the dataset:

This dataset was obtained from the StatLib repository. http://lib.stat.cmu.edu/datasets/

The target variable is the median house value for California districts.

This dataset was derived from the 1990 U.S. census, using one row per census block group. A block group is the smallest geographical unit for which the U.S. Census Bureau publishes sample data (a block group typically has a population of 600 to 3,000 people).

## Data Download
To download the data, run the following code block. The data file name is **cal_housing.data**
```
import boto3

region = "<your region>"
s3 = boto3.client("s3")
s3.download_file(
    f"sagemaker-example-files-prod-{region}",
    "datasets/tabular/california_housing/cal_housing.tgz",
    "cal_housing.tgz",
)

import tarfile
with tarfile.open("cal_housing.tgz") as tar:
    tar.extractall(path="tf/train_data")
```

## Upload to S3
```
aws s3 cp tf/train_data/CaliforniaHousing/cal_housing.data s3://<BUCKET>/<PREFIX>/cal_housing.data
```