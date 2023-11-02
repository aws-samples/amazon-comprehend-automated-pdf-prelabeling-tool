# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os
import sys

import boto3

LOGGER = logging.Logger("PreLabeling", level=logging.INFO)
HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
LOGGER.addHandler(HANDLER)



LOGGER.debug("Importing helpers.file_name_helper")
from helpers.file_name_helper import (
    get_file_name,
    get_file_name_without_ending,
    give_annotation_file_name,
)

LOGGER.debug("Importing helpers.prepare_ui_items")
from helpers.prepare_ui_items import merge_dictionary_expected_entities

LOGGER.debug("Importing store_files")
from store_files import (
    generate_individual_manifest,
    write_annotation_file,
    write_block_file,
)

LOGGER.debug("Importing helpers.s3_helper")
from helpers.s3_helper import S3Helper

REGION = os.environ.get("AWS_REGION")

session = boto3.Session(region_name=REGION)
sts = session.client("sts")
AWS_ID = sts.get_caller_identity().get("Account")
ANNOTATION_BUCKET = "comprehend-semi-structured-docs-{}-{}".format(REGION, AWS_ID)
FOLDER_ANNOTATIONS = "prelabeling/comprehend-annotations/"
MANIFEST_FOLDER = "prelabeling/manifest/"
FOLDER_DATA = "source-semi-structured-documents/"


