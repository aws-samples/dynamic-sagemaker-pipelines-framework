
from collections import namedtuple
import glob
import json
import logging
import os
import re

import lightgbm as lgb
import numpy as np
from sagemaker_inference import content_types, encoder

NUM_FEATURES = 12

class ModelHandler(object):
    """
    A lightGBM Model handler implementation.
    """

    def __init__(self):
        self.initialized = False
        self.model = None

    def initialize(self, context):
        """
        Initialize model. This will be called during model loading time
        :param context: Initial context contains model server system properties.
        :return: None
        """
        self.initialized = True
        properties = context.system_properties
        model_dir = properties.get("model_dir") 
        self.model = lgb.Booster(model_file=os.path.join(model_dir,'online_shoppers_model.txt'))
       

    def preprocess(self, request):
        """
        Transform raw input into model input data.
        :param request: list of raw requests
        :return: list of preprocessed model input data
        """        
        payload = request[0]['body']
        payload= payload[payload.find(b'\n')+1:]
        data = np.frombuffer(payload, dtype=np.float64)
        data = data.reshape((data.size // NUM_FEATURES, NUM_FEATURES))
        return data

    def inference(self, model_input):
        """
        Internal inference methods
        :param model_input: transformed model input data list
        :return: list of inference output in numpy array
        """
        prediction = self.model.predict(model_input)
        print('prediction: ', prediction)
        return prediction

    def postprocess(self, inference_output):
        """
        Post processing step - converts predictions to str
        :param inference_output: predictions as numpy
        :return: list of inference output as string
        """

        return [str(inference_output.tolist())]
        
    def handle(self, data, context):
        """
        Call preprocess, inference and post-process functions
        :param data: input data
        :param context: mms context
        """
        
        model_input = self.preprocess(data)
        model_out = self.inference(model_input)
        return self.postprocess(model_out)

_service = ModelHandler()


def handle(data, context):
    if not _service.initialized:
        _service.initialize(context)

    if data is None:
        return None

    return _service.handle(data, context)
