# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os
import sys

# Adding src/ and bin/ folders to python path in order to preserve the initial structure of the Annotation Tool
sys.path.append('src')
sys.path.append('bin')

from bin import comprehend_ssie_annotation_tool_cli

REGION = os.environ.get('AWS_REGION')
LOGGER = logging.Logger("Lambda-QueueTextract", level=logging.DEBUG)
HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
LOGGER.addHandler(HANDLER)


def lambda_handler(event, context):

    LOGGER.info(f'Calling Annotation Tool (comprehend_ssie_annotation_tool_cli.py)')

    labeling_job_arn = comprehend_ssie_annotation_tool_cli.main(
        input_manifest_file=event['output']['write_manifest']['uri_final_manifest'],
        cfn_name=os.environ['cfn_name'],
        work_team_name=event['work_team_name'],
        region=REGION,
        entity_types=event['entity_types'],
        job_name_prefix=event['output']['create_execution_id']['execution_id'],
        no_suffix=True
    )

    return {
        'statusCode': 200,
        'body': 'GT Job successfully created.',
        'labeling_job_arn':labeling_job_arn,
    }