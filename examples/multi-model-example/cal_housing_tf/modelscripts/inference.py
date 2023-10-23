import json
import os

import numpy as np

print(f"My location: {os.listdir()}")
print(f"Dir of /opt/ml: {os.listdir('/opt/ml')}")
print(f"Dir of /opt/ml/model: {os.listdir('/opt/ml/model')}")

print(f"{'-' * 40} Start printing Env Var {'-' * 40}")
for name, value in os.environ.items():
    print("{0}: {1}".format(name, value))
print(f"{'-' * 40} Finish printing Env Var {'-' * 40}")

model_dir = "/opt/ml/model"
print("numpy version", np.__version__)


def read_csv(csv):
    return np.array([[float(j) for j in i.split(",")] for i in csv.splitlines()])


def input_handler(data, context):
    """ Pre-process request input before it is sent to TensorFlow Serving REST API
    Args:
        data (obj): the request data, in format of dict or string
        context (Context): an object containing request and configuration details
    Returns:
        (dict): a JSON-serializable dict that contains request body and headers
    """
    print(f"InputHandler, request content type is {context.request_content_type}")
    print(f"InputHandler, model name is {context.model_name}")
    print(f"InputHandler, method is {context.method}")
    print(f"InputHandler, rest_uri is {context.rest_uri}")
    print(f"InputHandler, custom_attributes is {context.custom_attributes}")
    print(f"InputHandler, accept_header is {context.accept_header}")
    print(f"InputHandler, content_length is {context.content_length}")

    if context.request_content_type == 'application/json':
        # pass through json (assumes it's correctly formed)
        d = data.read().decode('utf-8')
        return d if len(d) else ''
    if context.request_content_type == 'text/csv':
        payload = data.read().decode('utf-8')
        inputs = read_csv(payload)
        print(inputs[:10])
        input_data = {'instances': inputs.tolist()}
        return json.dumps(input_data)


def output_handler(data, context):
    """Post-process TensorFlow Serving output before it is returned to the client.
    Args:
        data (obj): the TensorFlow serving response
        context (Context): an object containing request and configuration details
    Returns:
        (bytes, string): data to return to client, response content type
    """
    print(f"OutputHandler, hello world!")
    status_code = data.status_code
    content = data.content

    if status_code != 200:
        raise ValueError(content.decode('utf-8'))

    response_content_type = context.accept_header
    prediction = data.content

    print(f"Prediction type is {type(prediction)}, {prediction}")
    print(f"Prediction is {prediction}")

    return prediction, response_content_type
