#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Script used to create a Sagemaker GroundTruth labeling job for semi-structured documents."""

import json
import logging
import datetime
from typing import List
from pathlib import Path
import boto3


from utils.s3_helper import S3Client
from constants import general
from type.groundtruth_annotation_ui_config import GroundTruthAnnotationUIConfig, AnnotationUITaskSchemas, NamedEntitiesAnnotationTaskConfig


logging.basicConfig(level=logging.WARN)
logger = logging.getLogger(__name__)


class InvalidAnnotatorMetadataException(Exception):
    """Raise when invalid annotator metadata is given."""

    def __init__(self, message="Incorrect annotator metadata argument. Cannot parse a valid key/value pair."):
        """Initialize the custom exception."""
        super().__init__(message)


class NoFilesInDirectoryException(Exception):
    """Raise when local directory with files is empty."""

    def __init__(self, message="No semi-structured files have been found in input directory. Please re-enter a S3 path containing semi-structured files."):
        """Initialize the custom exception."""
        super().__init__(message)


def describe_sagemaker_labeling_job(sagemaker_client, job_name: str):
    """Call Sagemaker's describe-labeling-job API on a job."""
    labeling_job_response = sagemaker_client.describe_labeling_job(LabelingJobName=job_name)
    return labeling_job_response


def get_labels_for_prelabeled_job():
    """Get default labels.""" 
    labels = general.DEFAULT_LABELS
    return labels


def generate_schema_for_prelabeled_job(s3_client: S3Client, schema_path, entity_types):
    """Generate schema for a prelabeled job"""
    if schema_path:
        schema_content = s3_client.get_object_content_from_s3(schema_path) if schema_path else None
    else:
        labels = get_labels_for_prelabeled_job() if not entity_types else entity_types
        schema_content = json.dumps(GroundTruthAnnotationUIConfig(
            version="SSIE_NER_SCHEMA_2021-04-15",
            schemas=AnnotationUITaskSchemas(
                named_entity=NamedEntitiesAnnotationTaskConfig(
                    annotation_task="NER",
                    tags=labels,
                    properties=[]
                )
            ),
            exported_time="2s021-04-15T17:34:34.493Z",
            uuid="f44b0438-72ac-43ac-bdc7-5727914522b9"
        ).dict())

    return schema_content


def validate_groundtruth_labeling_job_name(sagemaker_client, job_name_prefix: str, no_suffix: bool):
    """Generate and validate GT labeling job name uniqueness."""
    now = datetime.datetime.utcnow()
    now_str = now.strftime('%Y%m%dT%H%M%S')
    if no_suffix:
        ground_truth_labeling_job_name = job_name_prefix
        try:
            describe_sagemaker_labeling_job(sagemaker_client, ground_truth_labeling_job_name)
            return None
        except Exception:
            pass
    else:
        ground_truth_labeling_job_name = f'{job_name_prefix}-labeling-job-{now_str}'
    return ground_truth_labeling_job_name


