"""Category domain service."""
from database import db
from middlewares.error_handler import NotFoundError
from models.category import Category


def create_category(payload: dict) -> dict:
    category = Category(
        name=payload["name"],
        description=payload.get("description", ""),
        color=payload.get("color", "#000000"),
    )
    db.session.add(category)
    db.session.commit()
    return category.to_dict()


def update_category(cat_id: int, payload: dict) -> dict:
    cat = db.session.get(Category, cat_id)
    if not cat:
        raise NotFoundError("Categoria não encontrada")
    for field, value in payload.items():
        setattr(cat, field, value)
    db.session.commit()
    return cat.to_dict()


def delete_category(cat_id: int) -> None:
    cat = db.session.get(Category, cat_id)
    if not cat:
        raise NotFoundError("Categoria não encontrada")
    db.session.delete(cat)
    db.session.commit()
