import json

from pipeline.model_unit import ModelUnit
from sagemaker.workflow.model_step import ModelStep
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.pipeline_context import PipelineSession
from utilities.configuration import Conf


class PipelineService:

    def __init__(self) -> "PipelineService":
        self.config = Conf().load_conf()
        pass

    def _add_step_dependencies(self, pipeline_steps: list) -> None:
        step_dependency_config = self.config.get("sagemakerPipeline.dependencies", [])
        for condition in step_dependency_config:
            temp_chain = condition.split(" >> ")
            for i in range(len(temp_chain) - 1):
                source_step_name = temp_chain[i]
                dest_step_name = temp_chain[i + 1]
                source_step = None
                dest_step = None
                for step in pipeline_steps:
                    step_name = step.name
                    if step_name == source_step_name:
                        source_step = step
                    elif step_name == dest_step_name:
                        dest_step = step
                    if source_step is not None and dest_step is not None:
                        if isinstance(dest_step, ModelStep):
                            dest_step.steps[0].add_depends_on([source_step])
                        else:
                            dest_step.add_depends_on([source_step])
                        break
                if source_step is None or dest_step is None:
                    raise Exception(
                        f"Failed when adding dependency between steps {source_step_name} and {dest_step_name}.")

    def construct_train_pipeline(self):
        model_steps_dict = {}

        for model_name in list(self.config.get("sagemakerPipeline.models").keys()):
            model_steps_dict[model_name] = ModelUnit(
                self.config, model_name, model_steps_dict,
            ).get_train_pipeline_steps()

        pipeline_steps = []
        for model_name, model_unit_steps in model_steps_dict.items():
            pipeline_steps += model_unit_steps

        self._add_step_dependencies(pipeline_steps=pipeline_steps)

        pipeline = Pipeline(
            name=self.config.get("sagemakerPipeline.pipelineName"),
            steps=pipeline_steps,
            sagemaker_session=PipelineSession(),
        )
        pipeline_definition = json.loads(pipeline.definition())

        return pipeline, pipeline_definition

    def execute_pipeline(self) -> None:
        pipeline_role = self.config.get("sagemakerNetworkSecurity.role")
        pipeline, pipeline_definition = self.construct_train_pipeline()

        with open("pipeline_definition.json", "w") as file:
            json.dump(pipeline_definition, file)

        pipeline.upsert(role_arn=pipeline_role)
        pipeline.start()
