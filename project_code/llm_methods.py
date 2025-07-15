import pandas as pd
# # THis file should have the LLM methods

#   the purpose of this file is to help user paste their schedule and it will return a pandas dataframe of the calendar version.
#   the function's data frame should follow the format below:
#   'title' | 'description' | 'event_date'
#   this function should use the LLM API to always create dataframes into the columns above
#   the llm can convert to dictionary then pd dataframe.
#   Need to train the LLM so that it can take any schedule type and convert into this format.

# 1.) getting user's response for schedule
# the function should take a string value of user's schedule. It might be easier to read a .txt file of user's response
# user's response will contain information on the class schedule, due dates of assignment, assignment start date, quizzes, finals, tests, ... etc
# this function just only reads user's response, for now it will read a user given txt file and store it as a string in python
# function to store user's response from a user given txt file and converts and stores into string file in python
# this function returns a string.
def store_response(path_to_txt):
    # read the path_to_txt and store it into a variable
    response = str() # this will be the user's response
    # LLM api will read this response data and convert into dictionary format
    # it will extract key informations stated below
    #   'title' | 'description' | 'event_date'
    # the key informations above are keys and it will store a list of values for each key.
    # LLM needs to make sure it extracts correct information in the same order as other keys.
    # read uer's txt file
    # store user's txt file to "response"
    # returns user's response
    # "response" is a dictionary type
    return response
