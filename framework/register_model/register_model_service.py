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

from sagemaker.model import ModelPackage
from sagemaker.workflow.execution_variables import ExecutionVariables
from sagemaker.model_metrics import MetricsSource, ModelMetrics
from sagemaker.workflow.steps import ProcessingStep, TrainingStep

from createmodel.create_model_service import CreateModelService


class RegisterModelService:
    def __init__(self, config: dict, model_name: str):
        self.config = config
        self.model_name = model_name

    def register_model(self, step_metrics: ProcessingStep, step_train: TrainingStep) -> ModelPackage:
        create_model_service = CreateModelService(self.config, self.model_name)
        model_package_dict = self.config.get(f"models.{self.model_name}.registry")
        model = create_model_service.create_model(step_train=step_train)

        if step_metrics:
            model_metrics = ModelMetrics(
                model_statistics=MetricsSource(
                    content_type=self.config.get(
                        f"models.{self.model_name}.evaluate.content_type", 
                        "application/json"
                    ),
                    s3_uri="{}{}.json".format(
                        step_metrics.arguments["ProcessingOutputConfig"]["Outputs"][0]["S3Output"]["S3Uri"],
                        step_metrics.arguments["ProcessingOutputConfig"]["Outputs"][0]["OutputName"],
                    ),
                ),
            )
        else:
            model_metrics = None

        inference_spec_dict = model_package_dict.get("InferenceSpecification")

        register_model_step_args = model.register(
            content_types=inference_spec_dict.get("supported_content_types"),
            response_types=inference_spec_dict.get("supported_response_MIME_types"),
            inference_instances=inference_spec_dict.get("SupportedRealtimeInferenceInstanceTypes", ["ml.m5.2xlarge"]),
            transform_instances=inference_spec_dict.get("SupportedTransformInstanceTypes", ["ml.m5.2xlarge"]),
            model_package_group_name=f"{self.config.get('models.projectName')}-{self.model_name}",
            marketplace_cert=False,
            description=model_package_dict.get(
                "ModelPackageDescription",
                "Default Model Package Description. Please add custom descriptioon in your conf.yaml file"
            ),
            customer_metadata_properties={
                "PIPELINE_ARN": ExecutionVariables.PIPELINE_EXECUTION_ARN,
            },
            approval_status=inference_spec_dict.get("approval_status"),
            model_metrics=model_metrics,
        )

        return register_model_step_args
