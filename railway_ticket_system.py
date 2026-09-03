#!/usr/bin/env python3
"""
Railway Ticket Simulation System

A detailed educational railway reservation simulator using:
- Python OOP
- SQLite database
- Train and station search
- Seat inventory and coach allocation
- Fare calculation
- Confirmed / RAC-like / waitlist simulation
- PNR generation
- Booking history
- Ticket cancellation + refund
- Admin train / station / route management
- Seed demo data
- Interactive CLI

This is a simulation for learning purposes and does not represent
real railway/IRCTC reservation, quota, refund, or fare rules.
"""

from __future__ import annotations

import sqlite3
import random
import string
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


DB_NAME = "railway.db"

# Utilities #

def money(amount: float) -> str:
    return f"₹{amount:,.2f}"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_date(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def generate_pnr() -> str:
    # 10-character simulation PNR
    prefix = datetime.now().strftime("%y%m%d")
    suffix = "".join(random.choices(string.digits, k=4))
    return prefix + suffix


def ask_int(prompt: str, minimum=None, maximum=None) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a valid integer.")
            continue

        if minimum is not None and value < minimum:
            print(f"Value must be >= {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Value must be <= {maximum}.")
            continue
        return value


def ask_float(prompt: str, minimum=None) -> float:
    while True:
        raw = input(prompt).strip()
        try:
            value = float(raw)
        except ValueError:
            print("Please enter a valid number.")
            continue
        if minimum is not None and value < minimum:
            print(f"Value must be >= {minimum}.")
            continue
        return value


# Data classes #

@dataclass
class Passenger:
    name: str
    age: int
    gender: str
    berth_preference: str = "No Preference"


@dataclass
class SearchResult:
    train_id: int
    train_no: str
    train_name: str
    departure: str
    arrival: str
    source: str
    destination: str
    duration_hours: float

# Database #

class Database:
    def __init__(self, db_name: str = DB_NAME):
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_schema()

    def create_schema(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE,
            city TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS trains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_no TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            train_type TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_id INTEGER NOT NULL,
            station_id INTEGER NOT NULL,
            stop_no INTEGER NOT NULL,
            arrival TEXT,
            departure TEXT,
            distance_km REAL NOT NULL DEFAULT 0,
            FOREIGN KEY(train_id) REFERENCES trains(id) ON DELETE CASCADE,
            FOREIGN KEY(station_id) REFERENCES stations(id) ON DELETE CASCADE,
            UNIQUE(train_id, stop_no)
        );

        CREATE TABLE IF NOT EXISTS coaches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_id INTEGER NOT NULL,
            coach_code TEXT NOT NULL,
            class_code TEXT NOT NULL,
            seat_capacity INTEGER NOT NULL,
            FOREIGN KEY(train_id) REFERENCES trains(id) ON DELETE CASCADE,
            UNIQUE(train_id, coach_code)
        );

        CREATE TABLE IF NOT EXISTS fares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_id INTEGER NOT NULL,
            class_code TEXT NOT NULL,
            rate_per_km REAL NOT NULL,
            base_fare REAL NOT NULL DEFAULT 50,
            FOREIGN KEY(train_id) REFERENCES trains(id) ON DELETE CASCADE,
            UNIQUE(train_id, class_code)
        );

        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pnr TEXT NOT NULL UNIQUE,
            train_id INTEGER NOT NULL,
            journey_date TEXT NOT NULL,
            source_station_id INTEGER NOT NULL,
            destination_station_id INTEGER NOT NULL,
            class_code TEXT NOT NULL,
            status TEXT NOT NULL,
            total_fare REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(train_id) REFERENCES trains(id),
            FOREIGN KEY(source_station_id) REFERENCES stations(id),
            FOREIGN KEY(destination_station_id) REFERENCES stations(id)
        );

        CREATE TABLE IF NOT EXISTS passengers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            passenger_no INTEGER NOT NULL,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            berth_preference TEXT NOT NULL,
            allocation_status TEXT NOT NULL,
            coach_code TEXT,
            seat_no INTEGER,
            fare REAL NOT NULL,
            FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_bookings_pnr ON bookings(pnr);
        CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(journey_date);
        CREATE INDEX IF NOT EXISTS idx_passengers_booking ON passengers(booking_id);
        """)

    def execute(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur

    def executemany(self, sql, seq):
        cur = self.conn.executemany(sql, seq)
        self.conn.commit()
        return cur

    def query_one(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()

    def query_all(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    def close(self):
        self.conn.close()

# Core system #

class RailwaySystem:
    CLASS_INFO = {
        "SL": {"name": "Sleeper", "multiplier": 1.0},
        "3A": {"name": "AC 3-Tier", "multiplier": 2.1},
        "2A": {"name": "AC 2-Tier", "multiplier": 3.1},
        "1A": {"name": "First AC", "multiplier": 4.3},
        "CC": {"name": "Chair Car", "multiplier": 1.5},
    }

    BERTHS = ["Lower", "Middle", "Upper", "Side Lower", "Side Upper"]

    def __init__(self, db: Database):
        self.db = db
