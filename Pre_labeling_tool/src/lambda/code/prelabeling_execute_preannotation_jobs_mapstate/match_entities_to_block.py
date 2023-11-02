# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import copy

import numpy as np
from fuzzywuzzy import fuzz
from helpers.string_cleaning.clean_text import clean_text

FUZZYMATCH_LINE_THR = 90
FUZZYMATCH_WORD_THR = 60


def find_text_Item_on_page(
    blocks,
    expected_texts,
    entity_type,
    fuzzymatch_line_thr=FUZZYMATCH_LINE_THR,
    fuzzymatch_word_thr=FUZZYMATCH_WORD_THR,
    ignore_list=[],
    language="de",
):
    found_entities = []
    single_items = (
        []
    )  # Separate the possible text into all words to later find all "WORD" blocks that belong to the entity
    for word in expected_texts:
        for item in word.split():
            single_items.append(item)

    for block in blocks:  # Go though all blocks and check if there is a match
        if block["BlockType"] == "LINE":  # first-find-parent-block --- which is a line
            # first try the fuzzy matching of the words
            if any(
                fuzz.token_set_ratio(
                    clean_text(word, language=language),
                    clean_text(block["Text"], language=language),
                )
                > fuzzymatch_line_thr
                for word in expected_texts
            ):
                entity = {}

                BeginOffset_line = 0

                main_ID = block["Id"]
                total_text = ""
                child_block_part_of_entity = []
                child_blocks = []
                for relatives in block["Relationships"]:
                    if relatives["Type"] == "CHILD":
                        child_blocks = [
                            c_block
                            for c_block in blocks
                            if c_block["Id"] in relatives["Ids"]
                        ]

                (
                    child_block_part_of_entity,
                    total_text,
                    BeginOffset_line,
                ) = check_which_child_blocks_are_in_entity(
                    single_items,
                    child_blocks,
                    fuzzymatch_word_thr=fuzzymatch_word_thr,
                    language=language,
                )

                block_ref = {"BlockId": main_ID}
                block_ref["ChildBlocks"] = child_block_part_of_entity
                entity["BlockReferences"] = [block_ref]
                block_ref["BeginOffset"] = BeginOffset_line

                block_ref["EndOffset"] = int(
                    np.minimum(BeginOffset_line + len(total_text), len(block["Text"]))
                )
                entity["Text"] = total_text
                entity["Type"] = entity_type
                entity["Score"] = 1
                if entity not in found_entities:
                    if entity["Text"] not in ignore_list:
                        found_entities.append(entity)

            """# If you didn't find a matching child block through fuzzy matching check if the text is explicitly in the list of words
            this part is not needed anymore because the fuzzy matching token_set_ratio will cover this
            elif any(
                clean_text(word, language=language)
                in clean_text(block["Text"], language=language)
                for word in expected_texts
            ):
                entity = {}
                BeginOffset_line = 0
                main_ID = block["Id"]

                total_text = ""
                child_block_part_of_entity = []
                child_blocks = []
                for relatives in block["Relationships"]:
                    if relatives["Type"] == "CHILD":
                        child_blocks = [
                            c_block
                            for c_block in blocks
                            if c_block["Id"] in relatives["Ids"]
                        ]

                (
                    child_block_part_of_entity,
                    total_text,
                    BeginOffset_line,
                ) = check_which_child_blocks_are_in_entity(
                    single_items,
                    child_blocks,
                    fuzzymatch_word_thr=fuzzymatch_word_thr,
                    language=language,
                )

                block_ref = {"BlockId": main_ID}
                block_ref["ChildBlocks"] = child_block_part_of_entity
                block_ref["BeginOffset"] = BeginOffset_line
                block_ref["EndOffset"] = int(
                    np.minimum(BeginOffset_line + len(total_text), len(block["Text"]))
                )
                entity["BlockReferences"] = [block_ref]
                entity["Text"] = total_text
                entity["Type"] = entity_type
                entity["Score"] = 1
                if entity not in found_entities:
                    if entity["Text"] not in ignore_list:
                        found_entities.append(entity)
                """
    return found_entities


