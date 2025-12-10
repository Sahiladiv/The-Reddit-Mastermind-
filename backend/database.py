from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Example connection string — update username/password/dbname
MYSQL_URL = "mysql+pymysql://root:root@localhost:3306/ogtool"

engine = create_engine(
    MYSQL_URL,
    echo=True,          # shows SQL in console
    future=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
