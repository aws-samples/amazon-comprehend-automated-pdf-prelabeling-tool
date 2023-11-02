# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json

import boto3


def train_comprehend_custom_entity_recognizer_for_pdfs(
    model_name,
    model_version,
    entities,
    manifest_s3_uri,
    attribute_names,
    s3_prefix_annotations,
    s3_prefix_source_docs,
    IAM_role,
    region,
    test_manifest_s3_uri=None,  ##not supported
    attribute_names_test=None,
    s3_prefix_test_annotations=None,
    s3_prefix_test_source_docs=None,
    lang="en",
    tags=[],
):
    """
    Train a new version or new model for a comprehend custom entity recognition model
    :param model_name: name of the model to train
    :param model_version: version of the model to train
    :param entities: list of entities to train the model on
    :param manifest_s3_uri: s3 uri of the manifest file
    :param attribute_names: list of attribute names to train the model on
    :param s3_prefix_annotations: s3 prefix of the annotations
    :param s3_prefix_source_docs: s3 prefix of the source docs
    :param IAM_role: IAM role to use for the training job
    :param region: region to train the model in
    :param test_manifest_s3_uri: s3 uri of the test manifest file *optional if not set comprehend will use auto split  --- currently no support
    :param s3_prefix_test_annotations: s3 prefix of the test annotations *optional if not set comprehend will use auto split or s3_prefix_annotations --- currently no support
    :param lang: language of the source documents
    :param tags: tags to add to the training job
    :param lang: language of the source docs as of 02/2023 only english is supported
    :return: response: dict output of comprehend
    """
    entity_types = []
    for entity in entities:
        entity_types.append({"Type": entity})

    train_manifest = {
        "S3Uri": manifest_s3_uri,
        "Split": "TRAIN",
        "AttributeNames": attribute_names,
        "AnnotationDataS3Uri": s3_prefix_annotations,
        "SourceDocumentsS3Uri": s3_prefix_source_docs,
        "DocumentType": "SEMI_STRUCTURED_DOCUMENT",
    }
    AugmentedManifests = [train_manifest]
    # add test set if given
    if test_manifest_s3_uri is not None:
        if attribute_names_test is None:
            attribute_names_test = attribute_names
        if s3_prefix_test_source_docs is None:
            s3_prefix_test_source_docs = s3_prefix_source_docs
        if s3_prefix_test_annotations is None:
            s3_prefix_test_annotations = s3_prefix_annotations
        test_manifest = {
            "S3Uri": test_manifest_s3_uri,
            "Split": "TEST",
            "AttributeNames": attribute_names_test,
            "AnnotationDataS3Uri": s3_prefix_test_annotations,
            "SourceDocumentsS3Uri": s3_prefix_test_source_docs,
            "DocumentType": "SEMI_STRUCTURED_DOCUMENT",
        }
        AugmentedManifests.append(test_manifest)
    print(AugmentedManifests)
    InputDataConfig = {
        "DataFormat": "AUGMENTED_MANIFEST",
        "EntityTypes": entity_types,
        "AugmentedManifests": AugmentedManifests,
    }

    client = boto3.client("comprehend", region_name=region)
    response = client.create_entity_recognizer(
        RecognizerName=model_name,
        VersionName=model_version,
        InputDataConfig=InputDataConfig,
        LanguageCode=lang,
        DataAccessRoleArn=IAM_role,
    )
    return response


def get_meta_information_from_manifest(manifest_s3_uri):
    """
    this file uses the first element in the manifest to get the information needed for setting up the comprehend training job
    input:
    manifest_s3_uri: s3 uri of the manifest file
    output:
    job_name: name of the job later to  be used as attribute_name
    pdf_file_prefix: prefix of the source docs
    annotations_file_prefix: prefix of the annotations
    entities: list of entities to train the model on
    """
    # load file from S3
    bucket, key = manifest_s3_uri.replace("s3://", "").split("/", 1)
    session = boto3.Session()
    s3_client = session.client("s3")
    response = s3_client.get_object(Bucket=bucket, Key=key)
    # read file
    file_content = response["Body"].read().decode("utf-8")
    # get first line
    first_line_dict = json.loads(file_content.split("\n")[0])
    # get name of the job
    list_of_keys = list(first_line_dict.keys())
    job_name = list_of_keys[3]
    # get prefix of source docs
    source_ref = first_line_dict["source-ref"]
    pdf_file_prefix = source_ref[: -len(source_ref.split("/")[-1])]

    # get prefix of annotations
    annotations_ref = first_line_dict[job_name]["annotation-ref"]
    annotations_file_prefix = annotations_ref[: -len(annotations_ref.split("/")[-1])]
    # get entities
    entities = first_line_dict["metadata"]["labels"]

    return job_name, pdf_file_prefix, annotations_file_prefix, entities
