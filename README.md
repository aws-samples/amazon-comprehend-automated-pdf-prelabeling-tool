# Semi-Structured Documents Automatic Pre-Labeling Tool

Training a custom entity recognizer on Comprehend for PDF documents requires the user to provide [**Annotation files**](https://docs.aws.amazon.com/comprehend/latest/dg/cer-annotation.html) which map the custom entities to their location in the PDF. The most common way to get these Annotation files, is to use Ground Truth Labeling jobs and let human annotators manually annotate the documents by drawing bounding boxes around the entities that need to be detected. This process of labeling is time consuming and can be expensive for customers.

A more convenient way would consist in being able to use [**Entity lists**](https://docs.aws.amazon.com/comprehend/latest/dg/cer-entity-list.html) to train a Comprehend custom entity recognizer. An Entity list consists in two pieces of information: a list of the entity names (e.g. 'Amazon') with their corresponding custom entity types (e.g. 'Company'), and a collection of unannotated documents in which you expect your entities to appear. However, at the time of the writing, this format is supported for plain text documents but not for the PDF documents.

To tackle this issue, we present a new **Pre-Labeling Tool** that will allow you to generate Annotation files based on Entity lists. User only need to provide Entity lists files and the **Pre-Labeling Tool** will detect the corresponding words on the documents and generate the corresponding Annotation files. Using these automatically generated pre-annotations, the Pre-Labeling Tool can directly train a Comprehend Custom Entity Recognizer and/or create a Ground Truth Labeling Job that human annotators can use to review the generated pre-anotations before training a model.

# Integration with [Comprehend Semi-Structured Documents Annotation Tool](https://github.com/aws-samples/amazon-comprehend-semi-structured-documents-annotation-tools)

This repository is built on top of [Comprehend Semi-Structured Documents Annotation Tool](https://github.com/aws-samples/amazon-comprehend-semi-structured-documents-annotation-tools) and extends its functionalities. The [Comprehend Semi-Structured Documents Annotation Tool](https://github.com/aws-samples/amazon-comprehend-semi-structured-documents-annotation-tools) was designed to create a Ground Truth labeling job where annotators could label custom entities on PDF documents. Once the labeling job was completed, the generated manifest file could be used to train a custom entity recognition model.

Warning: the version of the [Comprehend Semi-Structured Documents Annotation Tool](https://github.com/aws-samples/amazon-comprehend-semi-structured-documents-annotation-tools) used in this repository dates from February 2023 and has not been updated since then. If you don't need the Pre-Labeling Tool but only the resources from the Comprehend Semi-Structured Documents Annotation Tool, it is recommended to deploy the new version from the [original repository](https://github.com/aws-samples/amazon-comprehend-semi-structured-documents-annotation-tools). If you have already deployed a newer version of the Comprehend Semi-Structured Documents Annotation Tool and want to deploy the Pre-Labeling Tool resources on top, please refer to the section *'How to deploy the stack?'* in [Pre_labeling_tool/README.md](Pre_labeling_tool/README.md). 

The original template ```comprehend-semi-structured-documents-annotation-template.yml``` from the [Comprehend Semi-Structured Documents Annotation Tool](https://github.com/aws-samples/amazon-comprehend-semi-structured-documents-annotation-tools) has been integrated into a nested stack defined in ```template.yaml``` which deploys the resources from the ```comprehend-semi-structured-documents-annotation-template.yml``` stack and from the ```Pre_labeling_tool/pre_labeling_tool_template.yaml``` stack. The resources specific to the Pre-Labeling Tool are defined in ```Pre_labeling_tool/pre_labeling_tool_template.yaml```. All files defined in ```Pre_labeling_tool/``` are specific to the Pre-Labeling Tool and are listed and explained in ```Pre_labeling_tool/README.md```.

Please note the following modifications that have been brought to the original [Comprehend Semi-Structured Documents Annotation Tool](https://github.com/aws-samples/amazon-comprehend-semi-structured-documents-annotation-tools) stack:
- ```comprehend-semi-structured-documents-annotation-template.yml```: the ```SemiStructuredDocumentsS3BucketArn``` output was added to the template. Apart from this modification, the template has not been changed
- ```Makefile```: has been changed accordingly to allow the deployment of the new nested stack

# Step 0: Prerequisites
The prerequisites are the same as defined in the original [Comprehend Semi-Structured Documents Annotation Tool](https://github.com/aws-samples/amazon-comprehend-semi-structured-documents-annotation-tools).

* Install python3.8.x (e.g. You can use [pyenv](https://github.com/pyenv/pyenv) for python version management)
  Test your Python installation by running the following command which should display your Python3.8 path:
```
/usr/bin/which python3.8
```
* Install [jq](https://stedolan.github.io/jq/download/)
* Have the latest version of [aws-cli](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html) installed and your AWS credentials configured (https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html).

# How to Build, Package and Deploy

The instructions to build, package and deploy the nested stacks are the same than in the original [Comprehend Semi-Structured Documents Annotation Tool](https://github.com/aws-samples/amazon-comprehend-semi-structured-documents-annotation-tools).

## Option 1 (Recommended):

### Single-Step:
Run the following command to install all dependencies into a virtualenv, build the CloudFormation stack from the template, and deploy the stack to your AWS account with interactive guidance. 
```
make ready-and-deploy-guided
```
## Option 2:

### Step 1: Bootstrap
Run the following command to install [pipenv](https://pypi.org/project/pipenv/), [aws-sam-toolkit](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html), dependencies and setup virtualenv, etc.
```
make bootstrap
```

### Step 2: Enter the shell containing all required dependencies
```
make activate
```

### Step 3: Build
Run the following command to build the CloudFormation template
```
make build
```

### Step 4: Package and Deploy
Run the following command package the CloudFormation template to be ready for CloudFormation deployment, and follow interactive guidance for deployment.
This CloudFormation stack will manage the created lambdas, step machine, IAM roles and S3 bucket.
```
make deploy-guided 
```

Note: 
- Alternatively, you can use run ```make deploy``` if there is already a local samconfig.toml file
- To deploy to different region using different credentials. You can specify *AWS_PROFILE* and *AWS_REGION* option. e.g. ```make deploy-guided AWS_PROFILE=<profile-name> AWS_REGION=<aws-region-name>```
- The CloudFormation allows you to override the following Parameters. To specify the override values, you can run the following command: ```make deploy PRE_HUMAN_LAMBDA_TIMEOUT_IN_SECONDS=600 CONSOLIDATION_LAMBDA_TIMEOUT_IN_SECONDS=600```:
    1. *PRE_HUMAN_LAMBDA_TIMEOUT_IN_SECONDS*: The timeout value for PreHumanLambda to execute. Default to be 300 seconds
    2. *CONSOLIDATION_LAMBDA_TIMEOUT_IN_SECONDS*: The timeout value for Consolidation Lambda to execute. Default to be 300 seconds
    3. *PRE_HUMAN_LAMBDA_MEMORY_IN_MB*: The memory value for PreHumanLambda to execute. Default to be 10240 MB
    4. *CONSOLIDATION_LAMBDA_MEMORY_IN_MB*: The memory value for Consolidation Lambda to execute. Default to be 10240MB
- To update dependencies in the Pipfile, run `make update` and continue to `Step 2: Build`.


# Run Pre-Labeling Tool

Once you have deployed the stack, you can refer to [Pre_labeling_tool/README.md](Pre_labeling_tool/README.md) to see the instructions to test the Pre-Labeling Tool.

# License

All files outside of the `Pre-labeling_tool/` folder and inside the `Pre_labeling_tool/src/lambda/code/prelabeling_create_gt_labeling_job/ui-template/` are licensed under the Apache License. See the `LICENSE` file.

All other files are licensed under the MIT-0 License. See the `Pre_labeling_tool/LICENSE` file.