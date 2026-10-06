"""A tiny in-memory todo API used as the subject of the spec-check evaluation."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Todo API")


class TodoIn(BaseModel):
    title: str = Field(min_length=1, max_length=100)


class Todo(BaseModel):
    id: int
    title: str
    done: bool = False


todos: dict[int, Todo] = {}
_next_id = 1


def reset_store() -> None:
    global _next_id
    todos.clear()
    _next_id = 1


@app.get("/todos")
def list_todos() -> list[Todo]:
    return list(todos.values())


@app.post("/todos", status_code=201)
def create_todo(payload: TodoIn) -> Todo:
    global _next_id
    todo = Todo(id=_next_id, title=payload.title)
    todos[todo.id] = todo
    _next_id += 1
    return todo


@app.get("/todos/{todo_id}")
def get_todo(todo_id: int) -> Todo:
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todos[todo_id]
