# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os
import sys

import boto3
from helpers.s3_helper import S3Helper
from helpers.transform_GT_to_comprehend_format import (
    transform_GT_manifest_line_to_comprehend,
)

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
INDIVIDUAL_MANIFEST_SUBFOLDER = "temp_individual_manifests"

s3 = S3Helper(region=REGION)


def get_all_s3_objects(s3_client, bucket, key, file_format=".manifest"):
    """Get the full list of objects"""
    list_files = []
    continuation_token = None
    while True:
        arg_dict = {"Bucket": bucket, "Prefix": key}
        if continuation_token:
            arg_dict["ContinuationToken"] = continuation_token
        response = s3_client.list_objects_v2(**arg_dict)
        contents = response.get("Contents")
        if contents is None:
            return list_files
        else:
            list_files += [
                obj["Key"] for obj in contents if obj["Key"].endswith(file_format)
            ]
        if not response.get("IsTruncated"):
            return list_files
        continuation_token = response.get("NextContinuationToken")


def lambda_handler(event, context):
    LOGGER.info(f"Starting Consolidation Job of individual manifest files")
    execution_id = event["execution_id"]
    folder_individual_manifest = "s3://{}/{}/{}/{}/".format(
        OUTPUT_BUCKET, PRELABELING_FOLDER, execution_id, INDIVIDUAL_MANIFEST_SUBFOLDER
    )

    bucket, prefix_individual_manifests = s3.bucket_key_from_s3_uri(
        folder_individual_manifest
    )

    s3_client = boto3.client("s3")

    manifest_objs = get_all_s3_objects(
        s3_client, bucket, prefix_individual_manifests, ".manifest"
    )
    LOGGER.info(
        "{} individual manifest files found in s3://{}/{}".format(
            len(manifest_objs), bucket, prefix_individual_manifests
        )
    )

    if manifest_objs == []:
        print("No manifest files found")
        raise

    content_list_gt = []
    content_list_comprehend = []

    for manifest_obj in manifest_objs:
        individual_content = json.loads(
            s3.get_object_content_from_s3("s3://{}/{}".format(bucket, manifest_obj))
        )
        content_list_gt.append(individual_content)
        individual_content_comprehend = transform_GT_manifest_line_to_comprehend(
            individual_content, execution_id
        )
        content_list_comprehend.append(individual_content_comprehend)

    # write manifest for GT labeling job
    consolidated_manifest_s3_path = (
        "s3://{}/{}/{}/{}/consolidated_manifest.manifest".format(
            OUTPUT_BUCKET,
            PRELABELING_FOLDER,
            execution_id,
            CONSOLIDATED_MANIFEST_SUBFOLDER,
        )
    )
    s3.write_jsonl(consolidated_manifest_s3_path, content_list_gt)
    LOGGER.info(
        "Consolidated manifest file written in {}".format(consolidated_manifest_s3_path)
    )

    # write manifest for Comprehend training job
    consolidated_comprehend_manifest_s3_path = (
        "s3://{}/{}/{}/{}/consolidated_manifest_comprehend.manifest".format(
            OUTPUT_BUCKET,
            PRELABELING_FOLDER,
            execution_id,
            CONSOLIDATED_MANIFEST_SUBFOLDER,
        )
    )
    s3.write_jsonl(consolidated_comprehend_manifest_s3_path, content_list_comprehend)
    LOGGER.info(
        "Consolidated manifest file for comprehend training job written in {}".format(
            consolidated_comprehend_manifest_s3_path
        )
    )

    return {
        "statusCode": 200,
        "body": json.dumps("Individual manifests files successfully consolidated."),
        "consolidated_manifest_s3_path": consolidated_manifest_s3_path,
        "consolidated_comprehend_manifest_s3_path": consolidated_comprehend_manifest_s3_path
    }