def create_annotation_manifest_from_comp_inference_manifest(
    pre_labeling_manifest_s3_uri,  # the location of the manifest for this labeling job the labeling job
    ann_manifest_name,  # the name of the manifest you want to create
    df_comprehend_manifest, # manifest file of Comprehend and Textract jobs outputs
    region=REGION,
    ann_Folder=FOLDER_ANNOTATIONS,  # The location of the annotations
    ann_Manifest_folder=MANIFEST_FOLDER,  # the folder of the manifest
    move_source=False,  # by default the source file is not moved
    new_source_Folder=FOLDER_DATA,  # the location of the new source file if it is moved
    source_Bucket=None,  # by default set to the Bucket of the first original source_file
    ann_Bucket=None,  # by default set to the source_bucket
):
    """
    This function creates a manifest of the annotation files that were created by running the
    combine_job_outputs job, after a comprehend batch prediction job.
    the most important inputs are:
        pre_labeling_manifest_s3_uri: the location of the manifest for this labeling job the labeling job
            The manifest must have the following format:
            one file per line
            the lines should have the following keys:
            "pdf" : the s3 key of the file to be annotated
            "expected_entities" : the s3 key of the file that contains the expected text"
        ann_manifest_name: the name of the manifest you want to create
        prefix_comp_files: s3 folder where the annotation files are after running the combine_job_outputs job


    the outputs are:
        the s3_uri of the manifest that was created by running the
    """

    # load the manifest of the prediction job
    s3_helper = S3Helper(region=region)
    LOGGER.debug("Getting premanifest content from {}".format(pre_labeling_manifest_s3_uri))
    manifest_content = s3_helper.get_object_content_from_s3(
        pre_labeling_manifest_s3_uri
    )
    LOGGER.debug("Premanifest content retrieved")
    # lines_manifest_content = manifest_content.split("\n")
    lines_manifest_content = json.loads(manifest_content)
    LOGGER.debug("Premanifest content loaded in JSON format")
    
    # set source_Bucket if it is not set
    if not source_Bucket:
        LOGGER.debug(
            "setting source_Bucket to the Bucket of the first original source_file"
        )
        source_Bucket, _ = s3_helper.bucket_key_from_s3_uri(
            lines_manifest_content[0]["pdf"]
        )
    LOGGER.debug("source_Bucket: {}".format(source_Bucket))

    # set ann_Bucket  if it is not set
    if not ann_Bucket:
        ann_Bucket = source_Bucket
    LOGGER.debug("ann_Bucket: {}".format(ann_Bucket))

    null = None
    all_labeling_manifest_item = []
    
    df_comprehend_manifest.set_index('file_name',inplace=True)
    
    for line in lines_manifest_content:
        try:
            # load the information for this file

            # pre_manifest_dict = json.loads(line)
            source_file_s3 = line["pdf"]
            
            LOGGER.debug('Getting file name for {}'.format(source_file_s3))
            source_file_name = get_file_name(source_file_s3)
            LOGGER.info('{}'.format(source_file_name))
            
            if 'expected_entities' in line:
                LOGGER.debug('Loading expected_entities file {}'.format(line["expected_entities"]))
                objects_to_find = json.loads(
                    s3_helper.get_object_content_from_s3(
                        line["expected_entities"]
                    )
                )
                LOGGER.debug('Expected_entities successfully loaded')
            else:
                objects_to_find = {}
                LOGGER.debug('No expected_entities given')
                
            # load the comprehend output following the naming convention of the combine_job_output
            # source_file_name = get_file_name(source_file_s3)
            #comp_annotation_uri = give_annotation_file_name(output_s3_prefix_comprehend, comprehend_job_name, source_file_name)
            
            if df_comprehend_manifest.loc[source_file_name]['textract_extraction_status']=='failure':
                LOGGER.error('Skipping {} because of error when running Comprehend job'.format(source_file_name))
                pass
                
            else:
                comp_annotation_uri = df_comprehend_manifest.loc[source_file_name]['ann_file_location']
                LOGGER.debug('Generate Labeling annotations for file {}'.format(source_file_name))
                doc_s3_key,all_annotation_files,all_doc_meta_data = generate_labeling_annotations_from_com_output_for_file(
                    source_file_s3,
                    comp_annotation_uri,
                    region=region,
                    ann_Folder=ann_Folder,
                    move_source=move_source,
                    new_source_Folder=new_source_Folder,
                    # by default will be set to the Bucket of the original source_file
                    source_Bucket=source_Bucket,
                    ann_Bucket=ann_Bucket,
                    s3_helper=s3_helper
                )
                LOGGER.debug('Labeling annotations successfully generated')
                # get the expected entities to be displayed in the annotator metadata in the UI
                expected_entities_annotator_metadata = merge_dictionary_expected_entities(objects_to_find)
                LOGGER.debug(expected_entities_annotator_metadata)
                # create the manifest for each page of the document
                for index_page in range(len(all_annotation_files)):
                    LOGGER.info("Page: {}".format(index_page))
                    labeling_manifest_item = generate_individual_manifest(
                        index_page,
                        all_annotation_files,
                        all_doc_meta_data,
                        expected_entities_annotator_metadata,
                        source_file_s3,
                    )

                    all_labeling_manifest_item.append(labeling_manifest_item)

        except Exception as e:
            if line != "":
                LOGGER.error("problems with Order Number:{}".format(line))
                LOGGER.error("{}".format(e))
                
    #  write the manifest to s3 each line is one page.
    manifest_file_uri = s3_helper.s3_uri_from_bucket_folder_file(
        ann_Bucket, ann_Manifest_folder, ann_manifest_name
    )
    LOGGER.info("uploading Manifest to file uri: {}".format(manifest_file_uri))
    s3_helper.write_jsonl(manifest_file_uri, all_labeling_manifest_item)

    return manifest_file_uri


