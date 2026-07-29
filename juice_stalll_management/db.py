from pymongo import MongoClient

client = MongoClient(
    "mongodb://localhost:27017/",
    serverSelectionTimeoutMS=5000
)

db = client["RestaurantDB"]

products = db["products.csv"]
customers = db["customers.csv"]
orders = db["orders.csv"]
ingredients = db["Ingredients.csv"]
reviews = db["reviews.csv"]
users = db["users.csv"]
payments = db["payments.csv"]
branches = db["branches.csv"]