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
from typing import Tuple

from pipeline.helper import get_chain_input_file, look_up_step_type_from_step_name
from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput
from sagemaker.workflow.pipeline_context import PipelineSession


class TrainingService:
    """
    Class to handle SageMaker Training Service
    """

    def __init__(
            self,
            config: dict,
            model_name: str,
            step_config: dict,
            model_step_dict: dict
    ) -> "TrainingService":

        self.config = config
        self.model_name = model_name
        self.step_config = step_config
        self.domain_section = self.step_config.get("step_type", "train")
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
        - SageMaker Pipeline Session
        """

        return PipelineSession(default_bucket=self.config.get("s3Bucket"))

    def _args(self) -> dict:
        """
        Method to retreive SageMaker training arguments

        Returns:
        ----------
        - SageMaker Training Arguments dictionary
        """

        conf = self.config.get(f"models.{self.model_name}.{self.domain_section}")
        source_dir = self.config.get(
            f"models.{self.model_name}.source_directory",
            os.getenv("SMP_SOURCE_DIR_PATH")
        )

        args = dict(
            image_uri=conf.get("image_uri"),
            base_job_name=conf.get("base_job_name", "default-training-job-name"),
            entry_point=conf.get("entry_point"),
            instance_count=conf.get("instance_count", 1),
            instance_type=conf.get("instance_type", "ml.m5.2xlarge"),
            volume_size_in_gb=conf.get("volume_size_in_gb", 32),
            max_runtime_seconds=conf.get("max_runtime_seconds", 3000),
            tags=conf.get("tags", None),
            env=conf.get("env", None),
            source_directory=source_dir,
            output_path=conf.get("output_path"),
            hyperparams=conf.get("hyperparams", None),
            model_data_uri=conf.get("model_data_uri", None),
            role=self.config.get("sagemakerNetworkSecurity.role"),
            kms_key=self.config.get("sagemakerNetworkSecurity.kms_key", None)
        )

        return args

    def _get_static_input_list(self) -> list:
        """
        Method to retreive SageMaker static inputs

        Returns:
        ----------
        - SageMaker Processing Inputs list
        
        """
        conf = self.config.get(f"models.{self.model_name}.{self.domain_section}")
        # Get the total number of input files
        input_files_list = list()
        for channel in conf.get("channels", {}).keys(): input_files_list.append(
            conf.get(f"channels.{channel}.dataFiles", [])[0])
        return input_files_list

    def _get_static_input(self, channel) -> Tuple[list, int]:
        """
        Method to retreive SageMaker static inputs

        Returns:
        ----------
        - SageMaker Processing Inputs list
        
        """
        # parse main conf dictionary
        conf = self.config.get(f"models.{self.model_name}.{self.domain_section}")
        args = self._args()
        # Get the total number of input files
        input_files_list = self._get_static_input_list()

        training_channel_inputs = {}
        content_type = conf.get("content_type", None)
        input_mode = conf.get("input_mode", "File")
        distribution = conf.get("distribution", "FullyReplicated")

        for file in input_files_list:
            if file.get("fileName").startswith("s3://"):
                _source = file.get("fileName")
            else:
                bucket = conf.get("channels.train.s3Bucket")
                input_prefix = conf.get("channels.train.s3InputPrefix", "")
                _source = os.path.join(bucket, input_prefix, "data", channel, file.get("fileName"))

            training_input = TrainingInput(
                s3_data=_source,
                content_type=content_type,
                input_mode=input_mode,
                distribution=distribution,
            )

            training_channel_inputs[channel] = training_input

        return training_channel_inputs

    def _get_chain_input(self):
        """
        Method to retreive SageMaker chain inputs

        Returns:
        ----------
        - SageMaker Processing Inputs list
        """
        dynamic_training_input = []
        training_channel_inputs = {}
        conf = self.config.get(f"models.{self.model_name}.{self.domain_section}")
        chain_input_source_step = self.step_config.get("chain_input_source_step", [])
        content_type = conf.get("content_type", None)
        input_mode = conf.get("input_mode", "File")
        distribution = conf.get("distribution", "FullyReplicated")

        for source_step_name in chain_input_source_step:
            source_step_type = look_up_step_type_from_step_name(
                source_step_name=source_step_name,
                config=self.config
            )
            training_channel_inputs[source_step_name] = {}
            for channel in self.config["models"][self.model_name][source_step_type].get("channels", ["train"]):
                chain_input_path = get_chain_input_file(
                    source_step_name=source_step_name,
                    steps_dict=self.model_step_dict,
                    source_output_name=channel
                )

                training_input = TrainingInput(
                    s3_data=chain_input_path,
                    content_type=content_type,
                    input_mode=input_mode,
                    distribution=distribution,
                )

                # dynamic_training_input.append(temp)
                # training_channel_inputs[f"{self.model_name}-{source_step_name}"] = training_input
                # training_channel_inputs.update({source_step_name: {channel: training_input}})
                training_channel_inputs[source_step_name][channel] = training_input

        return training_channel_inputs

    def _run_training_step(self, args: dict):
        if "/" in args["entry_point"]:
            train_source_dir = f"{args['source_directory']}/{args['entry_point'].rsplit('/', 1)[0]}"
            train_entry_point = args["entry_point"].rsplit("/", 1)[1]
            train_dependencies = [
                os.path.join(args["source_directory"], f) for f in os.listdir(args["source_directory"])
            ]
        else:
            train_source_dir = args["source_directory"]
            train_entry_point = args["entry_point"]
            train_dependencies = None

        estimator = Estimator(
            role=args["role"],
            image_uri=args["image_uri"],
            instance_count=args["instance_count"],
            instance_type=args["instance_type"],
            volume_size=args["volume_size_in_gb"],
            max_run=args["max_runtime_seconds"],
            output_path=args["output_path"],
            base_job_name=args["base_job_name"],
            hyperparameters=args["hyperparams"],
            tags=args["tags"],
            model_uri=args["model_data_uri"],
            environment=args["env"],
            source_dir=train_source_dir,
            entry_point=train_entry_point,
            dependences=train_dependencies,
            sagemaker_session=self._get_pipeline_session()
        )

        return estimator

    def train_step(self):
        """
        Method to run training step

        Returns:
        ----------
        - SageMaker Estimator object
        
        """

        train_conf = self.config.get(f"models.{self.model_name}.{self.domain_section}")
        args = self._args()
        estimator = self._run_training_step(args)

        training_channel_inputs = {}
        for channel in train_conf.get("channels", "train"):
            temp_inputs = self._get_static_input(channel)
            training_channel_inputs.update(temp_inputs)

        chained_inputs = self._get_chain_input()
        for chain_input in chained_inputs:
            for channel in chained_inputs[chain_input]:
                training_channel_inputs.update({f"{chain_input}-{channel}": chained_inputs[chain_input][channel]})

        train_args = estimator.fit(
            inputs=training_channel_inputs,
            job_name=args["base_job_name"]
        )

        return train_args
