# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os
import sys

import boto3
import pandas as pd

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
LABELING_ANN_FOLDER = 'labeling-annotation-folder'
MANIFEST_FOLDER = "consolidated_manifest"

LOGGER.info('Importing custom python modules')
from create_manifest_from_comprehend_output import (
    create_annotation_manifest_from_comp_inference_manifest,
)


def lambda_handler(event, context):
    bucket_premanifest = event['premanifest']['bucket']
    key_premanifest = event['premanifest']['key']
    pre_labeling_manifest_s3_uri = 's3://{}/{}'.format(bucket_premanifest,key_premanifest)
    outputs_manifest_s3_file = event['output']['combine_outputs']['outputs_manifest_s3_file']
    
    LOGGER.debug('Reading intermediate manifest file in {}'.format(outputs_manifest_s3_file))
    df_comprehend_manifest = pd.read_csv(outputs_manifest_s3_file)
    LOGGER.debug('Intermediate manifest file successfully read')
    
    prelabeling_id = event['output']['create_execution_id']['execution_id']

    ann_manifest_name = 'final-manifest.manifest'
    ann_Folder = '{}/{}/{}/{}/'.format(PRELABELING_FOLDER,prelabeling_id,COMPREHEND_ANNOTATIONS_SUBFOLDER,LABELING_ANN_FOLDER)
    ann_Manifest_folder = '{}/{}/{}/'.format(PRELABELING_FOLDER,prelabeling_id,MANIFEST_FOLDER)

    LOGGER.debug('Calling create manifest function')
    uri_final_manifest= create_annotation_manifest_from_comp_inference_manifest(
        pre_labeling_manifest_s3_uri,
        ann_manifest_name,
        # output_s3_comprehend,
        # job_name_comprehend,
        df_comprehend_manifest,
        ann_Bucket=OUTPUT_BUCKET,
        ann_Folder=ann_Folder,
        ann_Manifest_folder=ann_Manifest_folder
    )

    return {
        'statusCode': 200,
        'uri_final_manifest': uri_final_manifest
    }