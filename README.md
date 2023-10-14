## dynamic-model-training-with-amazon-sagemaker-pipelines

This pattern allows you to define your training orchestration in a configuration(yaml) file to define/update and start a Sagemaker Pipeline.

How to define a training configuration?
Create a model level root folder in the repo root(ref. lgbm)
Create a conf/conf.yaml. The following breaks down sections of the conf.
the pattern entrypoint picks up all conf.yaml files in model level folders and spins up Sagemaker Pipelines for those.

* _conf_:
    This section contains the two main set of configurations for components of the models being trained(models) and detials of the trainig pipeline(sagemakerPipeline).
    
* _models_:
    Under this section, all ML models will be defined
    * _modelContainer_:
        Under this subsection, one or more machine learning models can be configured. When the pattern Multi-Model is executed the pattern will automatically read all configuration files that exists and on run-time will append all model data configuration into one to pass to the model-unit section to define all steps required. 
        

        # TODO ref to multi-model example.
        # TODO implicit dataFiles chaining. 
         
        # explian chain_input_additional_prefix.

        * {model-name} Subsection: is the model root level definition and under it, the training steps for this model are defined.
            * source_directory: a common source_dir path to use for all tasks
            * name: identifier of the sagemaker model that gets created. Models that run through sagemaker pipelines have job_name identifiers created/overriden by sagemaker. (Optional)
            * Common Parameters
                * image_uri: docker image URI persisted in Amazon Elastic Container Registry
                * entry_point: path to file that serves as entry logic for this job
                * base_job_name: identifier for the step. Jobs that run through sagemaker pipelines have job_name identifiers created/overriden by sagemaker. (Optional)
                * [instance_type](https://aws.amazon.com/sagemaker/pricing/): the compute instance on which to run this job
                * source_dir: source_dir path to bundle up the for the tarball for this step.
                * channels: the list of inputs that are loaded on the container for the job. See job specific details above for conatiner paths and implicit data chaining between steps.
                    * _channelName_
                        * dataFiles
                            * sourceName: an identifier for this file/s
                            * fileName: path(local or s3) of the file to load
            * [{processing}](https://docs.aws.amazon.com/sagemaker/latest/dg/build-and-manage-steps.html#step-type-processing) 
                * [Parameters](https://github.com/aws-samples/dynamic-model-training-with-amazon-sagemaker-pipelines/blob/main/framework/processing/processing_service.py#L101-L117)
                * dataFiles loaded on conatiner at "_/opt/ml/processing/input/{sourceName}/_"
                * Container paths that sagemaker uses to offload content to S3: "_/opt/ml/processing/input/{channelName}/_"
            * [train](https://docs.aws.amazon.com/sagemaker/latest/dg/build-and-manage-steps.html#step-type-training) (Required)
                * [Parameters](https://github.com/aws-samples/dynamic-model-training-with-amazon-sagemaker-pipelines/blob/main/framework/training/training_service.py#L90-L104)
                * dataFiles loaded on conatiner at "_/opt/ml/input/data/{channelName}/_"(also accessible via environment variable "_SM_CHANNEL\_{channelName}_")
                * Container path that sagemaker uses to zip trained model content and upload to S3: "_/opt/ml/model/_"
            * [create](https://docs.aws.amazon.com/sagemaker/latest/dg/build-and-manage-steps.html#step-type-register-model)
                * [Parameters](https://github.com/aws-samples/dynamic-model-training-with-amazon-sagemaker-pipelines/blame/main/framework/createmodel/create_model_service.py#L90-L104)
                * <font size="1"> **NOTE:** CreateModel step is implicit and does not need to be defined here. It can be declared directly in the _sagemakerPipeline_ section.</font>
            * [transform](https://docs.aws.amazon.com/sagemaker/latest/dg/build-and-manage-steps.html#step-type-transform) <font size="1"> **NOTE:** Transform step definition is required with entry_point parameter provided to register or create a model, even if not declared in _sagemakerPipeline_ section. Definiton and declaration is required though for metrics steps.</font>
                * [Parameters](https://github.com/aws-samples/dynamic-model-training-with-amazon-sagemaker-pipelines/blob/main/framework/transform/transform_service.py#L89-L104)
                * [s3BucketName](https://github.com/aws-samples/dynamic-model-training-with-amazon-sagemaker-pipelines/blob/main/framework/transform/transform_service.py#L132): s3 bucket for the results of the batch transform job. Also used to stage local input files pointed in _fileName_
                * [inputBucketPrefix](https://github.com/aws-samples/dynamic-model-training-with-amazon-sagemaker-pipelines/blob/main/framework/transform/transform_service.py#L131): an s3 bucket prefix appended to _s3BucketName_ used for results of the batch transform job. Also used to stage local input files pointed in _fileName_
                * dataFiles loaded on conatiner are managed by the model server(e.x [tensorflow serving](https://sagemaker.readthedocs.io/en/stable/frameworks/tensorflow/deploying_tensorflow_serving.html#)) implemented, serving logic for the machine learning framwork(e.x tensorflow), and [transform workflow](https://docs.aws.amazon.com/sagemaker/latest/dg/batch-transform.html) [guided](https://docs.aws.amazon.com/sagemaker/latest/dg/batch-transform.html#batch-transform-large-datasets) by the parameters used. <font size="1"> **NOTE:** only one channel and in that one dataFile allowed for Transform step </font>
            * [evaluate](https://sagemaker.readthedocs.io/en/stable/amazon_sagemaker_model_building_pipeline.html#property-file): Used by the register step to augment model trained with any details coming out the JSON generated by this step. evaluate step is a processing job with additional parameters.
                * [Parameters](https://github.com/aws-samples/dynamic-model-training-with-amazon-sagemaker-pipelines/blob/main/framework/modelmetrics/model_metrics_service.py#L113)
                * metrics
                    * model_quality
                        * Statistics:
                            * ContentType
                * dataFiles loaded on conatiner at "_/opt/ml/processing/input/{sourceName}/_" <font size="1"> **NOTE:** only one channel and in that one dataFile allowed for Evaluate step. </font>
                * Container paths that sagemaker uses to offload content to S3: "_/opt/ml/processing/input/{channelName}/_"
            * [registry](https://docs.aws.amazon.com/sagemaker/latest/dg/build-and-manage-steps.html#step-type-register-model): register model trained
                * ModelRepack: If "True", uses entry_point in the tranform step to use as inference entry_point when serving the model on sagemaker.
                * [ModelPackageDescription](https://github.com/aws-samples/dynamic-model-training-with-amazon-sagemaker-pipelines/blame/main/framework/createmodel/create_model_service.py#L62)
                * InferenceSpecification
                    * [Parameters](https://github.com/aws-samples/dynamic-model-training-with-amazon-sagemaker-pipelines/blame/main/framework/createmodel/create_model_service.py#L62-L67)

* _sagemakerPipeline_: Name of the Sagemaker Pipeline
    This section define pipeline name, models, model steps and dependencies, let’s breakdown each one. This section is needed at the end of the configuration file for the Singel-Model pattern. For Multi-Model, all models to be trained and/or created/registered should be present in one configuration file.
    * pipelineName: name of the sagemaker pipeline.
    * models : nested list of steps in the sagemaker pipeline to train, and/or create/register this model. 
        * {model}: model identifier in this sagemaker pipeline <font size="1"> **NOTE:** This pattern suggests having one train step, and a pertinent create/metric step if any. If multiple train steps are defined, create/metric/transform/register steps take the last train step to implicitly run the create/metric/transform/register steps. If you must  train multiple models in the same {model} chain, use a train->create->transform->metric->register for each train step.
        # TODO Look at multi-model example for training multiple models.</font>
            * steps:
                * step_name: name of the step displayed in this Sagemaker Pipeline.
                * step_class: (Union[Processing, Training, CreateModel, Transform, Metrics, RegisterModel])
                * enable_cache: (Optional[Union[True, False]]) - whether to enable [Sagemaker Pipeline caching](https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines-caching.html) for this step.
                * step_type: should match {step_name} in _modelContainer_.<font size="1"> **NOTE** This parameter is required for Processing steps. Also required if step names(excluding processing steps) are named other than pertinent keywords - [train, transform, registry, create, metrics]</font>
                * chain_input_source_step: (Optional[list[step_name]]) - to use the channel outputs of a step as input to this step.
                    -{step_name}
                * chain_input_additional_prefix: 
    * dependencies: following airflow notation, the sequence of steps across single DAG or Multi-DAG execution. If dependencies is left blank, explicit dependencies between steps by _chain_input_source_step_ parameter and/or implicit dependencies define the Sagemaker Pipleine DAG.
        - {step_name} >> {step_name}

How to use this pattern for executing Sagemaker Pipelines defined above?
Entrypoint: framework/framework_entrypoint.py
IAM section
AWS config file/IAM identity center



## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-*License. See the LICENSE file.
