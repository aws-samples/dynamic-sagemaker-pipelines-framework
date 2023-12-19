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
