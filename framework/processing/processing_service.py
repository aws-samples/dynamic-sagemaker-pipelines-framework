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

import json
import os
from typing import Tuple

from pipeline.helper import get_chain_input_file, look_up_step_type_from_step_name
from sagemaker.network import NetworkConfig
from sagemaker.processing import (
    FrameworkProcessor,
    ProcessingInput,
    ProcessingOutput
)
from sagemaker.sklearn import estimator
from sagemaker.workflow.pipeline_context import PipelineSession


class ProcessingService:
    """
    Class to handle the creation of processing steps

    Attributes:
    ----------
    - config: dict
        - Configuration dictionary
    - model_name: str
        - Model name
    - step_config: dict
        - Processing step configuration dictionary
    - model_step_dict: dict
        - Dictionary of model processing steps
    """

    def __init__(self, config: dict, model_name: str, step_config: dict, model_step_dict: dict):
        self.config = config
        self.model_name = model_name
        self.step_config = step_config
        self.model_step_dict = model_step_dict

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

    def _get_pipeline_session(self) -> PipelineSession:
        """
        Method to retreive SageMaker pipeline session

        Returns:
        ----------
        - SageMaker pipeline session
        """
        return PipelineSession(default_bucket=self.config.get("s3Bucket"))

    def _args(self) -> dict:
        """
        Parse method to retreive all arguments to be used to create the processing stop

        Returns:
        ----------
        - Processing Step arguments : dict
        """

        # parse main conf dictionary
        conf = self.config.get(f"models.{self.model_name}.{self.step_config.get('step_type')}")
        source_dir = self.config.get(
            f"models.{self.model_name}.source_directory", 
            os.getenv("SMP_SOURCE_DIR_PATH")
        )

        args = dict(
            image_uri=conf.get("image_uri"),
            base_job_name=conf.get("base_job_name", "default-processing-job-name"),
            entry_point=conf.get("entry_point"),
            instance_count=conf.get("instance_count", 1),
            instance_type=conf.get("instance_type", "ml.m5.2xlarge"),
            volume_size_in_gb=conf.get("volume_size_in_gb", 32),
            max_runtime_seconds=conf.get("max_runtime_seconds", 3000),
            tags=conf.get("tags", None),
            env=conf.get("env", None),
            source_directory=source_dir,
            framework_version=conf.get("framework_version", "0"),
            role=self.config.get("sagemakerNetworkSecurity.role"),
            kms_key=self.config.get("sagemakerNetworkSecurity.kms_key", None),
            s3_data_distribution_type=conf.get("s3_data_distribution_type", "FullyReplicated"),
            s3_data_type=conf.get("s3_data_type", "S3Prefix"),
            s3_input_mode=conf.get("s3_input_mode", "File"),
            s3_upload_mode=conf.get("s3_upload_mode", "EndOfJob"),
        )

        return args

    def _get_static_input_list(self) -> list:
        """
        Method to retreive SageMaker static inputs

        Returns:
        ----------
        - SageMaker Processing Inputs list
        
        """
        conf = self.config.get(f"models.{self.model_name}.{self.step_config.get('step_type')}")
        # Get the total number of input files
        input_files_list = list()
        for channel in conf.get("channels", {}).keys():
            temp_data_files = conf.get(f"channels.{channel}.dataFiles", [])
            if temp_data_files:
                input_files_list.append(temp_data_files[0])
        return input_files_list

    def _get_static_input(self) -> Tuple[list, int]:
        """
        Method to retreive SageMaker static inputs

        Returns:
        ----------
        - SageMaker Processing Inputs list
        
        """
        # parse main conf dictionary
        conf = self.config.get(f"models.{self.model_name}.{self.step_config.get('step_type')}")
        args = self._args()
        # Get the total number of input files
        input_files_list = self._get_static_input_list()
        static_inputs = []
        input_local_filepath = "/opt/ml/processing/input/"

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
                s3_data_distribution_type=args.get("s3_data_distribution_type")
            )

            static_inputs.append(temp)

        return static_inputs

    def _get_static_manifest_input(self):
        """
        Method to create a manifest file to reference SageMaker Processing Inputs
        To create a manifest file the conf file should have s3Bucket and s3InputPrefix
        and fileName should contain only the name of the file.

        Returns:
        ----------
        - SageMaker Processing Inputs list
        
        Notes:
        ----------
        SageMaker Processing Job API has a limit of 10 ProcessingInputs
        2 of these will be used for code and entrypoint input,
        If there are more than 7 input data files, Manifest file needs to
        be used to reference ProcessingInput data.
        """
        conf = self.config.get(f"models.{self.model_name}.{self.step_config.get('step_type')}")
        bucket = conf.get("channels.train.s3Bucket")
        input_prefix = conf.get("channels.train.s3InputPrefix", "")
        input_local_file_path = conf.get("inputLocalFilepath", "/opt/ml/processing/input")
        manifest_local_filename = f"{self.model_name}_{self.step_config.get('step_type')}_input.manifest"
        input_files_list = self._get_static_input_list()

        manifest_list = []
        for file in input_files_list:
            manifest_list.append(file.get("fileName"))

        manifest_data = [{"prefix": f"s3://{bucket}/{input_prefix}"}, *manifest_list]

        with open(manifest_local_filename, "w") as outfile:
            json.dump(manifest_data, outfile, indent=1)

        manifest_input = ProcessingInput(
            source=manifest_local_filename,
            destination=os.path.join(input_local_file_path, "train"),
            s3_data_type="ManifestFile",
        )

        return [manifest_input]

    def _get_chain_input(self):
        """
        Method to retreive SageMaker chain inputs

        Returns:
        ----------
        - SageMaker Processing Inputs list
        """
        dynamic_processing_input = []
        chain_input_source_step = self.step_config.get("chain_input_source_step", [])
        input_local_filepath = "/opt/ml/processing/input/"
        args = self._args()

        for source_step_name in chain_input_source_step:
            source_step_type = look_up_step_type_from_step_name(
                source_step_name=source_step_name,
                config=self.config
            )

            for channel in self.config["models"][self.model_name][source_step_type].get('channels',["train"]):
                chain_input_path = get_chain_input_file(
                    source_step_name=source_step_name,
                    steps_dict=self.model_step_dict,
                    source_output_name=channel,
                )

                temp = ProcessingInput(
                    input_name=f"{source_step_name}-input-{channel}",
                    source=chain_input_path,
                    destination=os.path.join(input_local_filepath, f"{source_step_name}-input-{channel}"),
                    s3_data_distribution_type=args.get("s3_data_distribution_type")
                )
                dynamic_processing_input.append(temp)

        return dynamic_processing_input

    def _get_processing_inputs(self) -> list:
        """
        Method to retreive SageMaker processing inputs

        Returns:
        ----------
        - SageMaker Processing Inputs list
        """

        temp_static_input = []
        if len(self._get_static_input_list()) >= 7:
            temp_static_input = self._get_static_manifest_input()
        else:
            temp_static_input = self._get_static_input()

        dynamic_processing_input = self._get_chain_input()

        return temp_static_input + dynamic_processing_input

    def _get_processing_outputs(self) -> list:
        """
        Method to retreive SageMaker processing outputs

        Returns:
        ----------
        - SageMaker Processing Outputs list
        """
        processing_conf = self.config.get(f"models.{self.model_name}.{self.step_config.get('step_type')}")
        processing_outputs = []
        processing_output_local_filepath = processing_conf.get("location.outputLocalFilepath",
                                                               "/opt/ml/processing/output")

        source_step_type = self.step_config["step_type"]

        output_names = list(
            self.config["models"][self.model_name][source_step_type].get('channels', ["train"]))

        for output_name in output_names:
            temp = ProcessingOutput(
                output_name=output_name,
                source=os.path.join(processing_output_local_filepath, output_name),
                s3_upload_mode="EndOfJob"
            )

            processing_outputs.append(temp)

        return processing_outputs

    def _run_processing_step(
            self,
            network_config: dict,
            args: dict
    ):
        """
        Method to run SageMaker Processing step

        Parameters:
        ----------
        - network_config: dict
            Network configuration
        - args: dict
            Arguments for SageMaker Processing step

        Returns:
        ----------
        - step_process: dict
            SageMaker Processing step
        """

        entrypoint_command = args["entry_point"].replace("/", ".").replace(".py", "")

        framework_processor = FrameworkProcessor(
            image_uri=args["image_uri"],
            framework_version=args["framework_version"],
            estimator_cls=estimator.SKLearn,
            role=args["role"],
            command=["python", "-m", entrypoint_command],
            instance_count=args["instance_count"],
            instance_type=args["instance_type"],
            volume_size_in_gb=args["volume_size_in_gb"],
            max_runtime_in_seconds=args["max_runtime_seconds"],
            base_job_name=args["base_job_name"],
            tags=args["tags"],
            env=args["env"],
            volume_kms_key=args["kms_key"],
            output_kms_key=args["kms_key"],
            network_config=NetworkConfig(**network_config),
            sagemaker_session=self._get_pipeline_session(),
        )

        step_process = framework_processor.run(
            inputs=self._get_processing_inputs(),
            outputs=self._get_processing_outputs(),
            source_dir=args["source_directory"],
            code=args["entry_point"],
            job_name=args["base_job_name"]
        )

        return step_process

    def processing(self) -> dict:
        return self._run_processing_step(
            self._get_network_config(),
            self._args()
        )
