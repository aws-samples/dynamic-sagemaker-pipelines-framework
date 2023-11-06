# LLM Example Data Source

## Data Information
We use the samsum https://huggingface.co/datasets/samsum dataset hosted at huggingface for this example.

More info on the dataset:

https://huggingface.co/datasets/samsum


## Data Download and S3 Upload
To download the data, run the following code block. The data files are named as **samsum-{train/test/validation}.arrow**
install requirements via: pip install aiobotocore, datasets, 
```
from datasets import load_dataset
from datasets import load_dataset_builder
import aiobotocore.session

# set up a profile in your aws config file: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
profile = 'default'
s3_session = aiobotocore.session.AioSession(profile=profile) 
storage_options = {"session": s3_session}

output_dir = "s3://<BUCKET>/<PREFIX>"
builder = load_dataset_builder("samsum")
builder.download_and_prepare(output_dir, storage_options=storage_options, file_format="arrow")
```
