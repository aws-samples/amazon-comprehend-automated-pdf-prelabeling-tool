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
COMPREHEND_ANNOTATIONS_SUBFOLDER = 'comprehend-annotations'
COMPREHEND_OUTPUT_UNZIPPED_FOLDER = "unzipped_files"
COMPREHEND_MANIFEST = 'manifest'

LOGGER.info('Importing custom python modules')
from data_handling_combine import combine_job_outputs


def lambda_handler(event, context):
    
    job_ids = event['output']['comprehend_batch_prediction']['job_ids']
    prelabeling_id = event['output']['create_execution_id']['execution_id']
    comprehend_output_s3_zip = event['output']['comprehend_batch_prediction']['comprehend_output_s3_zip']

    comprehend_output_s3_unzip = 's3://{}/{}/{}/{}/{}/'.format(OUTPUT_BUCKET,PRELABELING_FOLDER,prelabeling_id,COMPREHEND_ANNOTATIONS_SUBFOLDER,COMPREHEND_OUTPUT_UNZIPPED_FOLDER) 
    outputs_manifest_s3_file = 's3://{}/{}/{}/{}/{}/manifest.csv'.format(OUTPUT_BUCKET,PRELABELING_FOLDER,prelabeling_id,COMPREHEND_ANNOTATIONS_SUBFOLDER,COMPREHEND_MANIFEST) 
    LOGGER.info('Combining Comprehend outputs')
    textract_successful_extractions = combine_job_outputs(job_ids,comprehend_output_s3_zip,comprehend_output_s3_unzip,outputs_manifest_s3_file)

    return {
        'statusCode': 200,
        # 'job_ids': json.dumps(textract_successful_extractions),
        'outputs_manifest_s3_file':outputs_manifest_s3_file
    }