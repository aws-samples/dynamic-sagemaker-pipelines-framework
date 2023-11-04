## Dynamic Amazon Sagemaker Pipelines
In this repo, we present a framework for automating SageMaker Pipelines DAG creation based on simple configuration files. The framework code starts by reading the configuration file(s); and then dynamically creates a SameMaker Pipelines DAG based on the steps declared in the configuration file(s) and the interactions/dependencies among steps. This orchestration framework caters to both single-model and multi-model use cases; and ensures smooth flow of data and processes.

### Architecture Diagram

The following architecture diagram depicts how the proposed framework can be used during both experimentation and operationalization of ML models.

![architecture-diagram](./architecture_diagram.png)

### Repository Structure 

This repo contains the following directories and files: 

- **/framework/conf/**: This directory contains a configuration file that is used to set common variables across all modeling units such as subnets, security groups, and IAM role at the runtime. A modeling unit is a sequence of up to 6 steps for training an ML model 
- **/framework/createmodel/**: This directory contains a Python script that creates a SageMaker Model object based on model artifacts from a Training Step 
- **/framework/modelmetrics/**: This directory contains a Python script that creates a SageMaker Processing job for generating a model metrics JSON report for a trained model 
- **/framework/pipeline/**: This directory contains Python scripts that leverage Python classes defined in other framework directories to create or update a SageMaker Pipelines DAG based on the specified configurations. The model_unit.py script is used by pipeline_service.py to create one or more modeling units. Each modeling unit is a sequence of up to 6 steps for training an ML model: process, train, create model, transform, metrics, and register model. Configurations for each modeling unit should be specified in the model’s respective repository. The pipeline_service.py also sets dependencies among SageMaker Pipelines steps (i.e., how steps within and across modeling units are sequenced and/or chained) based on sagemakerPipeline section which should be defined in the configuration file of one of the model repositories (i.e., the anchor model)
- **/framework/processing/**: This directory contains a Python script that creates a generic SageMaker Processing job 
- **/framework/registermodel/**: This directory contains a Python script for registering a trained model along with its calculated metrics in SageMaker Model Registry 
- **/framework/training/**: This directory contains a Python script that creates a SageMaker Training job 
- **/framework/transform/**: This directory contains a Python script that creates a SageMaker Batch Transform job. In the context of model training, this is used to calculate the performance of a trained model on test data •	/framework/utilities/: This directory contains utility scripts for reading and joining configuration files, as well as logging 
- **/framework_entrypoint.py**: This file is the entry point of the framework code. It simply calls a function defined in the /framework/pipeline/ directory to create or update a SageMaker Pipelines DAG and execute it 
- **/examples/**: This directory contains several examples of how this automation framework can be used to create simple and complex training DAGs 
- **/env.env**: This file allows to set common variables such as subnets, security groups, and IAM role as environment variables 
- **/requirements.txt**: This file specifies Python libraries that are required for the framework code

### Deployment Guide 

Follow the steps below in order to deploy the solution:

1. Organize your model training repository, for example according to the following structure:

    ```
    <MODEL-MAIN-DIR>
    .
    ├── MODEL-DIR
    |   ├── conf
    |   |   └── conf.yaml
    |   └── scripts
    |       ├── preprocess.py
    |       ├── train.py
    |       ├── transform.py
    |       └── evaluate.py
    └── README.md
    ```

1. Clone the framework code and your model(s) source code from the Git repositories:

    a.	Clone `dynamic-model-training-with-amazon-sagemaker-pipelines` repo into a training directory. Here we assume the training directory is called aws-train: 

        ```bash
        git clone https://github.com/aws-samples/dynamic-model-training-with-amazon-sagemaker-pipelines.git aws-train
        ```

    a. Clone the model(s) source code under the same directory. For multi-model training repeat this step for as many models you require to train.

        ```bash
        git clone https:<YOUR-MODEL-REPO>.git aws-train
        ```

        For a single-model training, your directory should look like:

        ```
        <aws-train>  
        .  
        ├── framework
        └── <YOUR-MODEL-DIRECTORY>
        ```

        For multi-model training, your directory should look like:

        ```
        <aws-train>  
        .  
        ├── framework
        └── <YOUR-MODEL-1-DIRECTORY>
        └── <YOUR-MODEL-2-DIRECTORY>
        └── <YOUR-MODEL-3-DIRECTORY>
        ```