def check_which_child_blocks_are_in_entity(
    single_items,
    child_blocks,
    fuzzymatch_word_thr=FUZZYMATCH_WORD_THR,
    ignore_list=[],
    language="de",
):
    total_text = ""
    BeginOffset_line = 0
    child_block_part_of_entity = []
    looking_for_start_offset = True
    for c_block in child_blocks:  # Check if the child block belongs to the entity
        # first try the fuzzy matching of the words

        if any(
            [
                fuzz.ratio(
                    clean_text(c_block["Text"], language=language),
                    clean_text(item, language=language),
                )
                > fuzzymatch_word_thr
                for item in single_items
            ]
        ) and (c_block["Text"] not in ignore_list):
            child_block_part_of_entity.append(
                {
                    "BeginOffset": 0,
                    "EndOffset": len(c_block["Text"]),
                    "ChildBlockId": c_block["Id"],
                }
            )
            looking_for_start_offset = False
            if total_text == "":
                total_text = c_block["Text"]
            else:
                total_text = total_text + " " + c_block["Text"]
        elif looking_for_start_offset:
            BeginOffset_line += len(c_block["Text"])
            BeginOffset_line += 1

    if (
        child_block_part_of_entity == []
    ):  # If you didn't find a matching child block through fuzzy matching check if the text is explicitly in the list of words
        BeginOffset_line = 0
        for c_block in child_blocks:
            if any(
                clean_text(word, language=language)
                in clean_text(c_block["Text"], language=language)
                for word in single_items
            ) and (c_block["Text"] not in ignore_list):
                looking_for_start_offset = False
                child_block_part_of_entity.append(
                    {
                        "BeginOffset": 0,
                        "EndOffset": len(c_block["Text"]),
                        "ChildBlockId": c_block["Id"],
                    }
                )
                if total_text == "":
                    total_text = c_block["Text"]
                else:
                    total_text = total_text + " " + c_block["Text"]
            elif looking_for_start_offset:
                BeginOffset_line += len(c_block["Text"])
                BeginOffset_line += 1
    return child_block_part_of_entity, total_text, BeginOffset_line


def consolidate_entities(all_found_entities, double_types=None, changefor=None):
    # this function consolidates the found entities such that entities that together make a new entity get that title
    # first remove all entities that are in ["", " ", "  "]
    strange_entities = [
        copy.copy(entity)
        for entity in all_found_entities
        if entity["Text"] in ["", " ", "  "]
    ]
    for entity in strange_entities:
        all_found_entities.remove(entity)
    all_found_entities_final = copy.deepcopy(all_found_entities)
    # check if there are entities given for the consolidation
    if (double_types is not None) and (changefor is not None):
        if len(double_types) != len(changefor):
            print(
                "the number of pairs given to the consolidation does not match the new types"
            )
            return all_found_entities

        for ii in range(len(double_types)):
            pair = double_types[ii]
            new_type = changefor[ii]
            # Find all entities of the type that might be changed
            ents_t1 = [
                copy.copy(entity)
                for entity in all_found_entities
                if entity["Type"] == pair[0]
            ]
            ents_t2 = [
                copy.copy(entity)
                for entity in all_found_entities
                if entity["Type"] == pair[1]
            ]
            for jj, element in enumerate(ents_t1):
                element["Type"] = new_type
                ents_t1[jj] = element
            for jj, element in enumerate(ents_t2):
                element["Type"] = new_type
                ents_t2[jj] = element
            # check which  entities are in both lists
            double_entities = [entity for entity in ents_t1 if entity in ents_t2]
            # get list of entities to be dropped
            ents_t1_drop = [
                copy.copy(entity) for entity in ents_t1 if entity in double_entities
            ]
            ents_t2_drop = [
                copy.copy(entity) for entity in ents_t2 if entity in double_entities
            ]
            # drop the objects (with old entity_type) from the full list
            for entity in ents_t1_drop:
                entity["Type"] = pair[0]
                all_found_entities_final.remove(entity)
            for entity in ents_t2_drop:
                entity["Type"] = pair[1]
                all_found_entities_final.remove(entity)
            # add the objects with the new entity_type to the list
            all_found_entities_final += double_entities

    return all_found_entities_final
