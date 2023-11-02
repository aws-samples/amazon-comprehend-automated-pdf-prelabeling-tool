# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os
import sys

import boto3

LOGGER = logging.Logger("Lambda-QueueTextract", level=logging.DEBUG)
HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
LOGGER.addHandler(HANDLER)

REGION = os.environ.get('AWS_REGION')
session = boto3.Session(region_name=REGION)
sts = session.client('sts')
AWS_ID = sts.get_caller_identity().get('Account')


OUTPUT_BUCKET = 'comprehend-semi-structured-docs-{}-{}'.format(REGION, AWS_ID)
PRELABELING_FOLDER = 'prelabeling'
COMPREHEND_INPUT_BATCH_FOLDER = 'input-comprehend-pdf-batches'
COMPREHEND_ANNOTATIONS_SUBFOLDER = 'comprehend-annotations'
COMPREHEND_OUTPUT_ZIPPED_FOLDER = "zipped_files"

LOGGER.info('Importing custom python modules')
from comprehend_batch_prediction import (
    comprehend_custom_entity_detection_inference_documents,
)
from helpers.s3_helper import S3Helper as LAMBDAS3Helper
from helpers.text_processing import get_random_string

s3_helper_lambda = LAMBDAS3Helper()

def lambda_handler(event, context):

    LOGGER.info('Reading the manifest from s3')
    #read the manifest from s3 and get all non empty lines 
    bucket_premanifest = event['premanifest']['bucket']
    key_premanifest = event['premanifest']['key']
    pre_labeling_manifest_s3_uri = 's3://{}/{}'.format(bucket_premanifest,key_premanifest)
    manifest = s3_helper_lambda.get_object_content_from_s3(pre_labeling_manifest_s3_uri)
    manifest_lines = json.loads(manifest)
    # manifest_lines = [line for line in manifest.split("\n") if line]

    # get the list of files to predict with comprehend 
    list_of_files=[line["pdf"] for line in manifest_lines]

    prelabeling_id = event['output']['create_execution_id']['execution_id']
    job_name_comprehend = prelabeling_id + '-' + get_random_string(4)

    model_ARN_comprehend = event['model_ARN_comprehend']

    IAM_role_ARN_comprehend = os.environ['IAM_role_ARN_comprehend']

    comprehend_output_s3_zip = 's3://{}/{}/{}/{}/{}/'.format(OUTPUT_BUCKET,PRELABELING_FOLDER,prelabeling_id,COMPREHEND_ANNOTATIONS_SUBFOLDER,COMPREHEND_OUTPUT_ZIPPED_FOLDER) 

    s3_comprehend_batches_input = 's3://{}/{}/{}/{}'.format(OUTPUT_BUCKET,PRELABELING_FOLDER,prelabeling_id,COMPREHEND_INPUT_BATCH_FOLDER)


    sub_folders,job_ids,responses = comprehend_custom_entity_detection_inference_documents(
        list_of_files,
        job_name_comprehend,
        comprehend_output_s3_zip,
        model_ARN_comprehend,
        IAM_role_ARN_comprehend,
        s3_comprehend_batches_input,
        VpcConfig=None,
        Tags=None,
        lang="en",
        region=REGION
    )

    return {
        'statusCode': 200,
        'job_ids': job_ids,
        'comprehend_output_s3_zip':comprehend_output_s3_zip,
        'job_name_comprehend':job_name_comprehend
    }