1. Set up the following environment variables. Asterisks indicate environment variables which are required, while the rest are optional.  

  
    | Environment Variable | Description |
    | ---------------------| ------------|
    | SMP_ACCOUNTID*        |    AWS Account where SageMaker Pipeline is executed |
    | SMP_REGION*           |    AWS Region where SageMaker Pipeline is executed |
    | SMP_S3BUCKETNAME*     |    Amazon S3 bucket name |
    | SMP_ROLE*             |   Amazon SageMaker execution role |
    | SMP_MODEL_CONFIGPATH* |   Relative path of the of single-model or multi-model configuration file(s) |
    | SMP_SUBNETS          |  Subnet IDs for SageMaker networking configuration |
    | SMP_SECURITYGROUPS   |   Security group IDs for SageMaker networking configuration |

    - Note:
    > For **single-model** use cases: `SMP_MODEL_CONFIGPATH="lgbm/conf/conf.yaml" `

    > For **multi-model**  use cases: `SMP_MODEL_CONFIGPATH="*/conf/conf.yaml"  `

    During experimentation (i.e., local testing), you can specify environment variables inside env.env file; and then export them by executing the following command in your terminal: 
    
    ```bash
    source env.env
    ```
    During operationalization, these environment variables will be set by the CI pipeline.

1. Create and activate a virtual environment:

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

1. Install required python packages: 

    ```bash
    pip install -r requirements.txt
    ```

1. Edit your model training conf.yaml file(s). Please see the Configuration Files Structure section for more details. 

1. From terminal, call framework’s entry point to create or update and execute the SageMaker Pipeline training DAG:

    ```bash
    python framework/framework_entrypoint.py
    ```

1. View and debug the SageMaker Pipelines execution in the Pipelines tab of SageMaker Studio UI.



### Configuration Files Structure

Create a model level root folder in the repo root(ref. lgbm)
Create a conf/conf.yaml. The following breaks down sections of the conf.
  
This pattern entrypoint picks up all conf.yaml files in model level folders and spins up Sagemaker Pipelines for those.

 * **_conf_**:
    This section contains the two main set of configurations for components of the models being trained(models) and details of the training pipeline(sagemakerPipeline).
    
