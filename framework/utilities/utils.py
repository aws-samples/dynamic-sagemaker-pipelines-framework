import boto3

class S3Utilities:
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(S3Utilities, cls).__new__(cls)
        return cls._instance
    
    @staticmethod
    def split_s3_uri(s3_uri: str) -> tuple:
        split_list = s3_uri.split("//")[1].split("/")
        s3_bucket_name = split_list[0]
        s3_key = "/".join(split_list[1:])
        return s3_bucket_name, s3_key


class ParamStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ParamStore, cls).__new__(cls)
        return cls._instance

    @staticmethod
    def get_parameter_value(param_key: str) -> str:
        boto_session = boto3.Session()
        client = boto_session.client(service_name="ssm")
        param = client.get_parameter(Name=param_key)
        return param["Parameter"]["Value"]


class PipelineParamVariable:
    _instance = None
    _params = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PipelineParamVariable,cls).__new__(cls)
            return cls._instance

    @property
    def pipeline_params(self) -> dict:
        return self._params

    @pipeline_params.setter
    def pipeline_params(self, params: dict):
        if isinstance(params, dict):
            self._params.update(params)
        else:
            raise ValueError("Params must be a dictionary")

params_obj = PipelineParamVariable()