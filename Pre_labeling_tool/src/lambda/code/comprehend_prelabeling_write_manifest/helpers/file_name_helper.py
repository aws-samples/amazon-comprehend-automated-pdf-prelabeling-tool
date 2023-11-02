# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

def get_file_name(path: str):
    """
    Function to get the file name from a path
    :param path: path
    :return: file name
    """
    return path.split("/")[-1]


def get_file_name_without_ending(file_name):
    """
    Function to get the file name without the document type
    :param file_name: file name
    :return: file name without document type
    """
    return file_name[: -len(file_name.split(".")[-1]) - 1]


def give_textract_file_name(output_s3_prefix, job_name, file_name, page_number):
    file_name_prefix = get_file_name_without_ending(file_name)
    if output_s3_prefix[-1] == "/":
        return (
            output_s3_prefix
            + job_name
            + "/amazon-textract-output/"
            + file_name_prefix
            + "_page_"
            + page_number
            + ".json"
        )
    else:
        return (
            output_s3_prefix
            + "/"
            + job_name
            + "/amazon-textract-output/"
            + file_name_prefix
            + "_page_"
            + page_number
            + ".json"
        )


def give_annotation_file_name(output_s3_prefix, job_name, file_name):
    file_name_prefix = get_file_name_without_ending(file_name)
    if output_s3_prefix[-1] == "/":
        return output_s3_prefix + job_name + "/" + file_name_prefix + "_comp_ann.json"
    else:
        return output_s3_prefix + "/" + job_name + "/" + file_name_prefix + "_comp_ann.json"
