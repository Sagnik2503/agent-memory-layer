from app.db.database import Base, engine
from app.db.models import ExpenseDB, SubscriptionDB

print("Database URL:", engine.url)
print("Creating tables...")

Base.metadata.create_all(bind=engine)

print("Done")
