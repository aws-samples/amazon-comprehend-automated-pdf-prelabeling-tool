# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os
import sys

import boto3
from helpers.train_comprehend import *

LOGGER = logging.Logger("Lambda-QueueTextract", level=logging.DEBUG)
HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
LOGGER.addHandler(HANDLER)

REGION = os.environ.get("AWS_REGION")
session = boto3.Session(region_name=REGION)
sts = session.client("sts")
AWS_ID = sts.get_caller_identity().get("Account")

OUTPUT_BUCKET = "comprehend-semi-structured-docs-{}-{}".format(REGION, AWS_ID)
PRELABELING_FOLDER = "prelabeling"
CONSOLIDATED_MANIFEST_SUBFOLDER = "consolidated_manifest"


def lambda_handler(event, context):
    LOGGER.info(f"Starting train Comprehend model")
    if "execution_id" in event:
        execution_id = event["execution_id"] #TODO: should be deprecated and removed
    else:
        execution_id = event["output"]["create_execution_id"]["execution_id"]
    comprehend_parameters = event["comprehend_parameters"]

    # load all the parameters for the model
    model_name = comprehend_parameters["model_name"]
    if "model_version" in comprehend_parameters:
        model_version = comprehend_parameters["model_version"]
    else:
        model_version = execution_id
    if "IAM_role" in comprehend_parameters:
        IAM_role_ARN_comprehend = comprehend_parameters["IAM_role"]
    else:
        IAM_role_ARN_comprehend = os.environ["IAM_role_ARN_comprehend"]
    # get the name of the manifest file
    consolidated_comprehend_manifest_s3_path = (
        "s3://{}/{}/{}/{}/consolidated_manifest_comprehend.manifest".format(
            OUTPUT_BUCKET,
            PRELABELING_FOLDER,
            execution_id,
            CONSOLIDATED_MANIFEST_SUBFOLDER,
        )
    )

    LOGGER.debug(
        "created s3_path to comprehend manifest:  {}".format(
            consolidated_comprehend_manifest_s3_path
        )
    )

    # get information about the data for the training job from the manifest file

    (
        job_name,
        pdf_file_prefix,
        annotations_file_prefix,
        entities,
    ) = get_meta_information_from_manifest(consolidated_comprehend_manifest_s3_path)

    LOGGER.info(
        f"loaded all the information for the training job. Ready to start the Comprehend job"
    )
    attribute_names = [job_name]
    response = train_comprehend_custom_entity_recognizer_for_pdfs(
        model_name,
        model_version,
        entities,
        consolidated_comprehend_manifest_s3_path,
        attribute_names,
        annotations_file_prefix,
        pdf_file_prefix,
        IAM_role_ARN_comprehend,
        REGION,
    )

    return {
        "statusCode": 200,
        "body": json.dumps("successfully called the comprehend training job"),
        "response": response,
    }
