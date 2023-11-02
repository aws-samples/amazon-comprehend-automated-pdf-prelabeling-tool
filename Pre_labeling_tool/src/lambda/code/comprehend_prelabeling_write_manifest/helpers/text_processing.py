# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import random
import string


def get_random_string(length):
    return "".join(
        random.choice(string.ascii_lowercase + string.digits) for i in range(length)
    )
