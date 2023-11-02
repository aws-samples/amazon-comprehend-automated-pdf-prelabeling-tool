# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import time

import boto3
from move_files_batches import separate_manifest_into_folders

REGION = os.environ.get("AWS_REGION")
session = boto3.Session(region_name=REGION)
sts = session.client("sts")
AWS_ID = sts.get_caller_identity().get("Account")


def comprehend_custom_entity_detection_inference_documents(
    s3_pdfs,
    job_name,
    output_s3_comprehend,
    model_ARN,
    IAM_role_ARN,
    s3_comprehend_batches_input,
    VpcConfig=None,
    Tags=None,
    lang="en",
    region=REGION
):
    """
    Function to run inference on a list of documents.
    :param s3_pdfs: list of pdf files
    :param job_name: name of the job
    :param output_s3: S3 URI of output
    :param model_ARN: ARN of the model
    :param IAM_role_ARN: IAM role ARN
    :param s3_comprehend_batches_input: s3 path where pdfs will be copied in batches
    :param VpcConfig: VPC config
    :param Tags: tags
    :param lang: language # as of 02/2023 only english is supported
    :param region: region
    :return:
    list_of_manifests
    list_of_job_ids
    list_of_responses
    """

    # get manifests that are small enough to do an analysis job <500
    print('Saving pdfs in batches of size max 500 in {}'.format(s3_comprehend_batches_input))
    sub_folders = separate_manifest_into_folders(
        s3_pdfs,
        job_name,
        s3_comprehend_batches_input,
        region=region
    )

    responses = []
    job_ids = []
    comprehend = session.client("comprehend", region_name=region)
    counter_batches = 1

    print('Call Comprehend Batch Async Jobs')
    # call comprehend for all sub jobs
    for sub_folder in sub_folders:
        InputDataConfig = {
            "S3Uri": sub_folder,
            "InputFormat": "ONE_DOC_PER_FILE",
            "DocumentReaderConfig": {
                "DocumentReadAction": "TEXTRACT_DETECT_DOCUMENT_TEXT",
                "DocumentReadMode": "FORCE_DOCUMENT_READ_ACTION",
            },
        }
        response = comprehend.start_entities_detection_job(
            InputDataConfig=InputDataConfig,
            OutputDataConfig={
                "S3Uri": output_s3_comprehend,
                # "KmsKeyId":, # recommended to use a KMS Key if using sensitive data 
                },
            DataAccessRoleArn=IAM_role_ARN,
            JobName=job_name + "-batch-{}".format(counter_batches),
            EntityRecognizerArn=model_ARN,
            LanguageCode=lang
        )
        responses.append(response)
        job_ids.append(response["JobId"])
        counter_batches += 1
        print('job_id {} started'.format(job_ids))
        # pause because only 1 job can be submitted per second

        time.sleep(2)

    return sub_folders, job_ids, responses
