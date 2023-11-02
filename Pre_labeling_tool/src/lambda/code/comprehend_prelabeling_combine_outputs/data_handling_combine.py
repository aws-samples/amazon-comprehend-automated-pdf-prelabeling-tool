# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import glob
import json
import logging
import os
import shutil
import sys

import boto3
import pandas as pd

LOGGER = logging.Logger("PreLabeling", level=logging.DEBUG)
HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
LOGGER.addHandler(HANDLER)

from helpers.file_name_helper import (
    get_file_name,
    get_file_name_without_ending,
    give_annotation_file_name,
    give_textract_file_name,
)
from helpers.s3_helper import S3Helper

REGION = os.environ.get("AWS_REGION")
session = boto3.Session(region_name=REGION)
sts = session.client("sts")
AWS_ID = sts.get_caller_identity().get("Account")

# COMPREHEND_OUTPUT_FOLDER = "zipped_files"


def combine_job_outputs(
    job_id_list,
    comprehend_output_s3_zip,
    comprehend_output_s3_unzip,
    outputs_manifest_s3_file,
    region=REGION,
    user_ID=AWS_ID,
):
    """
    Function to combine the output of multiple jobs into one folder
    :param job_id_list: list of job ids
    :param job_name: name of the jobs
    :param output_s3_prefix: S3 URI of the output prefix same as given in the prediction job
    :param region: region
    :return: list of all the files that where uploaded
    """

    # output_s3_prefix_zip = os.path.join(output_s3_prefix, job_name + "/" + COMPREHEND_OUTPUT_FOLDER)

    print(
        "Unzip Comprehend output files from {} to {}".format(
            comprehend_output_s3_zip, comprehend_output_s3_unzip
        )
    )

    ## UNZIPPING COMPREHEND OUTPUT ###
    # add the folder ending to the prefix
    if comprehend_output_s3_zip[-1] != "/":
        comprehend_output_s3_zip = comprehend_output_s3_zip + "/"
    number_of_uploads = 0
    s3_helper = S3Helper(region=region)
    textract_successful_extractions = []

    col_job_id = []
    col_file_name = []
    col_ann_file_location = []
    col_textract_file_locations = []
    col_status = []
    for job_id in job_id_list:
        LOGGER.info("Job ID: {}".format(job_id))
        tar_s3 = comprehend_output_s3_zip + "{}-NER-{}/output/output.tar.gz".format(
            user_ID, job_id
        )
        temp_output_folder = "/tmp/temp_comp_output/"
        local_name = temp_output_folder + "temp_output.tar.gz"
        extract_path = temp_output_folder + "outputs/"
        try:
            os.makedirs(extract_path)
            print("{} folder created".format(extract_path))
        except Exception as err:
            print("Unexpected {}".format(err))
            raise
        load_bucket, load_key = s3_helper.bucket_key_from_s3_uri(tar_s3)
        LOGGER.debug("Downloading file from {} to {}".format(tar_s3, local_name))
        LOGGER.debug("local_name {}".format(local_name))
        LOGGER.debug("load_key {}".format(load_key))
        s3_helper.download_file(local_name, load_bucket, load_key)
        LOGGER.debug("File successfully downloaded")

        LOGGER.debug("Unzipping file")
        shutil.unpack_archive(local_name, extract_path)
        list_of_files_annotation_files = glob.glob(extract_path + "*")
        list_of_files_annotation_files.remove(extract_path + "output")
        list_of_files_annotation_files.remove(extract_path + "amazon-textract-output")

        for file in list_of_files_annotation_files:
            LOGGER.debug("{}".format(file))
            textract_file_locations = []

            file_name_annotation = get_file_name(file)
            original_file_name = get_file_name_without_ending(
                file_name_annotation
            )  # remove .out

            textract_success = is_textract_success(file)
            if textract_success == True:
                textract_successful_extractions.append(original_file_name)
                status = "success"
            else:
                status = "failure"

            ### RENAMING AND MOVING UNZIPPED FILES TO S3 ###
            new_ann_file_name = give_annotation_file_name(
                comprehend_output_s3_unzip, status, original_file_name
            )
            up_load_bucket, upload_key = s3_helper.bucket_key_from_s3_uri(
                new_ann_file_name
            )
            LOGGER.debug(
                "Uploading Comprehend annotations file from {} to {}".format(
                    file, new_ann_file_name
                )
            )
            s3_helper.upload_file(file, up_load_bucket, upload_key, extra_args=None)
            number_of_uploads += 1
            # move all corresponding textract files to S3
            textract_file_names = glob.glob(
                extract_path + "amazon-textract-output/" + original_file_name + "/*"
            )
            for textract_file in textract_file_names:
                page_number = textract_file.split("/")[-1]
                new_textract_file_name = give_textract_file_name(
                    comprehend_output_s3_unzip, status, original_file_name, page_number
                )
                up_load_bucket, upload_key = s3_helper.bucket_key_from_s3_uri(
                    new_textract_file_name
                )
                LOGGER.debug(
                    "Uploading Textract file from {} to {}".format(
                        textract_file, new_textract_file_name
                    )
                )
                s3_helper.upload_file(
                    textract_file, up_load_bucket, upload_key, extra_args=None
                )
                textract_file_locations.append(new_textract_file_name)

            col_job_id.append(job_id)
            col_file_name.append(original_file_name)
            col_ann_file_location.append(new_ann_file_name)
            col_textract_file_locations.append(textract_file_locations)
            col_status.append(status)
        # remove all the local files
        shutil.rmtree(temp_output_folder)

    outputs_location_mapping = {
        "file_name": col_file_name,
        "job_id": col_job_id,
        "ann_file_location": col_ann_file_location,
        "textract_file_location": col_textract_file_locations,
        "textract_extraction_status": col_status,
    }

    print("Saving outputs manifest csv in {}".format(outputs_manifest_s3_file))
    pd.DataFrame(data=outputs_location_mapping).to_csv(
        outputs_manifest_s3_file, index=False
    )

    return textract_successful_extractions


def is_textract_success(local_file_name):
    # read all the text from the local file and returns False if there was an error when calling textract
    with open(local_file_name, encoding="utf-8") as f:
        ann_content = f.read()

    lines_ann_content = ann_content.split("\n")
    lines_ann_content = [el for el in lines_ann_content if el]  # removes empty line

    textract_success = True
    for line in lines_ann_content:
        try:
            ann_data = json.loads(line)["Entities"]
        except:
            print("Unexpected content for file: {}".format(local_file_name))
            return False

    return textract_success
