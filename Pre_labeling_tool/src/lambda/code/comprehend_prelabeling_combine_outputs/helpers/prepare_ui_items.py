# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

def merge_dictionary_expected_entities(expected_entities_json):
    """Generates a merged dictionary with all expected entities to be displayed in the UI of the GT labeling job under the annotator metadata section
    we will only display one (the first expected_text) for each entity
    also we will merge all entities of the same ype together to one text to decrease the length of the text that needs to be displayed

    """

    list_of_word_per_entity_type = {}

    for expected_entity in expected_entities_json:
        entity_type = expected_entity["entity_type"]
        expected_text = expected_entity["expected_texts"][0]
        if entity_type not in list_of_word_per_entity_type.keys():
            list_of_word_per_entity_type[entity_type] = [expected_text]
        else:
            list_of_word_per_entity_type[entity_type].append(expected_text)

    expected_entities_annotator_metadata = {}
    for entity_type, list_of_words in list_of_word_per_entity_type.items():
        expected_entities_annotator_metadata[entity_type + "s"] = "--".join(
            list_of_words
        )
    return expected_entities_annotator_metadata
