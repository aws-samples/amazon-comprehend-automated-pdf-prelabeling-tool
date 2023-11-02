# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import copy


def get_blocks_for_block_file(blocks):
    saved_blocks = []
    for block in blocks:
        local_block = copy.copy(block)
        if local_block["BlockType"] == "LINE":
            local_block["Page"] = 1
            local_block["parentBlockIndex"] = -1
            local_block["blockIndex"] = 0
            saved_blocks.append(local_block)
        elif local_block["BlockType"] == "WORD":
            local_block["Page"] = 1
            local_block["parentBlockIndex"] = 0
            local_block["blockIndex"] = 1
            saved_blocks.append(local_block)

    return saved_blocks


def get_blocks_for_annotation_file(blocks):
    saved_blocks = []
    for block in blocks:
        local_block = copy.copy(block)
        if local_block["BlockType"] == "LINE":
            local_block["Page"] = 1

            saved_blocks.append(local_block)
            child_blocks = []
            for relatives in local_block['Relationships']:
                if relatives["Type"] == 'CHILD':
                    child_blocks = [
                        c_block for c_block in blocks if c_block["Id"] in relatives["Ids"]]
            for child in child_blocks:

                if child["BlockType"] == "WORD":
                    child["Relationships"] = []
                    child["Page"] = 1
                    saved_blocks.append(child)

    return saved_blocks