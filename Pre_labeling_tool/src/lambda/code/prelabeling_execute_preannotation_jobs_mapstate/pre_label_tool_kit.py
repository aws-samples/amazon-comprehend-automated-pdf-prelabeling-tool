# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os
import sys
from datetime import date

import boto3
from helpers.s3_helper import S3Helper
from match_entities_to_block import consolidate_entities, find_text_Item_on_page
from store_files import write_annotation_file, write_block_file
from textractcaller.t_call import (
    call_textract,  # python -m pip install amazon-textract-caller
)

LOGGER = logging.getLogger("PreLabeling")

REGION = os.environ.get('AWS_REGION')
session = boto3.Session(region_name=REGION)
sts = session.client('sts')
AWS_ID = sts.get_caller_identity().get('Account')
DATA_BUCKET = 'comprehend-semi-structured-docs-{}-{}'.format(REGION, AWS_ID)
FOLDER_ANNOTATIONS = "prelabeling/textract-annotations/"
MANIFEST_FOLDER = "prelabeling/manifest/"
FOLDER_DATA = "source-semi-structured-documents/"
INDIVIDUAL_MANIFEST = "prelabeling/temp-individual-manifests"
FUZZYMATCH_LINE_THR=90
FUZZYMATCH_WORD_THR=60
LOGGER.debug('Region: {}'.format(REGION))


'''
objects_to_find::List 
each item is a dict with the following keys:
    expected_texts::array[string] each element is a word that is a possible match for the entity
    *optional
    entity_type::string the type of the entity if not defined, the item will be labeled with entity_type ="UNASSIGNED"
    
    ignore_list::array[string] list of words that should be ignored in the match
'''


def generate_annotations_full_file(objects_to_find,
                                   document_key,
                                   Data_Bucket=DATA_BUCKET,
                                   region=REGION,
                                   save_blocks=True,
                                   fuzzymatch_line_thr=FUZZYMATCH_LINE_THR,
                                   fuzzymatch_word_thr=FUZZYMATCH_WORD_THR,
                                   ann_Bucket=None,
                                   ann_Folder=FOLDER_ANNOTATIONS,
                                   do_entity_consolidation=True, ## gives you the possibility to combine objects that have multiple entities to one consolidated entity. 
                                   # Types that should be consolidated in to one entity
                                   double_types=None, # if given is array(Tuples(string)) e.g [["entity-1","entity-2"],["entity-1","entity-4"]]
                                   # what we exchange the the types for
                                   changefor=None, # if given is array[string]  e.g. ["combo-of-entities-1-2","combo-of-entities-1-4"]
                                   ):
    # load the document
        
    LOGGER.info(f'Generating annotations')
    textract = boto3.client('textract',region_name=region)
    response=call_textract(input_document="s3://{}/{}".format(Data_Bucket,document_key), force_async_api=True, boto3_textract_client=textract)
    blocks = response["Blocks"]
    pages = [block for block in blocks if block["BlockType"] == "PAGE"]
    number_pages=len(pages)
    if ann_Bucket == None:
                ann_Bucket = Data_Bucket
    all_found_entities=[]
    all_annotation_files=[]
    all_doc_meta_data=[]
    for page_num in range(1,number_pages+1):
        document_meta_data={"Pages": str(number_pages), "PageNumber": str(page_num)}
        page_blocks=[block for block in blocks if block["Page"] == page_num]
        # Start the analysis
        page_all_found_entities, page_annotation_file = generate_annotations_single_page(page_blocks,
                                        objects_to_find,
                                        document_key,
                                        ann_Bucket,
                                        document_meta_data=document_meta_data,
                                        save_blocks=save_blocks,
                                        do_entity_consolidation=do_entity_consolidation,
                                        double_types=double_types,
                                        changefor=changefor,
                                        fuzzymatch_line_thr=fuzzymatch_line_thr,
                                        fuzzymatch_word_thr=fuzzymatch_word_thr,
                                        ann_Folder=ann_Folder,
                                        region = region)
        all_found_entities.append(page_all_found_entities)
        all_annotation_files.append(page_annotation_file)
        all_doc_meta_data.append(document_meta_data)
  
    LOGGER.info(f'Successfully generated annotations')
    return all_found_entities, all_annotation_files,all_doc_meta_data





def generate_annotations_single_page(blocks,
                                    objects_to_find,
                                    document_key,
                                    ann_Bucket,
                                    document_meta_data={
                                       "Pages": 1, "PageNumber": 1},
                                   region=REGION,
                                   save_blocks=True,
                                   fuzzymatch_line_thr=FUZZYMATCH_LINE_THR,
                                   fuzzymatch_word_thr=FUZZYMATCH_WORD_THR,
                                   ann_Folder=FOLDER_ANNOTATIONS,
                                   do_entity_consolidation=True, ## gives you the possibility to combine objects that have multiple entities to one consolidated entity. 
                                   # Types that should be consolidated in to one entity
                                   double_types=None, # if given is array(Tuples(string)) e.g [["entity-1","entity-2"],["entity-1","entity-4"]]
                                   # what we exchange the the types for
                                   changefor=None, # if given is array[string]  e.g. ["combo-of-entities-1-2","combo-of-entities-1-4"]
                                   ):

  
    
 
    # Check that the number of pages is 1
    pages = [block for block in blocks if block["BlockType"] == "PAGE"]
    if len(pages) > 1:
        print("More than one page detected")
        print("The limit for this application is 1 page")
        return -1

    # Start the analysis
    all_found_entities = []
    for object in objects_to_find:
        expected_texts = object["expected_texts"]
        if "entity_type" in object:
            entity_type = object["entity_type"]
        else:
            entity_type = "UNASSIGNED"
        if "ignore_list" in object:
            ignore_list = object["ignore_list"]
        else:
            ignore_list = []

        objects_found_local = find_text_Item_on_page(
            blocks, expected_texts, entity_type, ignore_list=ignore_list, fuzzymatch_line_thr=fuzzymatch_line_thr, fuzzymatch_word_thr=fuzzymatch_word_thr)
        # Only add new items to the list of found entities
        for entity_local in objects_found_local:
            if entity_local not in all_found_entities:
                all_found_entities += [entity_local]

    if do_entity_consolidation:
        all_found_entities = consolidate_entities(
            all_found_entities, double_types=double_types, changefor=changefor)

    annotation_file = "didn't save the annotations"
    
    if save_blocks:

        s3_helper=S3Helper(region=region)
        page_number=document_meta_data["PageNumber"]
        #ann_file = document_key.split("/")[-1][:-4]+"-{}-{}".format(page_number,get_random_string(8)) + "-ann.json"
        ann_file = document_key.split("/")[-1][:-4]+"_page_{}".format(page_number) + "_ann.json"

       # Store the blocks and save to S3
        LOGGER.debug(f'Saving Textract blocks to s3')
        block_file_key = ann_Folder+"bocks/" + \
            ann_file[:-9]+ "_blocks.json"
        block_file_s3_uri=s3_helper.s3_uri_from_bucket_key(ann_Bucket,block_file_key)
        write_block_file(blocks,block_file_s3_uri,s3_helper=s3_helper)

        # save the annotations to S3
        LOGGER.debug(f'Saving annotations to s3')
        annotation_file=write_annotation_file(blocks, all_found_entities, block_file_s3_uri, ann_file,
                          doc_metadata=document_meta_data,
                          Bucket=ann_Bucket,
                          folder=ann_Folder,
                          s3_helper = s3_helper)


    return all_found_entities, annotation_file
