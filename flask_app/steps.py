"""
    This file contains explanations to each step in encoding, decoding, etc.
"""

explanations = {}

# step 1: select column type
explanations[0] = "Set data type of each column by selecting using the dropdown button. You may switch between tables by clicking on the names."

# step 2: group String columns
explanations[1] = "Select columns to group for later conducting data desensitization. Choose NO columns if you would like to proceed to the next step. A column can only be in one group. Grouped columns will be marked by index of its group in different colors. You may switch between tables by clicking on the names."

# step 3: adjust encoding level
explanations[2] = "Adjust encoding level by adjusting the slider, 1 encodes column name', 2 encodes string values, 3 and above encodes float values. You may switch between tables by clicking on the names."