def generate_labeling_annotations_from_com_output_for_file(
    source_file_s3_uri,
    comp_annotation_uri,
    region=REGION,
    ann_Folder=FOLDER_ANNOTATIONS,
    move_source=False,
    new_source_Folder=FOLDER_DATA,
    source_Bucket=None,  # by default will be set to the Bucket of the original source_file
    ann_Bucket=None,  # by default set to be source_Bucket
    s3_helper=None,
):
    """
    This function generates the labeling annotations from the comprehend output for a given file.
    It splits up the file into pages and returns one manifest element per page
    It will also move the source file to the source_Folder if move_source is set to True.
    :param source_file_s3_uri: the location of the source file (the original PDF)
    :param comp_annotation_uri: The location of the comprehend output after it has been cleaned
    :param region:
    :param ann_Folder: # folder where the annotation files are after running the combine_job_outputs job
    :param move_source:  if true the source file will be moved to the new_source_Folder
    :param new_source_Folder: folder where the pdf are copied if move_source==True
    :param source_Bucket: bucket where the pdf are copied if move_source==True
    :param ann_Bucket:

    :return:
    source_file_s3_uri: The new location of the source file is the same if not moved (full PDF with all pages)
    all_annotation_files: List of all the s3_locations of the annotations (one per page)
    all_doc_meta_data: doc metadata for all pages
    """
    LOGGER.debug("Inside generate_labeling_annotations_from_com_output_for_file() function")
    
    LOGGER.debug("S3 Helper instantiate")

    if s3_helper is None:
        s3_helper = S3Helper(region=region)

    if source_Bucket is None:
        source_Bucket, _ = s3_helper.bucket_key_from_s3_uri(source_file_s3_uri)
    if ann_Bucket is None:
        ann_Bucket = source_Bucket

    # get the the names of all annotation files that belong to the same document
    LOGGER.debug("Get name of source file")
    source_file_name = get_file_name(source_file_s3_uri)
    # move the source file if move_source is true
    if move_source:
        LOGGER.debug("Moving files")
        new_source_key = s3_helper.s3_uri_from_bucket_folder_file(
            bucket=source_Bucket, folder=new_source_Folder, file=source_file_name
        )
        s3_helper.copy_object(source_file_s3_uri, new_source_key)
        source_file_s3_uri = new_source_key
    
    LOGGER.debug("Get file name without ending")
    file_name_no_ending = get_file_name_without_ending(source_file_name)
    # comp_annotation_prefix = comp_annotation_uri[:-len(comp_annotation_uri.split('/')[-1])]
    # textract_annotation_s3_uri_format = comp_annotation_prefix + "amazon-textract-output/"+file_name_prefix+"_page_{}.json"

    # load the comprehend output
    LOGGER.debug('Loading the comprehend output')
    ann_content = s3_helper.get_object_content_from_s3(comp_annotation_uri)
    lines_ann_content = ann_content.split("\n")
    all_annotation_files = []
    all_doc_meta_data = []
    for line in lines_ann_content:
        # LOGGER.debug('Line" {}'.format(line))
        try:
            ann_data = json.loads(line)
            doc_metadata = ann_data["DocumentMetadata"]

            page_num = doc_metadata["PageNumber"]
            all_blocks = ann_data["Blocks"]
            # all_found_entities = connect_found_entities(ann_data["Entities"])

            all_found_entities = ann_data["Entities"]
            ann_file = file_name_no_ending + "_page_{}".format(page_num) + "_ann.json"

            # Store the blocks and save to S3
            block_file_key = ann_Folder + "blocks/" + ann_file[:-9] + "_blocks.json"
            block_file_s3_uri = s3_helper.s3_uri_from_bucket_key(
                ann_Bucket, block_file_key
            )
            LOGGER.debug('Store block to s3')
            write_block_file(all_blocks, block_file_s3_uri, s3_helper=s3_helper)

            # store the correct annotation file
            # returns the s3 location of the annotation file for the manifest
            LOGGER.debug('Write Annotation file')
            ann_file_s3 = write_annotation_file(
                all_blocks,
                all_found_entities,
                block_file_s3_uri,
                ann_file,
                doc_metadata=doc_metadata,
                Bucket=ann_Bucket,
                folder=ann_Folder,
                s3_helper=s3_helper,
            )

            all_annotation_files.append(ann_file_s3)
            all_doc_meta_data.append(doc_metadata)
        except Exception as err:
            if line != "":
                print("Error in line {}".format(line))
                print("Unexpected error: {}".format(err))
                raise
    return source_file_s3_uri, all_annotation_files, all_doc_meta_data