def main(
    input_manifest_file: str,
    cfn_name: str,
    work_team_name: str,
    region: str,
    entity_types: list = False, 
    job_name_prefix: str = 'comprehend-semi-structured-docs',
    schema_path: str = None,
    create_input_manifest_only: str = False,
    no_suffix: bool = False,
    task_time_limit: int = 3600,
    task_availability_time_limit: int = 864000,
):
    """Creates GT labeling job

    Args:
        input_manifest_file (str): Input manifest file to use.
        cfn_name (str): CloudFormation stack deployed by comprehend-semi-structured-documents-annotation-template.
        work_team_name (str): Work team name the Ground Truth labeling job will be assigned to.
        region (str): AWS_REGION
        entity_types (list): A list of entity types for annotation.
        job_name_prefix (str): GroundTruth labeling job prefix. (Default: comprehend-semi-structured-docs)
        create_input_manifest_only (str): option to create and upload input manifest only.
        schema_path (str): Local path to schema file to use for the labeling job which will overwrite.
        task_time_limit (int): Time limit in seconds given for each task (default: 3600).
        task_availability_time_limit (int): Time availability time limit in seconds given for each task (default: 864000).
    """


    print('input_manifest_file: {}'.format(input_manifest_file))
    print('cfn_name: {}'.format(cfn_name))
    print('work_team_name: {}'.format(work_team_name))
    print('region: {}'.format(region))
    print('entity_types: {}'.format(entity_types))

    session = boto3.Session(region_name=region)
    sts = session.client('sts')
    cfn = session.client('cloudformation')

    account_id = sts.get_caller_identity().get('Account')
    workteam_arn = f"arn:aws:sagemaker:{region}:{account_id}:workteam/private-crowd/{work_team_name}"

    try:
        output = cfn.describe_stacks(StackName=cfn_name)
        for output in output['Stacks'][0]['Outputs']:
            if output['OutputKey'] == 'SemiStructuredDocumentsS3Bucket':
                ssie_documents_s3_bucket = output['OutputValue']
            if output['OutputKey'] == 'GTAnnotationConsolidationLambdaFunctionName':
                gt_annotation_consolidation_lambda_function = output['OutputValue']
            if output['OutputKey'] == 'GTPreHumanTaskLambdaFunctionName':
                gt_pre_human_task_lambda_function = output['OutputValue']
            if output['OutputKey'] == 'SageMakerRoleARN':
                sagemaker_role_arn = output['OutputValue']
    except Exception as e:
        print(e)
        if not create_input_manifest_only:
            print('Please enter correct cloudformation stack name deployed by comprehend-semi-structured-documents-annotation-template.')
            return
    s3_client = S3Client()
    sagemaker_client = session.client('sagemaker')

    ground_truth_labeling_job_name = validate_groundtruth_labeling_job_name(sagemaker_client=sagemaker_client, job_name_prefix=job_name_prefix, no_suffix=no_suffix)
    if not ground_truth_labeling_job_name:
        print(f'{ground_truth_labeling_job_name} already exists. Please use a different job name.')
        return


    input_manifest_path = input_manifest_file # use manifest file provided by user
    schema_content = generate_schema_for_prelabeled_job(
        s3_client,
        schema_path, 
        entity_types
    )

    if create_input_manifest_only:
        return

    # Upload ui artifacts
    ui_template_s3_path_prefix = f'comprehend-semi-structured-docs-ui-template/{ground_truth_labeling_job_name}'
    local_ui_template_directory_name = 'ui-template'
    s3_client.upload_directory(local_dir_path=local_ui_template_directory_name, bucket_name=ssie_documents_s3_bucket, s3_path_prefix=ui_template_s3_path_prefix)

    # Upload the annotation schema file
    ui_schema_path = f's3://{ssie_documents_s3_bucket}/{ui_template_s3_path_prefix}/{local_ui_template_directory_name}/schema.json'
    print('Uploading schema file.')
    s3_client.write_content(content=schema_content, s3_path=ui_schema_path)

    # Upload the UI template file
    ui_template_path = f's3://{ssie_documents_s3_bucket}/{ui_template_s3_path_prefix}/{local_ui_template_directory_name}/template-2021-04-15.liquid'
    root_path = Path(__file__).resolve().parents[1] # corresponds to prelabeling_create_gt_labeling_job/
    with open(f'{root_path}/{local_ui_template_directory_name}/index.html', encoding='utf-8') as template:
        template_file = template.read().replace('TO_BE_REPLACE', f'{ssie_documents_s3_bucket}/{ui_template_s3_path_prefix}')
        print('Uploading template UI.')
        s3_client.write_content(content=template_file, s3_path=ui_template_path)

    # Start a Sagemaker Groundtruth labeling job
    human_task_config = {
        'WorkteamArn': workteam_arn,
        'UiConfig': {
            'UiTemplateS3Uri': ui_template_path
        },
        'PreHumanTaskLambdaArn': gt_pre_human_task_lambda_function,
        'TaskTitle': ground_truth_labeling_job_name,
        'TaskDescription': ground_truth_labeling_job_name,
        'NumberOfHumanWorkersPerDataObject': 1,
        'TaskTimeLimitInSeconds': task_time_limit,
        'TaskAvailabilityLifetimeInSeconds': task_availability_time_limit,
        'AnnotationConsolidationConfig': {
            'AnnotationConsolidationLambdaArn': gt_annotation_consolidation_lambda_function
        }
    }
    start_labeling_job_request = {'LabelingJobName': f'{ground_truth_labeling_job_name}',
                                  'LabelAttributeName': f'{ground_truth_labeling_job_name}',
                                  'InputConfig': {
                                      'DataSource': {
                                          'S3DataSource': {
                                              'ManifestS3Uri': input_manifest_path
                                          }
                                      }
                                  },
                                  'OutputConfig': {
                                      'S3OutputPath': f's3://{ssie_documents_s3_bucket}/output/'
                                  },
                                  'RoleArn': sagemaker_role_arn,
                                  'StoppingConditions': {
                                      "MaxPercentageOfInputDatasetLabeled": 100
                                  },
                                  'HumanTaskConfig': human_task_config}

    result = sagemaker_client.create_labeling_job(**start_labeling_job_request)
    print("Sagemaker GroundTruth Labeling Job submitted: {}".format(result["LabelingJobArn"]))
    return result["LabelingJobArn"]

if __name__ == "__main__":
    main()
