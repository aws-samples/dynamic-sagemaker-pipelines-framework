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

# Create individual model units for pipeline

from createmodel.create_model_service import CreateModelService
from modelmetrics.model_metrics_service import ModelMetricsService
from pipeline.helper import get_cache_flag
from processing.processing_service import ProcessingService
from registermodel.register_model_service import RegisterModelService
from sagemaker.workflow.model_step import ModelStep
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.steps import (
    CacheConfig,
    ProcessingStep,
    TrainingStep,
    TransformStep
)
from training.training_service import TrainingService
from transform.transform_service import TransformService


class ModelUnit:
    def __init__(
            self,
            config: dict,
            model_name: str,
            model_step_dict: dict,
    ) -> "ModelUnit":

        self.config = config
        self.model_name = model_name
        self.model_step_dict = model_step_dict.copy()
        self.model_step_dict[self.model_name] = []

    def get_train_pipeline_steps(self) -> list:
        process_step = None
        train_step = None
        create_model_step = None
        transform_step = None
        metrics_step = None
        register_model_step = None
        model_pipeline_steps = []

        step_config_list = self.config.get(f"sagemakerPipeline.models.{self.model_name}.steps")

        for step_config in step_config_list:
            step_class = step_config.get("step_class")
            if step_class == "Processing":
                preprocess_step = self.sagemaker_processing(step_config)
                add_step = preprocess_step
            elif step_class == "Training":
                train_step = self.sagemaker_training(step_config)
                add_step = train_step
            elif step_class == "CreateModel":
                if train_step is None:
                    raise Exception("A training step must be run before a CreateModel step")
                create_model_step = self.sagemaker_create_model(step_config, train_step)
                add_step = create_model_step
            elif step_class == "Transform":
                sagemaker_model_name = create_model_step.properties.ModelName
                transform_step = self.sagemaker_transform(step_config, sagemaker_model_name)
                add_step = transform_step
            elif step_class == "Metrics":
                if transform_step is None:
                    raise Exception("A transform step is required to create a model metrics step.")
                metrics_step = self.sagemaker_model_metrics(step_config)
                add_step = metrics_step
            elif step_class == "RegisterModel":
                if train_step is None:
                    raise Exception("A training step is required to create a register model step.")
                register_model_step = self.sagemaker_register_model(step_config, metrics_step, train_step)
                add_step = register_model_step
            else:
                raise Exception("Invalid step_class value.")

            model_pipeline_steps.append(add_step)
            self.model_step_dict[self.model_name].append(add_step)
        return model_pipeline_steps

    def sagemaker_processing(self, step_config: dict) -> ProcessingStep:
        process_service = ProcessingService(
            self.config,
            self.model_name,
            step_config,
            self.model_step_dict,
        )
        step_args = process_service.processing()
        cache_config = CacheConfig(enable_caching=True, expire_after="10d")
        process_step = ProcessingStep(
            name=step_config.get("step_name"),
            step_args=step_args,
            cache_config=cache_config,
        )
        return process_step

    def sagemaker_training(self, step_config: dict) -> TrainingStep:

        training_service = TrainingService(
            self.config,
            self.model_name,
            step_config,
            self.model_step_dict,
        )

        step_args = training_service.train_step()
        cache_config = CacheConfig(enable_caching=True, expire_after="10d")
        train_step = TrainingStep(
            name=step_config.get("step_name"),
            step_args=step_args,
            cache_config=cache_config,
        )
        return train_step

    def sagemaker_create_model(self, step_config: dict, train_step: TrainingStep) -> ModelStep:

        create_model_service = CreateModelService(
            self.config,
            self.model_name,
        )
        model = create_model_service.create_model(train_step)
        create_model_step = ModelStep(
            name=step_config.get("step_name"),
            step_args=model.create(instance_type="ml.m5.2xlarge")
        )
        return create_model_step

    def sagemaker_transform(self, step_config: dict, sagemaker_model_name: str) -> TransformStep:

        transform_service = TransformService(
            self.config,
            self.model_name,
            step_config,
            self.model_step_dict,
        )

        transform_step_args = transform_service.transform(
            sagemaker_model_name=sagemaker_model_name
        )
        cache_config = CacheConfig(enable_caching=get_cache_flag(step_config), expire_after="10d")
        transform_step = TransformStep(
            name=step_config.get("step_name"),
            step_args=transform_step_args,
            cache_config=cache_config
        )
        return transform_step

    def sagemaker_model_metrics(self, step_config: dict) -> ProcessingStep:

        model_metric_service = ModelMetricsService(self.config, self.model_name, step_config, self.model_step_dict)
        model_metric_args = model_metric_service.calculate_model_metrics()

        cache_config = CacheConfig(enable_caching=get_cache_flag(step_config), expire_after="10d")
        evaluation_report = PropertyFile(
            name="EvaluationReport",
            output_name="model_evaluation_metrics",
            path=f"model_evaluation_metrics.json",
        )
        metrics_step = ProcessingStep(
            name=step_config.get("step_name"),
            step_args=model_metric_args,
            property_files=[evaluation_report],
            cache_config=cache_config,
        )

        return metrics_step

    def sagemaker_register_model(self, step_config: dict, metrics_step: ProcessingStep,
                                 train_step: TrainingStep) -> ModelStep:

        register_model_service = RegisterModelService(self.config, self.model_name)
        register_model_args = register_model_service.register_model(
            metrics_step,
            train_step
        )

        register_model_step = ModelStep(
            name=step_config.get("step_name"),
            step_args=register_model_args
        )

        return register_model_step
