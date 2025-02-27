from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, unique=True, nullable=False)
    first_name = Column(String(255))
    last_name = Column(String(255))
    age = Column(Integer)
    gender = Column(String(10))
    city = Column(String(255))
    access_token = Column(Text)

    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    blacklist = relationship("Blacklist", back_populates="user", cascade="all, delete-orphan")
    viewed = relationship("Viewed", back_populates="user", cascade="all, delete-orphan")
    photo_likes = relationship("UserPhotoLike", back_populates="user")


class Candidate(Base):
    __tablename__ = 'candidates'

    candidate_id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, unique=True, nullable=False)
    first_name = Column(String(255))
    last_name = Column(String(255))
    profile_link = Column(Text)
    age = Column(Integer)
    gender = Column(String(10))
    city = Column(String(255))

    photos = relationship("Photo", back_populates="candidate", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="candidate")
    blacklist = relationship("Blacklist", back_populates="candidate")
    viewed = relationship("Viewed", back_populates="candidate")


class Photo(Base):
    __tablename__ = 'photos'

    photo_id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey('candidates.candidate_id', ondelete="CASCADE"))
    photo_url = Column(Text, nullable=False)
    likes_count = Column(Integer)

    candidate = relationship("Candidate", back_populates="photos")
    likes = relationship("UserPhotoLike", back_populates="photo")

class Favorite(Base):
    __tablename__ = 'favorites'

    user_id = Column(Integer, ForeignKey('users.user_id', ondelete="CASCADE"), primary_key=True)
    candidate_id = Column(Integer, ForeignKey('candidates.candidate_id', ondelete="CASCADE"), primary_key=True)
    date_added = Column(TIMESTAMP, default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")
    candidate = relationship("Candidate", back_populates="favorites")


class Blacklist(Base):
    __tablename__ = 'blacklist'

    user_id = Column(Integer, ForeignKey('users.user_id', ondelete="CASCADE"), primary_key=True)
    candidate_id = Column(Integer, ForeignKey('candidates.candidate_id', ondelete="CASCADE"), primary_key=True)
    date_added = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="blacklist")
    candidate = relationship("Candidate", back_populates="blacklist")


class Viewed(Base):
    __tablename__ = 'viewed'

    user_id = Column(Integer, ForeignKey('users.user_id', ondelete="CASCADE"), primary_key=True)
    candidate_id = Column(Integer, ForeignKey('candidates.candidate_id', ondelete="CASCADE"), primary_key=True)
    viewed_date = Column(TIMESTAMP, default=datetime.utcnow)

    user = relationship("User", back_populates="viewed")
    candidate = relationship("Candidate", back_populates="viewed")


class UserPhotoLike(Base):
    __tablename__ = 'user_photo_likes'

    user_id = Column(Integer, ForeignKey('users.user_id', ondelete="CASCADE"), primary_key=True)
    photo_id = Column(Integer, ForeignKey('photos.photo_id', ondelete="CASCADE"), primary_key=True)
    liked = Column(Boolean, default=True)

    user = relationship("User", back_populates="photo_likes")
    photo = relationship("Photo", back_populates="likes")


DATABASE_URI = 'postgresql+psycopg2://user:password@localhost/db_name'
engine = create_engine(DATABASE_URI)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()