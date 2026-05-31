"""Populate the dev database with sample data.

Run with: `python -m app seed` or `python seed.py`.
Passwords are hashed with bcrypt (via `User.set_password`).
"""
from datetime import datetime, timedelta

from database import db
from models.category import Category
from models.task import Task
from models.user import User


def seed_data(flask_app=None):
    if flask_app is None:
        from app import app as flask_app

    with flask_app.app_context():
        # Clean slate
        Task.query.delete()
        User.query.delete()
        Category.query.delete()
        db.session.commit()

        u1 = User(name="João Silva", email="joao@email.com", role="admin")
        u1.set_password("1234")
        u2 = User(name="Maria Santos", email="maria@email.com", role="user")
        u2.set_password("abcd")
        u3 = User(name="Pedro Oliveira", email="pedro@email.com", role="manager")
        u3.set_password("pass")
        db.session.add_all([u1, u2, u3])
        db.session.commit()

        categories = [
            Category(name="Backend", description="Tarefas de backend", color="#3498db"),
            Category(name="Frontend", description="Tarefas de frontend", color="#2ecc71"),
            Category(name="DevOps", description="Tarefas de infraestrutura", color="#e74c3c"),
            Category(name="Bug", description="Correção de bugs", color="#e67e22"),
        ]
        db.session.add_all(categories)
        db.session.commit()
        c1, c2, c3, c4 = categories

        tasks_data = [
            {"title": "Implementar autenticação JWT", "description": "Adicionar autenticação real com JWT", "status": "pending", "priority": 1, "user_id": u1.id, "category_id": c1.id, "due_date": datetime.utcnow() - timedelta(days=3)},
            {"title": "Criar tela de login", "description": "Tela de login responsiva", "status": "in_progress", "priority": 2, "user_id": u2.id, "category_id": c2.id, "due_date": datetime.utcnow() + timedelta(days=5)},
            {"title": "Configurar CI/CD", "description": "Pipeline com GitHub Actions", "status": "done", "priority": 2, "user_id": u3.id, "category_id": c3.id, "tags": "devops,ci,github"},
            {"title": "Corrigir bug no filtro de busca", "description": "Filtro não funciona com caracteres especiais", "status": "pending", "priority": 1, "user_id": u1.id, "category_id": c4.id, "due_date": datetime.utcnow() - timedelta(days=1)},
            {"title": "Adicionar paginação na API", "description": "Endpoints retornam todos os registros", "status": "pending", "priority": 3, "user_id": u1.id, "category_id": c1.id, "due_date": datetime.utcnow() + timedelta(days=10)},
            {"title": "Escrever testes unitários", "description": "Cobertura mínima de 80%", "status": "pending", "priority": 2, "user_id": u2.id, "category_id": c1.id},
            {"title": "Documentar API com Swagger", "description": "Gerar documentação automática", "status": "cancelled", "priority": 4, "user_id": u3.id, "category_id": c1.id},
            {"title": "Refatorar models", "description": "Melhorar organização dos models", "status": "in_progress", "priority": 3, "user_id": u2.id, "category_id": c1.id, "tags": "refactor,tech-debt"},
            {"title": "Configurar monitoramento", "description": "Prometheus + Grafana", "status": "pending", "priority": 4, "user_id": u3.id, "category_id": c3.id, "due_date": datetime.utcnow() + timedelta(days=20)},
            {"title": "Melhorar validações de input", "description": "Usar marshmallow ou pydantic", "status": "pending", "priority": 3, "user_id": u1.id, "category_id": c1.id, "tags": "improvement,validation"},
        ]
        for td in tasks_data:
            db.session.add(Task(**td))
        db.session.commit()

        print("Seed concluído com sucesso!")
        print(f"  {User.query.count()} usuários")
        print(f"  {Category.query.count()} categorias")
        print(f"  {Task.query.count()} tasks")


if __name__ == "__main__":
    seed_data()
