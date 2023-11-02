# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import glob
import os
import shutil

import boto3
from helpers.s3_helper import S3Helper

REGION = os.environ.get("AWS_REGION")
session = boto3.Session(region_name=REGION)
sts = session.client("sts")
AWS_ID = sts.get_caller_identity().get("Account")


def separate_manifest_into_folders(
    s3_pdfs,
    job_name,
    s3_comprehend_batches_input,
    max_length=500,
    region=REGION
):
    """
    Splits a manifest file into smaller files to allow the comprehend prediction.
    :param s3_pdfs: list of pdfs files s3 uri
    :param max_length: Maximum number of lines per file.
    :param s3_comprehend_batches_input: s3 path where pdfs will be copied in batches
    :return: list of all manifests
    """

    s3_helper = S3Helper(region=region)

    manifest_split = []

    for i in range(0, len(s3_pdfs), max_length):
        manifest_split.append(s3_pdfs[i : i + max_length])
    data_folders = []

    sub_folder_names_uris = '{}/{}'.format(s3_comprehend_batches_input,job_name)+ "-batch-{}/"

    for i, split in enumerate(manifest_split):
        folder_s3_uri = sub_folder_names_uris.format(i)

        data_folders.append(folder_s3_uri)
        for old_s3_key in split:
            file_name = old_s3_key.split("/")[-1]
            new_s3_key = folder_s3_uri + file_name
            try:
                s3_helper.copy_file(old_s3_key, new_s3_key)
            except Exception as err:
                print('Error with batch {} when trying to copy {} into {}'.format(i,old_s3_key,new_s3_key))
                print(err)
                raise

    return data_folders