from distutils.log import error
from sqlite3 import Time
from flask import Flask,render_template,jsonify
import time
import numpy as np
import os
import pandas as pd
import json


app = Flask(__name__)

#
# DATA BASE TESTING FUNCTIONS
#
# Migrated here for non requests dependency

def get_ingredients_list(recipe_data):
    ingredients = pd.DataFrame(recipe_data.loc[recipe_data["INGREDIENTS"].notna()])
    ingredients["INGREDIENTS_LIST"] = ingredients["INGREDIENTS"].apply(lambda x: x.split(','))
    return ingredients

# We also might want other filters such as...

def remove_duplicates(data):
    return data.drop_duplicates(subset=['TITLE'])

# Checks if ingredient is mentioned in ingredients for an indredient list. To be used as an apply function
# where df.apply(lambda x: contains_ingredient(query,x)) queries a dataframe if its ingredient 
def contains_ingredient(ingredient, ingredient_list):
    
    for raw_ingredient in ingredient_list:
        if raw_ingredient.find(ingredient)>0:
            return True
    return False

def ingredient_filter(query_string,recipe_data):
    queries = query_string.split(',')
    
    recipe_data = remove_duplicates(recipe_data)
    recipe_data_with_ingredient_list = get_ingredients_list(recipe_data)

    ingredient_filter = recipe_data_with_ingredient_list["INGREDIENTS_LIST"].apply(lambda x: contains_ingredient(queries[0],x))
    if len(queries)>1:
        ingredient_filter = np.logical_and(ingredient_filter,recipe_data_with_ingredient_list["INGREDIENTS_LIST"].apply(lambda x: contains_ingredient(queries[1],x)))
    if len(queries)>2:
        for i in range(len(queries)):
            ingredient_filter = np.logical_and(ingredient_filter,recipe_data_with_ingredient_list["INGREDIENTS_LIST"].apply(lambda x: contains_ingredient(queries[i],x)))
    
    # We can apply this to the original dataframe
    # ingredient_filter(recipe_data_with_ingredient_list[ingredient_filter])

    return ingredient_filter

def NearestNeighbor_Reccomendation():
    # IDEA: Given a list of X data points as favorited recipes we should be able to preform a k nearest neighbor reccomendation
    # (SOURCE) https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.BallTree.html#sklearn.neighbors.BallTree
    return
# Paths to useful directories

path_to_cwd =(os.getcwd())
path_to_datasets= os.path.join(path_to_cwd,"datasets")

path_to_ingredient_data= os.path.join(path_to_datasets,"Manually Combined Dataset.csv")

path_to_server= os.path.join(path_to_cwd,"server")
path_to_recipe_data = os.path.join(path_to_server,"recipe_data")
path_to_central_recipe_data = os.path.join(path_to_recipe_data,"central_recipe_data.csv")

start_time = time.time()
ingredient_data = pd.read_csv(path_to_ingredient_data, encoding="latin-1")
end_time = time.time()
ingredient_data_access_time =end_time-start_time

start_time = time.time()
recipe_data = pd.read_csv(path_to_central_recipe_data)
end_time = time.time()
recipe_data_access_time =end_time-start_time


def load_recipe_data():
    recipe_data = pd.read_csv(path_to_central_recipe_data)
    # Testing Search Queries
    recipe_data_with_ingredient_list =get_ingredients_list(recipe_data)
    recipe_data = remove_duplicates(recipe_data_with_ingredient_list)
    return recipe_data

def query_recipe_data(query):
    recipe_data = pd.read_csv(path_to_central_recipe_data)

    # Testing Search Queries
    recipe_data_with_ingredient_list =get_ingredients_list(recipe_data)

    # We remove duplicates for ease
    recipe_data_with_ingredient_list = remove_duplicates(recipe_data_with_ingredient_list)


    # Filter splices queries by commas and searches with np.and
    filter = ingredient_filter(query,recipe_data_with_ingredient_list)

    # We can apply this to the original dataframe to filter it down
    return recipe_data_with_ingredient_list[filter]


# Endpoints

"""
search(query): preforms webscraping search saving nothing
@param query: search query to be used
@return: json of search results
"""
@app.route('/search/<string:query>')
def search(query):
   data = query_recipe_data(query)
   return jsonify(data.to_dict())

"""
load_ingredients(): Gets ingredients from database
@return: json of search results
"""
@app.route('/load_ingredients')
def load_ingredients():
   # Timing Start
   start_time = time.time()
   path=os.getcwd()
   path=os.path.join(path,'datasets')
   path=os.path.join(path,'ingredient_data2.json')
   path=open(path)
   #ingredients= pd.read_csv(path,encoding='latin-1')
   ingredients= json.load(path)
   # Timing End
   end_time = time.time()
   print("Time taken to retrieve:")
   print(end_time-start_time)
   return jsonify(ingredients)

if __name__ == '__main__':
   app.run()