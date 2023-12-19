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
from typing import Union, Tuple

from pipeline.helper import get_chain_input_file
# Import third-party libraries
from sagemaker.transformer import Transformer
from sagemaker.workflow.functions import Join
from sagemaker.workflow.pipeline_context import PipelineSession
# Import custom libraries
from utilities.logger import Logger


class TransformService:
    """
    SageMaker Transform Step service.
    """

    def __init__(self, config: dict, model_name: str, step_config: dict, model_step_dict: dict) -> "TransformService":
        """
        Initialization method to TransformStep

        Args:
        ----------
        - config (dict): Application configuration
        - model_name (str): Name of Model
        - run_mode (str): run mode definition. Can be 'train' or 'inference'
        """
        self.config = config
        self.model_name = model_name
        self.step_config = step_config
        self.model_step_dict = model_step_dict
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

    def _args(self) -> dict:
        """
        Parse method to retreive all arguments to be used to create the Model

        Returns:
        ----------
        - Transform Step arguments : dict
        """

        # parse main conf dictionary
        conf = self.config.get("models")

        args = dict(
            image_uri=conf.get(f"{self.model_name}.transform.image_uri"),
            base_job_name=conf.get(f"{self.model_name}.transform.base_job_name", "default-transform-job-name"),
            instance_count=conf.get(f"{self.model_name}.transform.instance_count", 1),
            instance_type=conf.get(f"{self.model_name}.transform.instance_type", "ml.m5.2xlarge"),
            strategy=conf.get(f"{self.model_name}.transform.strategy", None),
            assemble_with=conf.get(f"{self.model_name}.transform.assemble_with", None),
            join_source=conf.get(f"{self.model_name}.transform.join_source", None),
            split_type=conf.get(f"{self.model_name}.transform.split_type", None),
            content_type=conf.get(f"{self.model_name}.transform.content_type", "text/csv"),
            max_payload=conf.get(f"{self.model_name}.transform.max_payload", None),
            volume_size=conf.get(f"{self.model_name}.transform.volume_size", 50),
            max_runtime_in_seconds=conf.get(f"{self.model_name}.transform.max_runtime_in_seconds", 3600),
            input_filter=conf.get(f"{self.model_name}.transform.input_filter", None),
            output_filter=conf.get(f"{self.model_name}.transform.output_filter", None),
            tags=conf.get(f"{self.model_name}.transform.tags", None),
            env=conf.get(f"{self.model_name}.transform.env", None),
        )

        return args

    def _get_train_inputs_outputs(self, transform_data: dict) -> Tuple[str, str]:
        """
        Method to retreive dynamically the files to be Transformed

        Args:
        ----------
        - transform_data (dict): Dictionary of files

        Return
        ----------
        - input_data_file_s3path (str): Input path location
        - output_file_s3path (str): Output path location
        """

        evaluate_channels = list(transform_data.get("channels", "train").keys())
        if len(evaluate_channels) != 1:
            raise Exception(f"Only one channel allowed within Transform evaluate section. {evaluate_channels} found.")
        else:
            channel = evaluate_channels[0]
            self.logger.log_info("INFO", f"During TransformService, one evaluate channel {channel} found.")

        channel_full_name = f"channels.{channel}"
        bucket_prefix = transform_data.get(f"{channel_full_name}.inputBucketPrefix") + '/' if transform_data.get(
            f"{channel_full_name}.inputBucketPrefix") else ""
        s3_bucket_name = transform_data.get(f"{channel_full_name}.s3BucketName")

        # Transform data source
        files = list(transform_data.get(f"{channel_full_name}.dataFiles", ""))

        if len(files) == 1:
            file = files[0]
            self.logger.log_info("During TransformService, one evaluate file {file} found.")
            file_name = file.get("fileName")

            if file_name.startswith("s3://"):
                input_data_file_s3path = file_name
            else:
                input_data_file_s3path = f"s3://{s3_bucket_name}/{bucket_prefix}/{file_name}"

        elif len(files) == 0:
            self.logger.log_info("INFO", "During TransformService, no evaluate file found.")
            input_data_file_s3path = None
        else:
            raise Exception(f"Maximum one file allowed within evaluation.dataFiles section. {len(files)} found.")

        output_file_s3path = f"s3://{s3_bucket_name}/{bucket_prefix}{self.model_name}/predictions/transform"

        return input_data_file_s3path, output_file_s3path

    def _get_chain_input(self):
        """
        Method to retreive SageMaker chain inputs

        Returns:
        ----------
        - SageMaker Processing Inputs list
        """
        channels_conf = self.config.get(f"models.{self.model_name}.transform.channels", {"train": []})
        if len(channels_conf.keys()) != 1:
            raise Exception("Transform step can only have one channel.")
        channel_name = list(channels_conf.keys())[0]

        dynamic_processing_input = []
        chain_input_source_step = self.step_config.get("chain_input_source_step", [])
        chain_input_additional_prefix = self.step_config.get("chain_input_additional_prefix", "")
        args = self._args()

        if len(chain_input_source_step) == 1:
            self.logger.log_info(
                "INFO", f"During TransformService, chain input source step {chain_input_source_step} found."
            )
            for source_step_name in chain_input_source_step:
                chain_input_path = get_chain_input_file(
                    source_step_name=source_step_name,
                    steps_dict=self.model_step_dict,
                    source_output_name=channel_name,
                )

                input_data_file_s3path = Join("/", [chain_input_path, chain_input_additional_prefix])

        elif len(chain_input_source_step) == 0:
            self.logger.log_info(
                "INFO", "During TransformService, no chain input found. Input from transform.dataFiles"
            )
            return None
        else:
            raise Exception(
                f"Maximum one chain input allowed for TransformService. {len(chain_input_source_step)} found."
            )

        return input_data_file_s3path

    def _run_batch_transform(
            self,
            input_data: str,
            output_path: str,
            network_config: dict,
            sagemaker_model_name: str,
            args: dict,
    ) -> dict:
        """
        Method to setup a SageMaker Transformer and Transformer arguments

        Args:
        ----------
        - input_data (str): Input data path
        - output_path (str): Output data path
        - network_config (dict): SageMaker Network Config
        - sagemaker_model_name (str): SageMaker Model Name
        - args (dict): SageMaker TransformStep arguments

        Return
        ----------
        - step_transform_args : TransformStep Args
        """

        # define a transformer
        transformer = Transformer(
            model_name=sagemaker_model_name,
            instance_count=args["instance_count"],
            instance_type=args["instance_type"],
            strategy=args["strategy"],
            assemble_with=args["assemble_with"],
            max_payload=args["max_payload"],
            output_path=output_path,
            sagemaker_session=PipelineSession(
                default_bucket=self.config.get("models.s3Bucket"),
            ),
            output_kms_key=network_config["kms_key"],
            accept=args["content_type"],
            tags=args["tags"],
            env=args["env"],
            base_transform_job_name=args["base_job_name"],
            volume_kms_key=network_config["kms_key"],
        )

        step_transform_args = transformer.transform(
            data=input_data,
            content_type=args["content_type"],
            split_type=args["split_type"],
            input_filter=args["input_filter"],
            output_filter=args["output_filter"],
            join_source=args["join_source"],
        )

        return step_transform_args

    def transform(
            self,
            sagemaker_model_name: str,
    ) -> Union[dict, dict]:
        """
        Method to setup SageMaker TransformStep

        Args:
        ----------
        - step_config (dict)
        - steps_dict (dict)
        - sagemaker_model_name (str)
        """

        step_transform_args = None
        self.logger.log_info(f"{'-' * 40} {self.model_name} {'-' * 40}")
        self.logger.log_info(f"Starting {self.model_name} batch transform")

        # Get SageMaker network configuration
        sagemaker_network_config = self._get_network_config()
        self.logger.log_info(f"SageMaker network config: {sagemaker_network_config}")

        transform_data = self.config.get(f"models.{self.model_name}.transform")
        sagemaker_config = self._args()

        if self._get_chain_input():
            input_data_file_s3path = self._get_chain_input()
            output_data_file_s3path = None
        else:
            input_data_file_s3path, output_data_file_s3path = self._get_train_inputs_outputs(
                transform_data
            )

        step_transform_args = self._run_batch_transform(
            input_data=input_data_file_s3path,
            output_path=output_data_file_s3path,
            network_config=sagemaker_network_config,
            sagemaker_model_name=sagemaker_model_name,
            args=sagemaker_config,
        )

        return step_transform_args