* **_models_**:
    Under this section, all ML models will be defined

    Under this subsection, one or more machine learning models can be configured. When the pattern Multi-Model is executed the pattern will automatically read all configuration files that exists and on run-time will append all model data configuration into one to pass to the model-unit section to define all steps required. 

    * **{model-name}**: subsection is the model root level definition and under it, the training steps for this model are defined.
        * **source_directory**: a common source_dir path to use for all tasks
        * **name**: identifier of the sagemaker model that gets created. Models that run through sagemaker pipelines have job_name identifiers created/overriden by sagemaker. (Optional)

        * **[processing](https://docs.aws.amazon.com/sagemaker/latest/dg/build-and-manage-steps.html#step-type-processing)** (_Optional step_)
            * **[Parameters](https://sagemaker.readthedocs.io/en/stable/workflows/pipelines/sagemaker.workflow.pipelines.html#sagemaker.workflow.steps.ProcessingStep)**

            ```
            preprocess:                        <-- Preprocess Section (Optional)
                image_uri:                     <-- Field Required
                entry_point:                   <-- Field Required
                base_job_name:                 <-- Field OPTIONAL
                instance_count:                <-- Field OPTIONAL, default value: 1
                instance_type:                 <-- Field OPTIONAL, default value: "ml.m5.2xlarge"
                volume_size_in_gb:             <-- Field OPTIONAL, default value: 32
                max_runtime_seconds:           <-- Field OPTIONAL, default value: 3000
                tags:                          <-- Field OPTIONAL, default value: None
                env:                           <-- Field OPTIONAL, default value: None
                framework_version:             <-- Field OPTIONAL, default value: "0"
                s3_data_distribution_type:     <-- Field OPTIONAL, default value: "FullyReplicated"
                s3_data_type:                  <-- Field OPTIONAL, default value: "S3Prefix"
                s3_input_mode:                 <-- Field OPTIONAL, default value: "File"
                s3_upload_mode:                <-- Field OPTIONAL, default value: "EndOfJob"
                channels:
                    train:
                        dataFiles:
                            - sourceName:      <-- Field OPTIONAL
                                fileName:      <-- Field Required
            ```

            * dataFiles loaded on container at "_/opt/ml/processing/input/{sourceName}/_"
            * Container paths that sagemaker uses to offload content to S3: "_/opt/ml/processing/input/{channelName}/_"
              
        * **[train](https://docs.aws.amazon.com/sagemaker/latest/dg/build-and-manage-steps.html#step-type-training)** (Required)
            * **[Parameters](https://sagemaker.readthedocs.io/en/stable/workflows/pipelines/sagemaker.workflow.pipelines.html#sagemaker.workflow.steps.TrainingStep)**

            ```
            train:                            <-- Training Section
                image_uri:                    <-- Field Required 
                entry_point:                  <-- Field Required 
                base_job_name:                <-- Field OPTIONAL
                instance_count:               <-- Field OPTIONAL, default value: 1
                instance_type:                <-- Field OPTIONAL, default value: "ml.m5.2xlarge"
                volume_size_in_gb:            <-- Field OPTIONAL, default value: 32
                max_runtime_seconds:          <-- Field OPTIONAL, default value: 3000
                tags:                         <-- Field OPTIONAL, default value: None
                env:                          <-- Field OPTIONAL, default value: None
                hyperparams:                  <-- Field OPTIONAL, default value: None
                model_data_uri:               <-- Field OPTIONAL, default value: None
                channels:
                    train:                    <-- Train Channel (required)
                        dataFiles:
                            - sourceName:     <-- Field OPTIONAL
                                fileName:     <-- Field OPTIONAL
                    test:                     <-- Test Channel (optional)
                        dataFiles:
                            - sourceName:     <-- Field OPTIONAL
                                fileName:     <-- Field OPTIONAL
            ```

            * dataFiles loaded on container at "_/opt/ml/input/data/{channelName}/_"(also accessible via environment variable "_SM_CHANNEL\_{channelName}_")
            * Container path that sagemaker uses to zip trained model content and upload to S3: "_/opt/ml/model/_"

        * **[create](https://sagemaker.readthedocs.io/en/stable/workflows/pipelines/sagemaker.workflow.pipelines.html#sagemaker.workflow.model_step.ModelStep)**
            * **[Parameters](https://sagemaker.readthedocs.io/en/stable/api/inference/model.html#sagemaker.model.Model)**

            ```
            registry:
                ModelRepack: "False"
                InferenceSpecification: 
                    image_uri:                       <-- Field Required 
                    supported_content_types: 
                        - application/json           <-- Field Required 
                    supported_response_MIME_types: 
                        - application/json           <-- Field Required 
                    approval_status:                 <-- Field Required, 
                                                        - valid values: 
                                                        PendingManualApproval | Rejected | Approved
            ```

            * <font size="1"> **NOTE:** CreateModel step is implicit and does not need to be defined here. It can be declared directly in the _sagemakerPipeline_ section.</font>
              
        * **[transform](https://docs.aws.amazon.com/sagemaker/latest/dg/build-and-manage-steps.html#step-type-transform)** <font size="1">  

            **NOTE:** Transform step definition is required with entry_point parameter provided to register or create a model, even if not declared in _sagemakerPipeline_ section. Definition and declaration is required though for metrics steps.</font>  

            * **[Parameters](https://sagemaker.readthedocs.io/en/stable/workflows/pipelines/sagemaker.workflow.pipelines.html#sagemaker.workflow.steps.TransformStep)**

            ```
            transform:                      <-- Transform Section
                image_uri:                  <-- Field Required 
                base_job_name:              <-- Field OPTIONAL, default value: "default-transform-job-name"
                instance_count:             <-- Field OPTIONAL, default value: 1
                instance_type:              <-- Field OPTIONAL, default value: "ml.m5.2xlarge"
                strategy:                   <-- Field OPTIONAL, default value: None
                assemble_with:              <-- Field OPTIONAL, default value: None
                join_source:                <-- Field OPTIONAL, default value: None
                split_type:                 <-- Field OPTIONAL, default value: None
                content_type:               <-- Field OPTIONAL, default value: "text/csv"
                max_payload:                <-- Field OPTIONAL, default value: None
                volume_size:                <-- Field OPTIONAL, default value: 50
                max_runtime_in_seconds:     <-- Field OPTIONAL, default value: 3600
                input_filter:               <-- Field OPTIONAL, default value: None
                output_filter:              <-- Field OPTIONAL, default value: None
                tags:                       <-- Field OPTIONAL, default value: None
                env:                        <-- Field OPTIONAL, default value: None
                channels:
                    test:
                        s3BucketName: 
                        dataFiles:
                            - sourceName:   <-- Field OPTIONAL
                                fileName:   <-- Field OPTIONAL
            ```
            
            * **[s3BucketName](https://github.com/aws-samples/dynamic-model-training-with-amazon-sagemaker-pipelines/blob/main/framework/transform/transform_service.py#L132)**: s3 bucket for the results of the batch transform job. Also used to stage local input files pointed in _fileName_
            * **[inputBucketPrefix](https://github.com/aws-samples/dynamic-model-training-with-amazon-sagemaker-pipelines/blob/main/framework/transform/transform_service.py#L131)**: an s3 bucket prefix appended to _s3BucketName_ used for results of the batch transform job. Also used to stage local input files pointed in _fileName_
            * dataFiles loaded on container are managed by the model server(e.x [tensorflow serving](https://sagemaker.readthedocs.io/en/stable/frameworks/tensorflow/deploying_tensorflow_serving.html#)) implemented, serving logic for the machine learning framework(e.x tensorflow), and [transform workflow](https://docs.aws.amazon.com/sagemaker/latest/dg/batch-transform.html) [guided](https://docs.aws.amazon.com/sagemaker/latest/dg/batch-transform.html#batch-transform-large-datasets) by the parameters used. <font size="1"> **NOTE:** only one channel and in that one dataFile allowed for Transform step </font>
              
        * **[evaluate](https://sagemaker.readthedocs.io/en/stable/amazon_sagemaker_model_building_pipeline.html#property-file)**: Used by the register step to augment model trained with any details coming out the JSON generated by this step. evaluate step is a processing job with additional parameters.
            * **[Parameters](https://sagemaker.readthedocs.io/en/stable/api/inference/model_monitor.html#sagemaker.model_metrics.ModelMetrics)**

            ```
            evaluate:                          <-- Evaluate Section
                image_uri:                     <-- Field Required 
                entry_point:                   <-- Field Required 
                base_job_name:                 <-- Field OPTIONAL 
                instance_count:                <-- Field OPTIONAL, default value: 1
                instance_type:                 <-- Field OPTIONAL, default value: "ml.m5.2xlarge"
                strategy:                      <-- Field OPTIONAL, default value: "SingleRecord"
                max_payload:                   <-- Field OPTIONAL, default value: None
                volume_size_in_gb:             <-- Field OPTIONAL, default value: 50
                max_runtime_in_seconds:        <-- Field OPTIONAL, default value: 3600
                s3_data_distribution_type:     <-- Field OPTIONAL, default value: "FullyReplicated"
                s3_data_type:                  <-- Field OPTIONAL, default value: "S3Prefix"
                s3_input_mode:                 <-- Field OPTIONAL, default value: "File"
                tags:                          <-- Field OPTIONAL, default value: None
                env:                           <-- Field OPTIONAL, default value: None
                channels:
                    test:
                        s3BucketName:          <-- Field OPTIONAL
                        dataFiles:
                            - sourceName:      <-- Field OPTIONAL
                                fileName:      <-- Field OPTIONAL

            ```
            * **[content_type](https://sagemaker.readthedocs.io/en/stable/api/inference/model_monitor.html#sagemaker.model_metrics.MetricsSource)**: the content type of the output file in evaluate step.    
            * dataFiles loaded on container at "_/opt/ml/processing/input/{sourceName}/_" <font size="1">   
            **NOTE:** only one channel and in that one dataFile allowed for Evaluate step. </font>  
            * Container paths that sagemaker uses to offload content to S3: "_/opt/ml/processing/input/{channelName}/_"
              
        * **[registry](https://docs.aws.amazon.com/sagemaker/latest/dg/build-and-manage-steps.html#step-type-register-model)**: register a model trained in a _train_ step
            * **ModelRepack**: If "True", uses entry_point in the transform step to use as inference entry_point when serving the model on sagemaker.
            * **[ModelPackageDescription](https://sagemaker.readthedocs.io/en/stable/workflows/pipelines/sagemaker.workflow.pipelines.html#sagemaker.workflow.step_collections.RegisterModel)**
            * **InferenceSpecification**
                * [Parameters](https://sagemaker.readthedocs.io/en/stable/workflows/pipelines/sagemaker.workflow.pipelines.html#sagemaker.workflow.step_collections.RegisterModel)
                    

* **_sagemakerPipeline_**: Name of the Sagemaker Pipeline
    This section define pipeline name, models, model steps and dependencies, let’s break each one down. This section is needed at the end of the configuration file for the Single-Model pattern. For Multi-Model, all models to be trained and/or created/registered should be present in one configuration file.
    * **pipelineName**: name of the sagemaker pipeline.
    * **models** : nested list of steps in the sagemaker pipeline to train, and/or create/register this model. 
        * **{model}**: model identifier in this sagemaker pipeline <font size="1"> **NOTE:** This pattern suggests having one train step, and a pertinent create/metric step if any. If multiple train steps are defined, create/metric/transform/register steps take the last train step to implicitly run the create/metric/transform/register steps. If you must train multiple models in the same {model} chain, use a train->create->transform->metric->register for each train step. You can also control this DAG using the _dependencies_ section below.</font>
        
            * **steps**:
                * **step_name**: name of the step displayed in this Sagemaker Pipeline.
                * **step_class**: (Union[Processing, Training, CreateModel, Transform, Metrics, RegisterModel])
                * **enable_cache**: (Optional[Union[True, False]]) - whether to enable [Sagemaker Pipeline caching](https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines-caching.html) for this step.
                * **step_type**: should match {step_name} in _modelContainer_.<font size="1"> **NOTE** This parameter is required for Processing steps. Also required if step names(excluding processing steps) are named other than pertinent keywords - [train, transform, registry, create, metrics]</font>
                * **chain_input_source_step**: (Optional[list[step_name]]) - to use the channel outputs of a step as input to this step.
                    -{step_name}
                * **chain_input_additional_prefix**: (Optional) - only allowed in Transform step types to be specific about content under this S3 prefix under the chain_input_source_step S3 path.
    * **dependencies**: following airflow notation, the sequence of steps across single DAG or Multi-DAG execution. If dependencies is left blank, explicit dependencies between steps by _chain_input_source_step_ parameter and/or implicit dependencies define the Sagemaker Pipeline DAG.
        - {step_name} >> {step_name}


## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-*License. See the LICENSE file.
