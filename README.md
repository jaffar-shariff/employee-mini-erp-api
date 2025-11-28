# Employee Management Mini ERP API

A simple **ERP-style REST API** to manage employees and departments, built with **FastAPI** and **SQLite**.

## Features

- Create, list, view and delete **departments**
- Create, list, view, update and delete **employees**
- Filter employees by:
  - Active / Inactive status
  - Department
- Built using:
  - FastAPI
  - SQLAlchemy
  - SQLite
  - Pydantic

## Tech Stack

- Python 3.x
- FastAPI
- SQLite
- SQLAlchemy
- Uvicorn

## Setup & Run

```bash
pip install -r requirements.txt
uvicorn main:app --reload
