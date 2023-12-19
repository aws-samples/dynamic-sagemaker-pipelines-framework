# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Import native libraries

from sagemaker.model import Model
from sagemaker.workflow.pipeline_context import PipelineSession
# Import Third-party libraries
from sagemaker.workflow.steps import TrainingStep
# Import Custom libraries
from utilities.logger import Logger


########################################################################################
### If the Logger class implememntation required file handler                        ###
### self.logger = Logger(_conf)                                                      ###
########################################################################################


class CreateModelService:
    """
    Create Model Service. Create a ModelStep
    """

    def __init__(self, config: dict, model_name: str) -> "CreateModelService":
        """
        Initialization method to Create a SageMaker Model

        Args:
        ----------
        - config (dict): Application configuration
        - model_name (str): Name of Model
        """
        self.config = config
        self.model_name = model_name
        self.logger = Logger()

    def _get_network_config(self) -> dict:
        """
        Method to retreive SageMaker network configuration

        Returns:
        ----------
        - SageMaker Network Configuration dictionary
        """

        network_config_kwargs = dict(
            enable_network_isolation=False,
            security_group_ids=self.config.get("sagemakerNetworkSecurity.security_groups_id").split(
                ",") if self.config.get("sagemakerNetworkSecurity.security_groups_id") else None,
            subnets=self.config.get("sagemakerNetworkSecurity.subnets", None).split(",") if self.config.get(
                "sagemakerNetworkSecurity.subnets", None) else None,
            kms_key=self.config.get("sagemakerNetworkSecurity.kms_key"),
            encrypt_inter_container_traffic=True,
            role=self.config.get("sagemakerNetworkSecurity.role"),
        )
        return network_config_kwargs

    def _get_pipeline_session(self) -> PipelineSession:
        return PipelineSession(default_bucket=self.config.get("s3Bucket"))

    def _args(self) -> dict:
        """
        Parse method to retreive all arguments to be used to create the Model

        Returns:
        ----------
        - CreateModel arguments : dict
        """

        # parse main conf dictionary
        conf = self.config.get("models")

        args = dict(
            name=conf.get(f"{self.model_name}.name"),
            image_uri=conf.get(f"{self.model_name}.registry.InferenceSpecification.image_uri"),
            model_repack_flag=conf.get(f"{self.model_name}.registry.ModelRepack", "True"),
            # source_dir=conf.get(f"{self.model_name}.source_directory", os.environ["SMP_SOURCE_DIR_PATH"]),
            source_dir=conf.get(f"{self.model_name}.source_directory"),
            entry_point=conf.get(f"{self.model_name}.transform.entry_point", "inference.py").replace("/", ".").replace(
                ".py", ""),
            env={
                "SAGEMAKER_SUBMIT_DIRECTORY": "/opt/ml/model/code",
                "SAGEMAKER_PROGRAM": conf.get(f"{self.model_name}.transform.entry_point", "inference.py")
                .replace("/", ".")
                .replace(".py", ""),
                "SAGEMAKER_REQUIREMENTS": "requirements.txt",
            },
            enable_network_isolation=False,
            default_bucket=self.config.get(f"s3Bucket"),
        )

        return args

    def create_model(self, step_train: TrainingStep) -> Model:
        """
        Create a SageMaker Model

        Args:
        ----------
        - step_train (TrainingStep): SageMaker Training Step

        Returns:
        ----------
        - SageMaker Model

        """
        # Get SegeMaker Network Configuration
        sagemaker_network_config = self._get_network_config()
        self.logger.log_info(f"{'-' * 50} Start SageMaker Model Creation {self.model_name} {'-' * 50}")
        self.logger.log_info(f"SageMaker network config: {sagemaker_network_config}")

        # Get Arg for CreateModel Step
        args = self._args()
        self.logger.log_info(f"Arguments used: {args}")

        # Check ModelRepack Flag
        _model_repack_flag = args.get("model_repack_flag")

        vpc_config = {}
        if sagemaker_network_config.get("security_group_ids", None): vpc_config.update(
            {'SecurityGroupIds': sagemaker_network_config.get("security_group_ids")})
        if sagemaker_network_config.get("subnets", None): vpc_config.update(
            {'Subnets': sagemaker_network_config.get("subnets")})
        if not vpc_config: vpc_config = None

        model = ''
        if _model_repack_flag == "True":
            model = Model(
                name=args["name"],
                image_uri=args["image_uri"],
                source_dir=args["source_dir"],
                entry_point=args["entry_point"],
                model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
                role=sagemaker_network_config["role"],
                vpc_config=vpc_config,
                enable_network_isolation=args["enable_network_isolation"],
                sagemaker_session=self._get_pipeline_session(),
                model_kms_key=sagemaker_network_config["kms_key"],
            )

        elif _model_repack_flag == "False":
            model = Model(
                name=args["name"],
                image_uri=args["image_uri"],
                env=args["env"],
                model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
                role=sagemaker_network_config["role"],
                vpc_config=vpc_config,
                enable_network_isolation=args.get("enable_network_isolation"),
                sagemaker_session=self._get_pipeline_session(),
                model_kms_key=sagemaker_network_config["kms_key"],
            )
            print

        self.logger.log_info(f"SageMaker Model - {self.model_name} - Created")
        return model
