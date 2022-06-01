from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    # code here...
    # recommender ..

    return {"message" : "Hello Docker fastapi..." }
