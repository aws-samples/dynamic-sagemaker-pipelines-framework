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
import os

# Import Third-party libraries
import boto3
import sagemaker
from pipeline.helper import get_chain_input_file
from sagemaker.network import NetworkConfig
from sagemaker.processing import (
    FrameworkProcessor,
    ProcessingInput,
    ProcessingOutput,
    RunArgs,
)
from sagemaker.workflow.pipeline_context import PipelineSession
# Import Custom libraries
from utilities.logger import Logger

########################################################################################
### If the Logger class implememntation required file handler                        ###
### self.logger = Logger(_conf)                                                      ###
########################################################################################

session = boto3.session.Session()
region_name = session.region_name
client_sagemaker_obj = boto3.client("sagemaker", region_name=region_name)


class ModelMetricsService:
    """
    Create an Evaluate function to generate the model metrcis
    """

    def __init__(self, config: dict, model_name: str, step_config: dict,
                 model_step_dict: dict) -> "ModelMetricsService":
        """
        Initialization method to Create ModelMetricsService

        Args:
        ----------
        - config (dict): Application configuration
        - model_name (str): Name of Model
        """
        self.config = config
        self.model_name = model_name
        self.step_config = step_config
        self.model_step_dict = model_step_dict
        self.logger = Logger()

    def _get_pipeline_session(self) -> PipelineSession:
        return PipelineSession(default_bucket=self.config.get("s3Bucket"))

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
            encrypt_inter_container_traffic=True,
        )
        return network_config_kwargs

    def _sagemaker_args(self):
        """
        Parse method to retreive all sagemaker arguments
        """
        conf = self.config.get(f"models.{self.model_name}.evaluate")

        args = dict(
            image_uri=conf.get("image_uri"),
            entry_point=conf.get("entry_point"),
            base_job_name=conf.get("base_job_name", "default-model-metrics-job-name"),
            instance_count=conf.get("instance_count", 1),
            instance_type=conf.get("instance_type", "ml.m5.2xlarge"),
            strategy=conf.get("strategy", "SingleRecord"),
            max_payload=conf.get("max_payload", None),
            volume_size_in_gb=conf.get("volume_size_in_gb", 50),
            max_runtime_in_seconds=conf.get("max_runtime_in_seconds", 3600),
            s3_data_distribution_type=conf.get("s3_data_distribution_type", "FullyReplicated"),
            s3_data_type=conf.get("s3_data_type", "S3Prefix"),
            s3_input_mode=conf.get("s3_input_mode", "File"),
            role=self.config.get("sagemakerNetworkSecurity.role"),
            kms_key=self.config.get("sagemakerNetworkSecurity.kms_key", None),
            tags=conf.get("tags", None),
            env=conf.get("env", None),
        )

        self.logger.log_info("Arguments Instantiates", f"Args: {args}")

        return args

    def _get_static_input_list(self) -> list:
        """
        Method to retreive SageMaker static inputs

        Returns:
        ----------
        - SageMaker Processing Inputs list
        
        """
        conf = self.config.get(f"models.{self.model_name}.evaluate")
        # Get the total number of input files
        input_files_list = list()
        for channel in conf.get("channels", {}).keys(): input_files_list.append(
            conf.get(f"channels.{channel}.dataFiles", [])[0])
        return input_files_list

    def _get_static_input(self, input_local_filepath):
        """
        Method to retreive SageMaker static inputs

        Returns:
        ----------
        - SageMaker Processing Inputs list
        
        """
        static_inputs = []

        conf = self.config.get(f"models.{self.model_name}.evaluate")
        if isinstance(conf.get("channels", {}), dict):
            # Get the total number of input files
            input_files_list = self._get_static_input_list()
            if len(input_files_list) >= 7:
                raise Exception("Static inputs for metrics should not exceed 7")
            for file in input_files_list:
                if file.get("fileName").startswith("s3://"):
                    _source = file.get("fileName")
                else:
                    bucket = conf.get("channels.train.s3Bucket")
                    input_prefix = conf.get("channels.train.s3InputPrefix", "")
                    _source = os.path.join(bucket, input_prefix, file.get("fileName"))

                temp = ProcessingInput(
                    input_name=file.get("sourceName", ""),
                    source=_source,
                    destination=os.path.join(input_local_filepath, file.get("sourceName", "")),
                    s3_data_distribution_type=conf.get("s3_data_distribution_type", "FullyReplicated"),
                )
                static_inputs.append(temp)

        return static_inputs

    def _get_chain_input(self, input_local_filepath):
        """
        Method to retreive SageMaker chain inputs

        Returns:
        ----------
        - SageMaker Processing Inputs list
        """
        dynamic_inputs = []
        chain_input_source_step = self.step_config.get("chain_input_source_step", [])

        channels_conf = self.config.get(f"models.{self.model_name}.evaluate.channels", "train")
        if isinstance(channels_conf, str):
            # no datafile input
            channel_name = channels_conf
        else:
            # find datafile input
            if len(channels_conf.keys()) != 1:
                raise Exception("Evaluate step can only have one channel.")
            channel_name = list(channels_conf.keys())[0]

        for source_step_name in chain_input_source_step:
            chain_input_path = get_chain_input_file(
                source_step_name=source_step_name,
                steps_dict=self.model_step_dict,
                source_output_name=channel_name,
            )

            temp = ProcessingInput(
                input_name=f"{source_step_name}-input",
                source=chain_input_path,
                destination=os.path.join(input_local_filepath, f"{source_step_name}-{channel_name}"),
            )
            dynamic_inputs.append(temp)

        return dynamic_inputs

    def _get_processing_inputs(self, input_destination) -> list:
        """
        Method to get additional processing inputs
        """
        # Instantiate a list of inputs
        temp_static_input = self._get_static_input(input_destination)
        temp_dynamic_input = self._get_chain_input(input_destination)
        processing_inputs = temp_static_input + temp_dynamic_input
        return processing_inputs

    def _generate_model_metrics(
            self,
            input_destination: str,
            output_source: str,
            output_destination: str,
    ) -> RunArgs:

        """
        Method to create the ProcessorStep args to calculate metrics

        Args:
        ----------
        - input_destination(str): path for input destination
        - output_source (str): path for output source
        - output_destination (str): path for output destination
        """

        # Get metrics Config
        # metrics_config = self.config.get(f"models.{self.model_name}.evaluate")
        # Get Sagemaker Network config params
        sagemakernetworkconfig = self._get_network_config()
        # Get Sagemaker config params
        args = self._sagemaker_args()
        # Replace entry point path leverage python -m for local dependencies
        entrypoint_command = args.get("entry_point").replace("/", ".").replace(".py", "")

        # Create SageMaker Processor Instance
        processor = FrameworkProcessor(
            image_uri=args.get("image_uri"),
            estimator_cls=sagemaker.sklearn.estimator.SKLearn,  # ignore bc of image_uri
            framework_version=None,
            role=args.get("role"),
            command=["python", "-m", entrypoint_command],
            instance_count=args.get("instance_count"),
            instance_type=args.get("instance_type"),
            volume_size_in_gb=args.get("volume_size_in_gb"),
            volume_kms_key=args.get("kms_key"),
            output_kms_key=args.get("kms_key"),
            max_runtime_in_seconds=args.get("max_runtime_in_seconds"),
            base_job_name=args.get("base_job_name"),
            sagemaker_session=self._get_pipeline_session(),
            env=args.get("env"),
            tags=args.get("tags"),
            network_config=NetworkConfig(**sagemakernetworkconfig),
        )

        generate_model_metrics_args = processor.run(
            inputs=self._get_processing_inputs(input_destination),
            outputs=[
                ProcessingOutput(
                    source=output_source,
                    destination=output_destination,
                    output_name="model_evaluation_metrics",
                ),
            ],
            source_dir=self.config.get(
                f"models.{self.model_name}.source_directory",
                os.getenv("SMP_SOURCE_DIR_PATH")
            ),
            code=args.get("entry_point"),
            wait=True,
            logs=True,
            job_name=args.get("base_job_name"),
        )

        return generate_model_metrics_args

    def calculate_model_metrics(self) -> RunArgs:
        """
        Method to calculate models metrics
        """

        self.logger.log_info(f"{'-' * 40} {self.model_name} {'-' * 40}")
        evaluate_data = self.config.get(f"models.{self.model_name}.evaluate")
        if isinstance(evaluate_data.get("channels", "train"), dict):
            evaluate_channels = list(evaluate_data.get("channels").keys())
            # Iterate through evaluate channels
            if len(evaluate_channels) != 1:
                raise Exception(f" Only one channel allowed within evaluation section. {evaluate_channels} found.")
            else:
                channel = evaluate_channels[0]
                self.logger.log_info(f"During ModelMetricsService, one evaluate channel {channel} found.")

            channel_full_name = f"channels.{channel}"
            bucket_prefix = evaluate_data.get(f"{channel_full_name}.bucket_prefix", "")
            s3_bucket_name = evaluate_data.get(f"{channel_full_name}.s3BucketName")
            processing_input_destination = evaluate_data.get(
                f"{channel_full_name}.InputLocalFilepath", "/opt/ml/processing/input/"
            )
            processing_output_source = evaluate_data.get(
                f"{channel_full_name}.OuputLocalFilepath", "/opt/ml/processing/output/"
            )
            processing_output_key = os.path.join(
                bucket_prefix,
                self.model_name,
                "evaluation",
            )
            processing_output_destination = f"s3://{s3_bucket_name}/{processing_output_key}/"
        else:
            processing_input_destination = "/opt/ml/processing/input/"
            processing_output_source = "/opt/ml/processing/output/"
            processing_output_destination = None

        generate_model_metrics_args = self._generate_model_metrics(
            input_destination=processing_input_destination,
            output_source=processing_output_source,
            output_destination=processing_output_destination,
        )

        self.logger.log_info(f" Model evaluate completed.")

        return generate_model_metrics_args
