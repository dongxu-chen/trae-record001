import TodoItem from './TodoItem'

function TodoList({ todos, onToggle, onDelete, onUpdate, tags, getTagColor, getTagName }) {
  if (todos.length === 0) {
    return <div className="empty-list">暂无待办事项</div>
  }

  return (
    <div className="todo-list">
      {todos.map(todo => (
        <TodoItem
          key={todo.id}
          todo={todo}
          onToggle={onToggle}
          onDelete={onDelete}
          onUpdate={onUpdate}
          tags={tags}
          getTagColor={getTagColor}
          getTagName={getTagName}
        />
      ))}
    </div>
  )
}

export default TodoList
