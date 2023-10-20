# Inserting an inference.py to register the fine-tuned model. 
# This pattern demands the inference logic be available in a batch transform step.

# Replace this script with your inference logic, and place model dependencies for your model under llm-text-summarization/transform.
# e.x: s3://jumpstart-cache-prod-us-east-1/huggingface-infer/prepack/v1.0.0/infer-prepack-huggingface-llm-falcon-40b-bf16.tar.gz
# refer: https://huggingface.co/docs/sagemaker/inference#user-defined-code-and-modules

# extract Model ID from: https://sagemaker.readthedocs.io/en/stable/doc_utils/pretrainedmodels.html.
# then use the code snippet below. also use to get the appropriate container in 'deploy_image_uri'

'''
from sagemaker import image_uris, model_uris

model_id, model_version, = (
    "huggingface-llm-falcon-40b-bf16",
    "*",
)
inference_instance_type = "ml.p3.2xlarge"

# Retrieve the inference docker container uri. This is the base HuggingFace container image for the default model above.
deploy_image_uri = image_uris.retrieve(
region=None,
framework=None, # automatically inferred from model_id
image_scope="inference",
model_id=model_id,
model_version=model_version,
instance_type=inference_instance_type,
)

# Retrieve the model uri.
model_uri = model_uris.retrieve(
model_id=model_id, model_version=model_version, model_scope="inference"
)
'''
