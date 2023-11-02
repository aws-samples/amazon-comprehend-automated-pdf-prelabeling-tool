# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging
import os
from datetime import date

import boto3
from file_formatting import get_blocks_for_annotation_file, get_blocks_for_block_file
from helpers.s3_helper import S3Helper
from helpers.text_processing import get_random_string

LOGGER = logging.getLogger("PreLabeling")

REGION = os.environ.get("AWS_REGION")
session = boto3.Session(region_name=REGION)
sts = session.client("sts")
AWS_ID = sts.get_caller_identity().get("Account")
DATA_BUCKET = "comprehend-semi-structured-docs-{}-{}".format(REGION, AWS_ID)
ANNOTATION_BUCKET = "comprehend-semi-structured-docs-{}-{}".format(REGION, AWS_ID)
FOLDER_ANNOTATIONS = "prelabeling/textract-annotations/"


def write_annotation_file(
    blocks,
    all_found_entities,
    blocks_s3Ref,
    file_name,
    doc_metadata={"Pages": 1, "PageNumber": 1},
    # where to store the file
    Bucket=ANNOTATION_BUCKET,
    folder=FOLDER_ANNOTATIONS,
    s3_helper=S3Helper(region=REGION),
):
    final_dict = {
        "Blocks": get_blocks_for_annotation_file(blocks),
        "BlocksS3Ref": blocks_s3Ref,
    }
    final_dict["DocumentMetadata"] = doc_metadata
    final_dict["Version"] = str(date.today())
    final_dict["DocumentType"] = "ScannedPDF"
    final_dict["Entities"] = all_found_entities

    final_dict["File"] = file_name

    s3_uri = s3_helper.s3_uri_from_bucket_folder_file(Bucket, folder, file_name)
    s3_helper.write_json_dict(s3_uri, final_dict)

    return s3_uri


def write_block_file(blocks, file_s3_ui, s3_helper=S3Helper(region=REGION)):
    s3_helper.write_json_dict(file_s3_ui, get_blocks_for_block_file(blocks))


def generate_individual_manifest(
    index_page,
    all_annotation_files,
    all_doc_meta_data,
    expected_entities_annotator_metadata,
    document_s3uri,
):
    LOGGER.info(
        "Generating Manifest file for: {}".format(document_s3uri.split("/")[-1])
    )
    page_meta_data = all_doc_meta_data[index_page]
    page_annotation_file = all_annotation_files[index_page]

    doc_pages = page_meta_data["Pages"]
    page_number = page_meta_data["PageNumber"]
    meta_data = {"pages": str(doc_pages), "use-textract-only": True}
    # prep manifest for labeling job
    labeling_manifest_item = {"source-ref": document_s3uri, "page": str(page_number)}
    labeling_manifest_item["metadata"] = meta_data
    labeling_manifest_item["annotator-metadata"] = expected_entities_annotator_metadata
    labeling_manifest_item["primary-annotation-ref"] = page_annotation_file
    labeling_manifest_item["secondary-annotation-ref"] = None

    return labeling_manifest_item


def save_individual_manifest(
    labeling_manifest_item, bucket, key_path, document_key, index_page, s3_helper
):
    """Saves one temporary manifest file per PDF page"""
    LOGGER.info("Saving Manifest file for: {}".format(document_key.split("/")[-1]))
    manifest_filename = (
        document_key.split("/")[-1][:-4]
        + "_page_{}".format(index_page)
        + "_manifest.manifest"
    )
    manifest_s3_path = "s3://{}/{}/{}".format(bucket, key_path, manifest_filename)
    s3_helper.write_json_dict(manifest_s3_path, labeling_manifest_item)
    return manifest_filename
