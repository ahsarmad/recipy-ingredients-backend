from sqlite3 import Time
from flask import Flask, render_template, jsonify
import time
import numpy as np
import os
import pandas as pd
import json
import pickle
from sklearn.cluster import KMeans
# import sklearn


app = Flask(__name__)

#
# DATA BASE TESTING FUNCTIONS
#
# Migrated here for non requests dependency


def get_ingredients_list(recipe_data):
    ingredients = pd.DataFrame(
        recipe_data.loc[recipe_data["INGREDIENTS"].notna()])
    ingredients["INGREDIENTS_LIST"] = ingredients["INGREDIENTS"].apply(
        lambda x: x.split(','))
    return ingredients

# We also might want other filters such as...


def remove_duplicates(data):
    return data.drop_duplicates(subset=['TITLE'])

# Checks if ingredient is mentioned in ingredients for an indredient list. To be used as an apply function
# where df.apply(lambda x: contains_ingredient(query,x)) queries a dataframe if its ingredient


def contains_ingredient(ingredient, ingredient_list):

    for raw_ingredient in ingredient_list:
        if raw_ingredient.find(ingredient) > 0:
            return True
    return False


def ingredient_filter(query_string, recipe_data):
    queries = query_string.split(',')

    recipe_data = remove_duplicates(recipe_data)
    recipe_data_with_ingredient_list = get_ingredients_list(recipe_data)

    ingredient_filter = recipe_data_with_ingredient_list["INGREDIENTS_LIST"].apply(
        lambda x: contains_ingredient(queries[0], x))
    if len(queries) > 1:
        ingredient_filter = np.logical_and(ingredient_filter, recipe_data_with_ingredient_list["INGREDIENTS_LIST"].apply(
            lambda x: contains_ingredient(queries[1], x)))
    if len(queries) > 2:
        for i in range(len(queries)):
            ingredient_filter = np.logical_and(ingredient_filter, recipe_data_with_ingredient_list["INGREDIENTS_LIST"].apply(
                lambda x: contains_ingredient(queries[i], x)))

    # We can apply this to the original dataframe
    # ingredient_filter(recipe_data_with_ingredient_list[ingredient_filter])

    return ingredient_filter


# Paths to useful directories

path_to_cwd = (os.getcwd())
path_to_ingredient_data = os.path.join(
    path_to_cwd, "Manually Combined Dataset.csv")
path_to_central_recipe_data = os.path.join(
    path_to_cwd, "central_recipe_data.csv")

start_time = time.time()
ingredient_data = pd.read_csv(path_to_ingredient_data, encoding="latin-1")
end_time = time.time()
ingredient_data_access_time = end_time-start_time


#recipe_data = pd.read_csv(path_to_central_recipe_data)
# We use the pickle file to store our data now
start_time = time.time()
path_to_pickle_databases = os.path.join(path_to_cwd, 'pickle_database')
with open(os.path.join(path_to_pickle_databases, 'central_recipe_data.pkl'), 'rb') as file:
    recipe_data = pickle.load(file)
end_time = time.time()
recipe_data_access_time = end_time-start_time


def load_recipe_data():

    # Testing Search Queries
    recipe_data_with_ingredient_list = get_ingredients_list(recipe_data)
    recipe_data = remove_duplicates(recipe_data_with_ingredient_list)
    return recipe_data


def query_recipe_data(recipe_data, query):

    # Testing Search Queries
    recipe_data_with_ingredient_list = get_ingredients_list(recipe_data)

    # We remove duplicates for ease
    recipe_data_with_ingredient_list = remove_duplicates(
        recipe_data_with_ingredient_list)

    # Filter splices queries by commas and searches with np.and
    filter = ingredient_filter(query, recipe_data_with_ingredient_list)

    # We can apply this to the original dataframe to filter it down
    return recipe_data_with_ingredient_list[filter]


def mass_query_recipe_data(recipe_data, query_data):
    # Assume query_data is a list
    data = query_recipe_data(recipe_data, query_data[0])
    for q in range(1, len(query_data)):
        pd.concat([data, query_recipe_data(
            recipe_data, query_data[q])], axis=1)
    return data


def get_recipe_data(recipe_data, recipe_ID):
    recipe_ID = int(recipe_ID)
    return recipe_data.iloc[recipe_ID]


def mass_get_recipe_data(recipe_data, query_data):

    query_list = query_data.split(',')
    query_list = list(map(int, query_list))
    data = recipe_data.iloc[query_list]
    return data

#
#   KMEANS_Reccomendation(query_data,pantry):
#
#       query_data  : comma seperated list of recipes
#       pantry      : comma seperated list of pantry ingredients
#
#       Returns     : A dictionary with reccomendations corresponding to the index.
#                     example: dict[query_data[0]] = {list of recipes recomended based on query_data[0]}


