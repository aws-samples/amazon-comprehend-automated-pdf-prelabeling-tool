# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import string

from .languages.german import clean_text_de

"""
add specifics for other languages here follow the structure of the german clean_text_de and add the information to the dict of cleaners
"""
# from shared_libraries.string_cleaning.languages.clean_customer_name_fr import clean_customer_name_fr

dict_text_cleaners = {
    "de": clean_text_de,
    # "fr":clean_text_fr
}

def clean_text(text, language="de"):
    text = text.lower()
    cleaned_text = dict_text_cleaners[language](text)
    return cleaned_text
