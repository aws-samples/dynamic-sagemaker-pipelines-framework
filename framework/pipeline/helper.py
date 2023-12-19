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
import re

from sagemaker.workflow import steps
from sagemaker.workflow.functions import Join
from ast import literal_eval


def look_up_step_type_from_step_name(source_step_name: str, config: dict) -> str:
    """
    Look up a step_type in the sagemakerPipeline providing source_step_name and model_name.

    Args:
        source_step_name (str): The name of the step to look up in the sagemakerPipeline.
        model_name (str): The model in sagemaker pipeline
        config (dict): The configuration.


    Returns:
        The step_type.
    """
    # note: chain_input_source_step will error out if source_step does not have an optional step_type declared in
    # sagemakerPipeline section of conf. step_type is mandatory for step_class: Processing.
    for model_name in config['models'].keys():
        steps_dict = config['models'][model_name]
        smp_steps_dict = config['sagemakerPipeline']['models'][model_name]['steps']

        for step in smp_steps_dict:
            if step['step_name'] == source_step_name:
                if step['step_class'] == 'Processing':
                    try:
                        return step['step_type']
                    except KeyError:
                        print(
                            f'When chaining input, source {source_step_name} needs to include step_type, in sagemakerPipeline section of conf'
                        )
                elif step['step_class'] == 'Training':
                    return "train"
                elif step['step_class'] == 'Transform':
                    return "transform"
                else:
                    raise Exception("Only Prcoessing, Training & Transform Step can be used as chain input source.")


def look_up_steps(source_step_name: str, steps_dict: dict) -> steps.Step:
    """
    Look up a step in a dictionary of steps.

    Args:
        source_step_name (str): The name of the step to look up.
        steps_dict (dict): The dictionary of steps.

    Returns:
        The step.
    """
    for model_name, model_steps in steps_dict.items():
        for step in model_steps:
            if step.name == source_step_name:
                return step


def look_up_step_config(source_step_name: str, smp_config: dict) -> dict:
    """
    Look up a step configuration in a dictionary of steps.

    Args:
        source_step_name (str): The name of the step to look up.
        smp_config (dict): The dictionary of steps.

    Returns:
        The step configuration.
    """
    for source_model in smp_config.get("models"):
        for step in smp_config.get(f"models.{source_model}.steps"):
            if step.get("step_name") == source_step_name:
                step_class = step.get("step_class")
                return source_model, step_class


def get_chain_input_file(
        source_step_name: str,
        steps_dict: dict,
        source_output_name: str = "train",
        allowed_step_types: list = ["Processing", "Training", "Transform"],
) -> str:
    """
    Get the input file for a step in a chain.

    Args:
        source_step_name (str): The name of the step to look up.
        steps_dict (dict): The dictionary of steps.
        source_output_name (str): The name of the output to look up.
        allowed_step_types (list): The list of allowed step types.

    Returns:
        The input file.
    """

    source_step = look_up_steps(source_step_name, steps_dict)
    if source_step.step_type.value not in allowed_step_types:
        raise ValueError(
            f"Invalid Source Step Type: {source_step.step_type.value}, Valid source step are {allowed_step_types}"
        )
    if source_step.step_type.value == "Processing":
        chain_input_file = source_step.properties.ProcessingOutputConfig.Outputs[source_output_name].S3Output.S3Uri
    elif source_step.step_type.value == "Training":
        chain_input_file = source_step.properties.ModelArtifacts.S3ModelArtifacts
    elif source_step.step_type.value == "Transform":
        chain_input_file = source_step.properties.TransformOutput.S3OutputPath
    else:
        raise ValueError(
            f"SageMaker model Framework is not supported: {source_step.step_type.value}"
            f"Invalid Source Step Type: {source_step.step_type.value}, Valid source step are {allowed_step_types}"
        )
    return chain_input_file


def get_cache_flag(step_config: dict) -> bool:
    """
    Get the cache flag for a step configuration.

    Args:
        step_config (dict): The step configuration.

    Returns:
        The cache flag.
    """
    if "enable_cache" in step_config.keys():
        cache_flag_content = step_config.get("enable_cache")
        if isinstance(cache_flag_content, bool):
            chache_flag = cache_flag_content
        else:
            raise Exception("Invalid value of step_caching, valid values are True or False")
    else:
        chache_flag = False
    return chache_flag


def generate_default_smp_config(config: dict) -> dict:
    """
    Generate the default SageMaker Model Parallelism configuration.

    Args:
        config (dict): The configuration.

    Returns:
        The SageMaker Model Parallelism configuration.
    """
    model_name = config.get("models.modelName")
    model_abbreviated = model_name.replace("model", "")
    project_name = config.get("project_name")

    try:
        default_pipeline_name = config.get(f"models.{model_name}.sagemakerPipeline.pipelineName")
    except Exception:
        default_pipeline_name = f"{project_name}-{model_abbreviated}-pipeline"

    smp_ = f"""
        {{
            pipelineName: "{default_pipeline_name}",
            models: {{
                {model_name}: {{
                    steps = [
                        {{
                            step_name = {model_abbreviated}-Preprocessing,
                            step_class = preprocessing,
                        }},
                        {{
                            step_name = {model_abbreviated}-Training,
                            step_class = training,
                            chain_input_source_steps = [{model_abbreviated}-Preprocessing],
                        }},
                        {{
                            step_name = {model_abbreviated},
                            step_class = createmodel,
                        }},
                        {{
                            step_name = {model_abbreviated}-Transform,
                            step_class = transform,
                        }},
                        {{
                            step_name = {model_abbreviated}-Metrics, 
                            step_class = metrics,
                        }},
                        {{
                            step_name = {model_abbreviated}-Register,
                            step_class = registermodel,
                        }}
                    ]
                }}
            }},
            dependencies = [
                "{model_abbreviated}-Preprocessing >> {model_abbreviated}-Training >> {model_abbreviated} >> {model_abbreviated}-Transform >> {model_abbreviated}-Metrics >> {model_abbreviated}-Register"
            ]
        }}
    
    """
    smp_config = literal_eval(smp_)
    return smp_config
