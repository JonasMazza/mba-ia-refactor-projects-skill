"""User payload validation."""
from src.middlewares.errors import ValidationError


def validate_signup(dados: dict | None) -> dict:
    if not dados:
        raise ValidationError("dados inválidos")
    nome = dados.get("nome", "").strip()
    email = dados.get("email", "").strip().lower()
    senha = dados.get("senha", "")

    if not nome or not email or not senha:
        raise ValidationError("nome, email e senha são obrigatórios")
    if "@" not in email:
        raise ValidationError("email inválido")
    if len(senha) < 6:
        raise ValidationError("senha deve ter ao menos 6 caracteres")
    return {"nome": nome, "email": email, "senha": senha}


def validate_login(dados: dict | None) -> dict:
    if not dados:
        raise ValidationError("dados inválidos")
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""
    if not email or not senha:
        raise ValidationError("email e senha são obrigatórios")
    return {"email": email, "senha": senha}