def KMEANS_Reccomendation(query_data, pantry, recipe_data):
    # Note every thing should be in grams
    NUMERICAL_COLS = ['CALORIES', 'FAT', 'CARBS', 'PROTEIN']

    """data =(recipe_data[NUMERICAL_COLS])"""

    # We can make this into a function that works on arbitary samples by replacing sample_data with parameter of favorited users
    # Will need way to select data from database

    query_based_data = mass_get_recipe_data(recipe_data, query_data)
    pantry_based_data = mass_query_recipe_data(recipe_data, pantry)
    sample_data = pd.concat([query_based_data, pantry_based_data])
    # Data we are using to do K means
    #sample_data = sample_data[NUMERICAL_COLS]
    sample_model = KMeans(3, random_state=0).fit(sample_data[NUMERICAL_COLS])
    sample_data['LABEL'] = sample_model.predict(sample_data[NUMERICAL_COLS])

    # For each recipe in the query list containing recipes we want recconmendations in we want to return all other recipes in the same cluster.
    reccomendations = dict()
    for q in query_data.split(','):
        # Look up the cluster of q and set it equal to the value at index q.
        q = int(q)

        reccomendations[q] = (
            sample_data[sample_data['LABEL'] == sample_data.iloc[q]['LABEL']]).to_dict()
        if (len(reccomendations[q]) >= 10):
            reccomendations[q] = (sample_data[sample_data['LABEL'] ==
                                              sample_data.iloc[q]['LABEL']].sample(n=10)).to_dict()
            return reccomendations

# expty commmit for heroku


#   keyword_search(keyword, recipe_data):
#
#       keyword  : some string to look up in the titles and descriptions
#       recipe_data : dataframe all recipe data comes from
#
#       Returns  : A dataframe that contains keyword
#
#
def keyword_search(keyword, recipe_data):
    title_search = (
        recipe_data.loc[recipe_data['TITLE'].str.lower().str.contains(keyword.lower())])
    description_search = (
        recipe_data.loc[recipe_data['DESCRIPTION'].str.lower().str.contains(keyword.lower())])
    result = pd.concat([title_search, description_search])
    result = remove_duplicates(result)
    return result


# Endpoints


#   KMEANS_Reccomendation(query_data,pantry,recipe_data):
#
#       query_data  : comma seperated list of recipes
#       pantry      : comma seperated list of pantry ingredients
#       recipe_data : dataframe all recipe data comes from
#
#       Returns     : A dictionary with reccomendations corresponding to the index.
#                     example: dict[query_data[0]] = {list of recipes recomended based on query_data[0]}
@app.route('/recommend/<string:query_data>/<string:pantry_data>')
def recomend(query_data, pantry_data):
    # query_data=query_data.split(",")
    # pantry_data=pantry_data.split(",")
    data = KMEANS_Reccomendation(query_data, pantry_data, recipe_data)

    return jsonify(data)

#   keyword_search(keyword, recipe_data):
#
#       keyword  : some string to look up in the titles and descriptions
#       recipe_data : dataframe all recipe data comes from
#
#       Returns  : A dataframe that contains keyword
#
#


def keyword_search(keyword, recipe_data):
    title_search = (
        recipe_data.loc[recipe_data['TITLE'].str.lower().str.contains(keyword.lower())])
    description_search = (
        recipe_data.loc[recipe_data['DESCRIPTION'].str.lower().str.contains(keyword.lower())])
    result = pd.concat([title_search, description_search])
    result = remove_duplicates(result)
    return result.dropna()


"""
search_filter(query,filter): queries databse for search but applies filter over that.
@param query: search query to be used
@return: json of search results
"""


@app.route('/search/<string:query>/<string:filter>/<string:black_list>')
def search_filter(query, filter, black_list):
    data = query_recipe_data(recipe_data, query)
    # Assume Blacklist is list of strings seperated by commas
    black_list_filter = ingredient_filter(black_list, data)
    black_list_filter = np.logical_not(black_list_filter)
    known_filters = ["isVegan", "isKeto", "isVegetarian"]
    if filter in known_filters:
        data = data[data[filter] == 1]
    data = data[black_list_filter]

    return jsonify(data.dropna().to_dict())


"""
search(query): preforms webscraping search saving nothing
@param query: search query to be used
@return: json of search results
"""


@app.route('/search/<string:query>')
def search(query):
    data = query_recipe_data(recipe_data, query)
    return jsonify(data.dropna().to_dict())


"""
keyword_search(query): preforms keyword search
@param query: some string to look up in the titles and descriptions
@return: json of search results
"""


@app.route('/key_word_search/<string:keyword>')
def key_word_search(keyword):
    data = keyword_search(keyword, recipe_data)
    return jsonify(data.dropna().to_dict())


"""
load_ingredients(): Gets ingredients from database
@return: json of search results
"""


@app.route('/load_ingredients')
def load_ingredients():
    # Timing Start
    start_time = time.time()
    path = os.getcwd()
    path = os.path.join(path, 'ingredient_data2.json')
    path = open(path)
    #ingredients= pd.read_csv(path,encoding='latin-1')
    ingredients = json.load(path)
    # Timing End
    end_time = time.time()
    print("Time taken to retrieve:")
    print(end_time-start_time)
    return jsonify(ingredients)


@app.route('/')
def index():
    return "Server is running!"


if __name__ == '__main__':
    app.run()


# empty comment to test
# empty comment again
