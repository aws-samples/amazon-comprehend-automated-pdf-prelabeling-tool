# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging
import os
import sys

LOGGER = logging.Logger("Lambda-QueueTextract", level=logging.DEBUG)
HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
LOGGER.addHandler(HANDLER)

REGION = os.environ.get("AWS_REGION")

LOGGER.info('Importing custom python modules')
from check_active_comprehend_jobs import check_comprehend_jobs_finished


def lambda_handler(event, context):

    job_ids = event['output']['comprehend_batch_prediction']['job_ids']
    LOGGER.info('Checking if Comprehend jobs are finished')
    all_done=check_comprehend_jobs_finished(job_ids,REGION)

    return {
        'statusCode': 200,
        'finished':all_done
        # 'job_ids': json.dumps(job_ids)
    }