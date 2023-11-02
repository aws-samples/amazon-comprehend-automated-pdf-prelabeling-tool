# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import datetime


def get_labels(list_of_entities):
    list_of_labels=[]
    for label in list_of_entities.keys():
        list_of_labels.append(label[:-1]) # remove "s" at the end of the word
    return list_of_labels


def generate_job_metadata_for_auto_labeling_job(job_name):
    time=str(datetime.datetime.today().strftime('%Y-%m-%dT%H:%M:%S'))
    job_metadata={"type":"groundtruth/custom",
               "job-name":job_name,
               "human-annotated":"no",
               "creation-date":time}
    return job_metadata

def transform_GT_manifest_line_to_comprehend(gt_manifest_line,job_name):
    comprehend_line={'source-ref':gt_manifest_line['source-ref'],
                     "page":gt_manifest_line['page']
                    }
    metadata=gt_manifest_line['metadata']
    metadata["labels"]=get_labels(gt_manifest_line["annotator-metadata"])
    comprehend_line["metadata"]=metadata
    comprehend_line[job_name]= {"annotation-ref":gt_manifest_line['primary-annotation-ref']}
    comprehend_line["{}-metadata".format(job_name)] = generate_job_metadata_for_auto_labeling_job(job_name)
    return comprehend_line