# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os
import sys
from datetime import date

import boto3

LOGGER = logging.Logger("PreLabeling", level=logging.DEBUG)
HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
LOGGER.addHandler(HANDLER)

LOGGER.info(f'Import Python custom modules')
from helpers.prepare_ui_items import merge_dictionary_expected_entities
from helpers.s3_helper import S3Helper
from pre_label_tool_kit import generate_annotations_full_file
from store_files import generate_individual_manifest, save_individual_manifest

LOGGER.info(f'Python custom modules successfully imported')

REGION = os.environ.get('AWS_REGION')
session = boto3.Session(region_name=REGION)
sts = session.client('sts')
AWS_ID = sts.get_caller_identity().get('Account')


OUTPUT_BUCKET = 'comprehend-semi-structured-docs-{}-{}'.format(REGION, AWS_ID) # (blocks, annotations & individual manifests)
PRELABELING_FOLDER = 'prelabeling'
ANNOTATIONS_SUBFOLDER = 'textract-annotations'
INDIVIDUAL_MANIFEST_SUBFOLDER = 'temp_individual_manifests'

FUZZYMATCH_LINE_THR=90
FUZZYMATCH_WORD_THR=60

s3=S3Helper(region=REGION)

def lambda_handler(event, context):
    LOGGER.info(f'Starting Run_FuzzyPrelabelingJobs handler execution')

    # Saving the annotations in the core bucket (comprehend-semi-structured-docs)
    output_bucket = OUTPUT_BUCKET

    today = str(date.today())
    jobname = 'auto-preannotation-job' + '-' + today
    
    LOGGER.debug('Reading message attributes')
    document_s3uri = event['premanifest_keys']['pdf']
    expected_entities_s3uri = event['premanifest_keys']['expected_entities']
    prelabeling_id = event['output']['create_execution_id']['execution_id']
    
    LOGGER.info('Filename: {}'.format(document_s3uri.split('/')[-1]))

    objects_to_find = json.loads(s3.get_object_content_from_s3(expected_entities_s3uri))

    # Extract s3 bucket and key for the document
    document_bucket, document_key = s3.bucket_key_from_s3_uri(document_s3uri)

    ann_folder = '{}/{}/{}/'.format(PRELABELING_FOLDER,prelabeling_id,ANNOTATIONS_SUBFOLDER)

    #get all the annotations for the file
    _,all_annotation_files,all_doc_meta_data = generate_annotations_full_file(
                objects_to_find, document_key,
                Data_Bucket=document_bucket,
                region=REGION,
                fuzzymatch_line_thr=FUZZYMATCH_LINE_THR,
                fuzzymatch_word_thr=FUZZYMATCH_WORD_THR,
                ann_Bucket=output_bucket,
                ann_Folder=ann_folder,
                do_entity_consolidation=True,
                double_types=None,
                changefor=None)

    # Create a dictionary with the expected entities to display on the UI
    expected_entities_annotator_metadata = merge_dictionary_expected_entities(objects_to_find)

    #write one line of manifest for each labeld page
    for index_page in range(len(all_annotation_files)):
        LOGGER.info('Page: {}'.format(index_page))
        labeling_manifest_item = generate_individual_manifest(index_page, all_annotation_files, all_doc_meta_data, expected_entities_annotator_metadata, document_s3uri)
        # save individual manifest file to s3
        individual_manifest_key_path = '{}/{}/{}'.format(PRELABELING_FOLDER,prelabeling_id,INDIVIDUAL_MANIFEST_SUBFOLDER)
        manifest_filename = save_individual_manifest(labeling_manifest_item, output_bucket, individual_manifest_key_path, document_key, index_page, s3)
        
        LOGGER.info('Successfully processed {}'.format(manifest_filename))
        
    return {
        'statusCode': 200,
        'body': json.dumps('Pre-Annotation job done.')
    }
