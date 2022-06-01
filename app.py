from fastapi import FastAPI
from pydantic import BaseModel
from pydantic import parse_obj_as

import math
import pandas as pd
#import numpy as np
#import matplotlib.pyplot as plt
import requests
from typing import List

urlGraphqlApi    = 'http://34.125.0.249/graphql/'

class Input(BaseModel):
    title: str
    rating: float

class InputList(BaseModel):
    __root__: List[Input]




app = FastAPI()

@app.get("/")
def read_root(input: InputList):

    queryMovies = {'query' : '{ movies { movieId title genres} }' }
    movies = requests.post(url=urlGraphqlApi, json=queryMovies)
    movies_obj = eval(movies.text)
    movies_json = movies_obj["data"]["movies"]
    movies_df = pd.json_normalize(movies_json)

    queryRatings = {'query' : '{   ratings { movieId userId rating } }' }
    ratings = requests.post(url=urlGraphqlApi, json=queryRatings)
    ratings_obj = eval(ratings.text)
    ratings_json = ratings_obj["data"]["ratings"]
    ratings_df = pd.json_normalize(ratings_json)

    #creamos una columna nueva que se llamará year
    movies_df['year'] = movies_df.title.str.extract('(\(\d\d\d\d\))',expand=False)
    #Quitando los paréntesis 
    movies_df['year'] = movies_df.year.str.extract('(\d\d\d\d)',expand=False)
    #Eliminar los años de la columna "título" y el espacio
    movies_df['title'] = movies_df.title.str.replace(' (\(\d\d\d\d\))', '')
    #eliminamos los generos
    movies_df = movies_df.drop('genres',1)

    #userInput = [
    #{'title':'Heat', 'rating':5},
    #{'title':'Star Wars: Episode II - Attack of the Clones', 'rating':4.5},
    #{'title':'Secret in Their Eyes, The (El secreto de sus ojos)', 'rating':4.5},
    # {'title':'Terminator 2: Judgment Day', 'rating':4.5},
    #{'title':'Four Rooms', 'rating':3.5}
    #]

    movieItems = list(input.__root__)
    myMovies = []
    for movie in movieItems:
       mymovie = {
                   "title" : movie.title,
                   "rating" : movie.rating
                 }
       myMovies.append(mymovie)

    inputMovies = pd.DataFrame(myMovies)
    print(inputMovies)

    #Filtrar las películas por título 
    inputId = movies_df[movies_df['title'].isin(inputMovies['title'].tolist())]
    #Luego fusionándolo para que podamos obtener el movieId. Lo está fusionando implícitamente por título. 
    #print(inputId)
    inputMovies = pd.merge(inputId, inputMovies)
    #print(inputMovies)
    #Eliminar información que no usaremos del dataframe
    inputMovies = inputMovies.drop('year', 1)
    #Final input dataframe
    #inputMovies
    #Filtrar a los usuarios que han visto películas que la entrada ha visto y almacenarlas 
    userSubset = ratings_df[ratings_df['movieId'].isin(inputMovies['movieId'].tolist())]
    #print(userSubset.head())
    # Groupby crea varios sub dataframes de datos donde todos tienen el mismo valor en la columna especificada #como parámetro 
    userSubsetGroup = userSubset.groupby(['userId'])
    # Ordenamos por los usuarios que han puntuado mas a las peliculas en común con la entrada
    userSubsetGroup = sorted(userSubsetGroup, key=lambda x: len(x[1]), reverse=True)
    userSubsetGroup = userSubsetGroup[0:100]
   
    pearsonCorrelationDict = {}
    #Para cada grupo de usuarios de nuestro subconjunto 
    for name, group in userSubsetGroup:
        #Comencemos ordenando la entrada y el grupo de usuarios actual para que los valores no se mezclen más adelante. 
        group = group.sort_values(by='movieId')
        inputMovies = inputMovies.sort_values(by='movieId')
        #Obtenga las puntuaciones de las reseñas de las películas que ambos tienen en común 
        temp_df = inputMovies[inputMovies['movieId'].isin(group['movieId'].tolist())]
        #Y luego guárdelos en una variable de búfer temporal en un formato de lista para facilitar cálculos futuros 
        tempRatingList = temp_df['rating'].tolist()
        #Pongamos también las reseñas del grupo de usuarios actual en un formato de lista 
        tempGroupList = group['rating'].tolist()
        data_corr = {'tempGroupList': tempGroupList,
            'tempRatingList': tempRatingList}
        pd_corr = pd.DataFrame(data_corr)
        r = pd_corr.corr(method="pearson")["tempRatingList"]["tempGroupList"]
        #ahora eliminamos los nan de nuestro coef de pearson
        if math.isnan(r) == True:
            r = 0
        pearsonCorrelationDict[name] = r

    #Convertimos el diccionario a un dataframe:         
    pearsonDF = pd.DataFrame.from_dict(pearsonCorrelationDict, orient='index')
    pearsonDF.columns = ['similarityIndex']
    pearsonDF['userId'] = pearsonDF.index
    pearsonDF.index = range(len(pearsonDF))

    topUsers=pearsonDF.sort_values(by='similarityIndex', ascending=False)[0:50]
    topUsers.head(20)

    topUsersRating=topUsers.merge(ratings_df, left_on='userId', right_on='userId', how='inner')
    topUsersRating.head()

    topUsersRating['weightedRating'] = topUsersRating['similarityIndex']*topUsersRating['rating']
    topUsersRating.head()

    tempTopUsersRating = topUsersRating.groupby('movieId').sum()[['similarityIndex','weightedRating']]
    tempTopUsersRating.columns = ['sum_similarityIndex','sum_weightedRating']
    tempTopUsersRating.head()

    #Crea un nuevo dataframe
    recommendation_df = pd.DataFrame()
    #Ahora tomamos el promedio ponderado 
    recommendation_df['weighted average recommendation score'] = tempTopUsersRating['sum_weightedRating']/tempTopUsersRating['sum_similarityIndex']
    recommendation_df['movieId'] = tempTopUsersRating.index
    #recommendation_df.head()

    recommendation_df = recommendation_df.sort_values(by='weighted average recommendation score', ascending=False)
    #recommendation_df.head(30)
    #print(movies_df.loc[movies_df['movieId'].isin(recommendation_df.head(30)['movieId'].tolist())])
    moviesRec = movies_df.loc[movies_df['movieId'].isin(recommendation_df.head(30)['movieId'].tolist())]

    return moviesRec.to_dict(orient='records')
